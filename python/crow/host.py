# host.py
# Crow Host Implementation
# 2 May 2018
# Chris Siedell
# project: https://pypi.org/project/crow-serial/
# source: https://github.com/chris-siedell/PyCrow
# homepage: http://siedell.com/projects/Crow/


import time
import serial
import crow.utils
import crow.parser
import crow.transaction
import crow.errors
import crow.host_serial


class Host:

    # A Host object is the intermediary used by a Client object to send
    #  commands and receive responses over a serial port.
    # The intention is that each Client instance will create a Host instance.
    #  By design, the host instances are relatively lightweight. Multiple host
    #  instances may use the same serial port. There will be only one
    #  underlying serial.Serial instance per serial port, regardless of how
    #  many hosts are using that serial port.
    # The serial.Serial instance is wrapped by a HostSerialPort object, which
    #  also stores the settings used by each address on that serial port.
    # Changing the serial port (i.e. the HostSerialPort object) is done by
    #  changing the serial_port_name property.

    def __del__(self):
        if hasattr(self, '_serial_port'):
            Host._release_serial_port(self._serial_port)

    def __init__(self, serial_port_name):
        self._serial_port = Host._retain_serial_port_by_name(serial_port_name)
        self._next_token = 0
        self._parser = crow.parser.Parser()
        self.custom_service_error_callback = None

    @property
    def serial_port_name(self):
        return self._serial_port.name

    @serial_port_name.setter
    def serial_port_name(self, serial_port_name):
        # Release old instance after retaining new one in case they are the
        #  same object to prevent unnecessary deletion and creation.
        old_sp = self._serial_port
        self._serial_port = Host._retain_serial_port_by_name(serial_port_name)
        Host._release_serial_port(old_sp)

    @property
    def serial_port(self):
        return self._serial_port

    def send_command(self, address=1, port=32, payload=None, response_expected=True, context=None):
        # context is an optional argument. It will be passed to the custom service error
        #  callback if an error response with numbers 128-255 is received.

        # Returns a Transaction object if successful, or raises an exception.
        # The transaction object's response property will be None when response_expected==False,
        #  or a bytes-like object otherwise.

        ser = self._serial_port.serial

        baudrate = self._serial_port.get_baudrate(address)
        transaction_timeout = self._serial_port.get_transaction_timeout(address)
        propcr_order = self._serial_port.get_propcr_order(address)

        ser.reset_input_buffer()
        ser.baudrate = baudrate

        token = (self._next_token%256 + 256)%256
        self._next_token = (self._next_token + 1)%256

        t = crow.transaction.Transaction()
        t.new_command(address, port, payload, response_expected, token, propcr_order)

        ser.write(t.cmd_packet_buff[0:t.cmd_packet_size])

        if not response_expected:
            return t

        self._parser.reset()

        # The time limit is
        #  <time start receiving> + <transaction timeout> + <time to transmit rec'd data at baudrate, up to 2084 bytes>.
        bits_per_byte = 10.0
        if ser.stopbits == serial.STOPBITS_ONE_POINT_FIVE:
            bits_per_byte += 0.5
        elif ser.stopbits == serial.STOPBITS_TWO:
            bits_per_byte += 1.0
        seconds_per_byte = bits_per_byte / baudrate
        now = time.perf_counter()
        time_limit = now + transaction_timeout
        max_time_limit = time_limit + seconds_per_byte*2084

        byte_count = 0
        results = []
        
        while self._parser.min_bytes_expected > 0 and now < time_limit:
            
            ser.timeout = time_limit - now 
            data = ser.read(self._parser.min_bytes_expected)
            byte_count += len(data)
            results += self._parser.parse_data(data, token)
            
            time_limit = min(time_limit + seconds_per_byte*len(data), max_time_limit)
            now = time.perf_counter()

        # The parser returns a list of a results, where each item is an dictionary
        #  with a 'type' property. See the comments to Parser.parse_data for details.
        
        if self._parser.min_bytes_expected == 0:
            # The parser sets min_bytes_expected==0 to signify that an expected
            #  response (identified by token) was received.
            # Currently we are ignoring other items in results besides the expected
            #  response (i.e. other responses, extraneous bytes, leftovers, etc.).
            # todo: consider adding warnings for unexpected parser results
            for item in results:
                if item['type'] == 'response':
                    if item['token'] == token:
                        # The expected response was parseable, and is described by item.
                        t.response = item['payload']
                        if item['is_error']:
                            # error response
                            self._raise_error(t, context)
                        else:
                            # normal response
                            return t
                elif item['type'] == 'error':
                    if item['token'] == token:
                        # The expected response was recognized, but could not be
                        #  parsed. item describes the error.
                        raise crow.errors.NoResponseError(address, port, byte_count, item['message'])
            raise RuntimeError("Programming error. Expected to find a response with the correct token in parser results, but none was found.")
        else:
            # Failed to receive a response with the expected token.
            if byte_count == 0:
                # No data received at all.
                raise crow.errors.NoResponseError(address, port, byte_count)
            for item in results:
                if item['type'] == 'response':
                    if item['token'] != token:
                        # A parseable response with incorrect token was received.
                        raise crow.errors.NoResponseError(address, port, byte_count, "An invalid response was received (incorrect token). It may be a stale response, or the responding device may have malfunctioned.")
                    else:
                        raise RuntimeError("Programming error. Should not have a response with the correct token in the parser results at this point.")
            # To get to this point, some data must have been received, but the parser was unable
            #  to find a complete response packet -- whether with the expected token or not, or
            #  corrupt or not.
            # todo: consider adding a message to the error based on the final parser state
            #  and the parser results
            raise crow.errors.NoResponseError(address, port, byte_count)


    def _raise_error(self, transaction, context):
        # context passed to the custom service error callback, if applicable.
    
        address = transaction.address
        port = transaction.port
        response = transaction.response
        
        if len(response) == 0:
            # If the payload is empty we use an implicit number 0 (generic RemoteError).
            number = 0
        else:
            # The error number is the first byte of the payload.
            number = response[0]
    
        # rsp_name is used if there is an error parsing the error response
        rsp_name = "error number " + str(number)
    
        # info will hold any additional details included in the error.
        info = {}
    
        # Optional byte E1 is a bitfield that specifies what additional details are included.
        if len(response) >= 2:
            E1 = response[1]
            transaction.arg_index = 2
            try:
                # The unpack_* functions will raise RuntimeError on parsing errors.
                if E1 & 1:
                    crow.utils.unpack_ascii(info, transaction, 4, 'message', rsp_name)
                if E1 & 2:
                    crow.utils.unpack_int(info, transaction, 1, 'crow_version', rsp_name)
                if E1 & 4:
                    crow.utils.unpack_int(info, transaction, 2, 'max_command_size', rsp_name)
                if E1 & 8:
                    crow.utils.unpack_int(info, transaction, 2, 'max_response_size', rsp_name)
                if E1 & 16:
                    crow.utils.unpack_int(info, transaction, 1, 'address', rsp_name)
                if E1 & 32:
                    crow.utils.unpack_int(info, transaction, 1, 'port', rsp_name)
                if E1 & 64:
                    crow.utils.unpack_ascii(info, transaction, 3, 'service_identifier', rsp_name)
            except RuntimeError as e:
                # If the RemoteError response can not be parsed it gets superceded by a HostError.
                raise crow.errors.HostError(address, port, str(e))
    
        if number == 0:
            raise crow.errors.RemoteError(address, port, number, info)
        elif number == 1:
            raise crow.errors.DeviceError(address, port, number, info)
        elif number == 2:
            raise crow.errors.DeviceFaultError(address, port, number, info)
        elif number == 3:
            raise crow.errors.ServiceFaultError(address, port, number, info)
        elif number == 4:
            raise crow.errors.DeviceUnavailableError(address, port, number, info)
        elif number == 5:
            raise crow.errors.DeviceIsBusyError(address, port, number, info)
        elif number == 6:
            raise crow.errors.OversizedCommandError(address, port, number, info)
        elif number == 7:
            raise crow.errors.CorruptCommandPayloadError(address, port, number, info)
        elif number == 8:
            raise crow.errors.PortNotOpenError(address, port, number, info)
        elif number == 9:
            raise crow.errors.DeviceLowResourcesError(address, port, number, info)
        elif number >= 10 and number < 32:
            raise crow.errors.UnknownDeviceError(address, port, number, info)
        elif number >= 32 and number < 64:
            raise crow.errors.DeviceError(address, port, number, info)
        elif number == 64:
            raise crow.errors.ServiceError(address, port, number, info)
        elif number == 65:
            raise crow.errors.UnknownCommandFormatError(address, port, number, info)
        elif number == 66:
            raise crow.errors.ServiceLowResourcesError(address, port, number, info)
        elif number == 67:
            raise crow.errors.InvalidCommandError(address, port, number, info)
        elif number == 68:
            raise crow.errors.RequestTooLargeError(address, port, number, info)
        elif number == 69:
            raise crow.errors.CommandNotAvailableError(address, port, number, info)
        elif number == 70:
            raise crow.errors.CommandNotImplementedError(address, port, number, info)
        elif number == 71:
            raise crow.errors.CommandNotAllowedError(address, port, number, info)
        elif number == 72:
            raise crow.errors.IncorrectCommandSizeError(address, port, number, info)
        elif number == 73:
            raise crow.errors.MissingCommandDataError(address, port, number, info)
        elif number == 74:
            raise crow.errors.TooMuchCommandDataError(address, port, number, info)
        elif number >= 75 and number < 128:
            raise crow.errors.UnknownServiceError(address, port, number, info)
        elif number >= 128 and number < 256:
            if self.custom_service_error_callback is not None:
                self.custom_service_error_callback(address, port, number, info, context)
            raise crow.errors.ServiceError(address, port, number, info)
      
        raise RuntimeError("Programming error. A remote error (number " + str(number) + ") was not handled.")
    

    # _serial_ports maintains references to all HostSerialPort instances in use
    #  by hosts. _serial_ports is managed by the _retain*/_release* static methods
    #  of Host, and only those methods should create HostSerialPort instances.
    # The static methods use the retain_count property on each HostSerialPort
    #  instance so that the instance can be removed from the set when the serial
    #  port is no longer used by any host.
    _serial_ports = set()

    @staticmethod
    def _retain_serial_port_by_name(serial_port_name):
        for sp in Host._serial_ports:
            if sp.name == serial_port_name:
                # A HostSerialPort instance with that name exists, so use it.
                sp.retain_count += 1
                return sp
        # There is no HostSerialPort instance with that name, so create one.
        sp = crow.host_serial.HostSerialPort(serial_port_name, _magic_word="abracadabra")
        Host._serial_ports.add(sp)
        sp.retain_count = 1
        return sp

    @staticmethod
    def _release_serial_port(sp):
        sp.retain_count -= 1
        if sp.retain_count == 0:
            # No hosts are using the serial port, so remove it from the set.
            Host._serial_ports.remove(sp)

    
    @staticmethod
    def set_baudrate(serial_port_name, address, baudrate):
        for sp in Host._serial_ports:
            if sp.name == serial_port_name:
                sp.set_baudrate(address, baudrate)
                return
        raise RuntimeError("The serial port is not in use by any host.")

    @staticmethod
    def set_transaction_timeout(serial_port_name, address, transaction_timeout):
        for sp in Host._serial_ports:
            if sp.name == serial_port_name:
                sp.set_transaction_timeout(address, transaction_timeout)
                return
        raise RuntimeError("The serial port is not in use by any host.")

    @staticmethod
    def set_propcr_order(serial_port_name, address, propcr_order):
        for sp in Host._serial_ports:
            if sp.name == serial_port_name:
                sp.set_propcr_order(address, propcr_order)
                return
        raise RuntimeError("The serial port is not in use by any host.")

    @staticmethod
    def open(serial_port_name):
        for sp in Host._serial_ports:
            if sp.name == serial_port_name:
                sp.serial.open()
                return
        raise RuntimeError("The serial port is not in use by any host.")

    @staticmethod
    def close(serial_port_name):
        for sp in Host._serial_ports:
            if sp.name == serial_port_name:
                sp.serial.close()
                return
        raise RuntimeError("The serial port is not in use by any host.")



