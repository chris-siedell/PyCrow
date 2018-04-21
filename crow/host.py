# Crow Host
# 21 April 2018
# Chris Siedell
# https://github.com/chris-siedell/PyCrow


import time
import serial
import crow.utils
import crow.parser
import crow.transaction
import crow.errors


class SerialSettings():
    # SerialSettings stores settings used by Crow hosts and clients.
    # Values of None indicate that defaults should be used.
    def __init__(self):
        self.baudrate = None
        self.transaction_timeout = None


class SerialPort():
    # SerialPort represents a serial port used by a Crow host. It maintains a reference
    #  to a serial.Serial instance and stores the settings for all 32 Crow addresses
    #  associated with the serial port.
    # The serial.Serial instance associated with the serial port is intended to be read-only,
    #  and it is assumed that its port property is constant.
    # SerialPort objects should be created only in the static methods of the Host class.
    # Host is designed so that only one SerialPort object is created for each port name,
    #  regardless of how many hosts are using that port.

    def __del__(self):
        print("SerialPort.__del__")
        print("  self: " + str(self))
        
    def __init__(self, serial_port_name):
        print("SerialPort.__init__")
        print("  serial_port_name: " + serial_port_name)
        self._serial = serial.Serial(serial_port_name)
        self._settings = []
        for i in range(0, 32):
            self._settings.append(SerialSettings());
        self.default_transaction_timeout = 0.25
        self.default_baudrate = 115200

    def __repr__(self):
        return "<" + self.__class__.__name__ + " instance for '" + self._serial.port + "' at " + "{0:#x}>".format(id(self))

    @property
    def serial(self):
        return self._serial

    @property
    def name(self):
        return self._serial.port

    def get_transaction_timeout(self, address):
        value = self._settings[address].transaction_timeout
        if value is not None:
            return value
        else:
            return self.default_transaction_timeout

    def get_baudrate(self, address):
        value = self._settings[address].baudrate
        if value is not None:
            return value
        else:
            return self.default_baudrate


class Host:

    # A Host object is the intermediary used by a Client object to send
    #  commands and receive responses over a serial port.
    # The intention is that each Client instance will create a Host instance.
    #  By design, the host instances are relatively lightweight. Multiple host
    #  instances may use the same serial port. There will be only one
    #  underlying serial.Serial instance per serial port, regardless of how
    #  many hosts are using that serial port.

    # _serial_ports maintains references to all SerialPort instances in use
    #  by hosts. _serial_ports is managed by static methods on Host, and
    #  only those methods should use this set or create SerialPort instances.
    #  The static methods add a retain_count property to each SerialPort
    #  instance so that the instance can be removed from the set when
    #  the serial port is no longer used by any host.

    _serial_ports = set()

    @staticmethod
    def _retain_serial_port_by_name(serial_port_name):
        print("_retain_serial_port_by_name")
        print("  serial_port_name: "+serial_port_name)
        for sp in Host._serial_ports:
            if sp.name == serial_port_name:
                # A SerialPort instance with that port name exists, so use it.
                print("  serial port already exits")
                print("  sp: " + str(sp))
                sp.retain_count += 1
                return sp
        print("  serial port does not exist, will create")
        # There is no SerialPort instance with that port name, so create one.
        sp = SerialPort(serial_port_name)
        Host._serial_ports.add(sp)
        sp.retain_count = 1
        print("  sp: "+str(sp))
        return sp

    @staticmethod
    def _release_serial_port(sp):
        print("_release_serial_port")
        print("  sp: "+str(sp))
        sp.retain_count -= 1
        if sp.retain_count == 0:
            # No hosts are using the serial port, so remove it from the set.
            print("  retain count reached zero, will remove")
            Host._serial_ports.remove(sp)

    def __del__(self):
        print("Host.__del__")
        print("  ref: " + str(self))
        print("  serial_port: " + str(self._serial_port))
        Host._release_serial_port(self._serial_port)

    def __init__(self, serial_port_name):
        print("Host.__init__")
        print("  ref: " + str(self))
        self._serial_port = Host._retain_serial_port_by_name(serial_port_name)
        print("  serial_port: " + str(self._serial_port))
        self._next_token = 0
        self._parser = crow.parser.Parser()

    @property
    def serial_port_name(self):
        print("serial_port_name getter")
        return self._serial_port.name

    @serial_port_name.setter
    def serial_port_name(self, serial_port_name):
        print("serial_port_name setter")
        # Release old instance after retaining new one in case they refer to the
        #  same object (prevents unnecessary deletion and creation).
        old_sp = self._serial_port
        self._serial_port = Host._retain_serial_port_by_name(serial_port_name)
        print("  new serial_port: " + str(self._serial_port))
        print("  old serial_port: " + str(old_sp))
        Host._release_serial_port(old_sp)

    # Although the host exposes the underlying serial.Serial instance, user
    #  code should be careful about making changes to this object.
    # Changing the baudrate and read timeout are safe, and will have no effect
    #  on Crow clients. If the serial object is closed it must be reopened
    #  before sending commands.
    # The port property must not be changed -- changes will cause undefined
    #  behavior since they violate assumptions made in the Host's internals.
    @property
    def serial(self):
        print("serial getter")
        print("  serial_port: " + str(self._serial_port))
        return self._serial_port.serial

    def send_command(self, address=1, port=32, payload=None, response_expected=True, propcr_order=False):

        # Returns a Transaction object if successful, or raises an exception.
        # The transaction object's response property will be None when response_expected==False,
        #  or a bytes-like object otherwise.

        # Get the serial port settings.
        ser = self._serial_port.serial
        transaction_timeout = self._serial_port.get_transaction_timeout(address)
        baudrate = self._serial_port.get_baudrate(address)

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
                            raise_remote_error(t)
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


def raise_remote_error(transaction):

    # Remote errors are those that are raised by the device by
    #  sending an error response.

    address = transaction.address
    port = transaction.port
    response = transaction.response

    # If the error response payload is empty we raise UnspecifiedDeviceError.
    if len(response) == 0:
        raise crow.errors.UnspecifiedDeviceError(address, port, None)

    # The error number is in the first byte of the payload.
    number = response[0]

    # rsp_name is used if there is an error parsing the error response
    rsp_name = "error number " + str(number)

    # info will hold any additional details included in the error
    info = None

    # Optional byte E1 is a bitfield that specifies what additional details are included.
    if len(response) >= 2:
        info = {}
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
            raise crow.errors.HostError(address, port, str(e))

    if number == 0:
        raise crow.errors.UnspecifiedDeviceError(address, port, info)
    elif number == 1:
        raise crow.errors.DeviceFaultError(address, port, info)
    elif number == 2:
        raise crow.errors.ServiceFaultError(address, port, info)
    elif number == 3:
        raise crow.errors.DeviceUnavailableError(address, port, info)
    elif number == 4:
        raise crow.errors.DeviceIsBusyError(address, port, info)
    elif number == 5:
        raise crow.errors.OversizedCommandError(address, port, info)
    elif number == 6:
        raise crow.errors.CorruptCommandPayloadError(address, port, info)
    elif number == 7:
        raise crow.errors.PortNotOpenError(address, port, info)
    elif number == 8:
        raise crow.errors.DeviceLowResourcesError(address, port, info)
    elif number >= 9 and number < 32:
        raise crow.errors.UnknownDeviceError(address, port, number, info)
    elif number >= 32 and number < 64:
        raise crow.errors.DeviceError(address, port, number, info)
    elif number == 64:
        raise crow.errors.UnspecifiedServiceError(address, port, info)
    elif number == 65:
        raise crow.errors.UnknownCommandFormatError(address, port, info)
    elif number == 66:
        raise crow.errors.RequestTooLargeError(address, port, info)
    elif number == 67:
        raise crow.errors.ServiceLowResourcesError(address, port, info)
    elif number == 68:
        raise crow.errors.CommandNotAvailableError(address, port, info)
    elif number == 69:
        raise crow.errors.CommandNotImplementedError(address, port, info)
    elif number == 70:
        raise crow.errors.CommandNotAllowedError(address, port, info)
    elif number == 71:
        raise crow.errors.InvalidCommandError(address, port, info)
    elif number == 72:
        raise crow.errors.IncorrectCommandSizeError(address, port, info)
    elif number == 73:
        raise crow.errors.MissingCommandDataError(address, port, info)
    elif number == 74:
        raise crow.errors.TooMuchCommandDataError(address, port, info)
    elif number >= 75 and number < 128:
        raise crow.errors.UnknownServiceError(address, port, number, info)
    elif number >= 128 and number < 255:
        raise crow.errors.ServiceError(address, port, number, info)
  
    raise RuntimeError("Programming error. A remote error (number " + str(number) + ") was not handled.")



