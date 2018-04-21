# Crow Host
# 20 April 2018
# Chris Siedell
# https://github.com/chris-siedell/PyCrow


import time
import serial
import crow.utils
import crow.parser
import crow.transaction
import crow.host.errors
import crow.serial_wrapper


class SerialSettings():
    def __init__(self):
        self.baudrate = 115200
        self.timeout = 0.25


class Host:

    def __init__(self, serial_port):
        self._serial_wrapper = crow.serial_wrapper.SerialWrapper(serial_port)
        self._settings = []
        for i in range(0, 32):
            self._settings.append(SerialSettings())
        self._next_token = 2
        self._parser = crow.parser.Parser()

    @property
    def serial_port(self):
        return self._serial_wrapper.serial.port

    @serial_port.setter
    def serial_port(self, serial_port):
        self._serial_wrapper = crow.serial_wrapper.SerialWrapper(serial_port)

    @property
    def serial(self):
        return self._serial_wrapper.serial


    def send_command(self, address=1, port=32, payload=None, response_expected=True, propcr_order=False):

        # Returns a Transaction object if successful, or raises an exception.
        # The transaction object's response property will be None when response_expected==False,
        #  or a bytes-like object otherwise.

        ser = self._serial_wrapper.serial

        if ser is None:
            raise RuntimeError("The host can not send a command without a serial object. Set the host's serial or port properties.")

        ser.reset_input_buffer()

        token = (self._next_token%256 + 256)%256
        self._next_token = (self._next_token + 1)%256

        t = crow.transaction.Transaction()
        t.new_command(address, port, payload, response_expected, token, propcr_order)

        ser.write(t.cmd_packet_buff[0:t.cmd_packet_size])

        if not response_expected:
            return t

        self._parser.reset()

        timeout = self._settings[address].timeout
        baudrate = self._settings[address].baudrate

        ser.baudrate = baudrate

        # The time limit is <time start receiving> + <timeout> + <time to transmit up to 2084 bytes at baudrate>.
        bits_per_byte = 10.0
        if ser.stopbits == serial.STOPBITS_ONE_POINT_FIVE:
            bits_per_byte += 0.5
        elif ser.stopbits == serial.STOPBITS_TWO:
            bits_per_byte += 1.0
        seconds_per_byte = bits_per_byte / baudrate
        now = time.perf_counter()
        time_limit = now + timeout
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
        
        if self._parser.min_bytes_expected == 0:
            # The parser sets min_bytes_expected==0 to signify that an expected
            #  response (identified by token) was received.
            # Currently we are ignoring other items in results besides the expected
            #  response (i.e. other responses, extraneous bytes, leftovers, etc.).
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
                        raise crow.host.errors.NoResponseError(address, port, byte_count, item['message'])
            raise RuntimeError("Program logic error. Expected to find a response with the correct token in parser results, but none was found.")
        else:
            # Failed to receive a response with the expected token.
            if byte_count == 0:
                raise crow.host.errors.NoResponseError(address, port, byte_count)
            for item in results:
                if item['type'] == 'response':
                    if item['token'] != token:
                        raise crow.host.errors.NoResponseError(address, port, byte_count, "An invalid response was received (incorrect token). It may be a stale response, or the responding device may have malfunctioned.")
                    else:
                        raise RuntimeError("Program logic error. Should not have a response with the correct token in the parser results at this point.")
            raise crow.host.errors.NoResponseError(address, port, byte_count)


def raise_remote_error(transaction):

    address = transaction.address
    port = transaction.port
    response = transaction.response

    # If the error response payload is empty we raise UnspecifiedDeviceError.
    if len(response) == 0:
        raise crow.host.errors.UnspecifiedDeviceError(address, port, None)

    # The error number is in the first byte of the payload.
    number = response[0]

    # rsp_name is used if there is an error parsing the error response
    rsp_name = "error number " + str(number)

    # info will hold any additional details included in the error
    info = {}

    # Optional byte E1 is a bitfield that specifies what additional details are included.
    if len(response) >= 2:
        E1 = response[1]
        transaction.arg_index = 2
        try:
            # The unpack_* functions may raise RuntimeError.
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
            raise crow.host.errors.HostError(address, port, str(e))

    if number == 0:
        raise crow.host.errors.UnspecifiedDeviceError(address, port, info)
    elif number == 1:
        raise crow.host.errors.DeviceFaultError(address, port, info)
    elif number == 2:
        raise crow.host.errors.ServiceFaultError(address, port, info)
    elif number == 3:
        raise crow.host.errors.DeviceUnavailableError(address, port, info)
    elif number == 4:
        raise crow.host.errors.DeviceIsBusyError(address, port, info)
    elif number == 5:
        raise crow.host.errors.OversizedCommandError(address, port, info)
    elif number == 6:
        raise crow.host.errors.CorruptCommandPayloadError(address, port, info)
    elif number == 7:
        raise crow.host.errors.PortNotOpenError(address, port, info)
    elif number == 8:
        raise crow.host.errors.DeviceLowResourcesError(address, port, info)
    elif number >= 9 and number < 32:
        raise crow.host.errors.UnknownDeviceError(address, port, number, info)
    elif number >= 32 and number < 64:
        raise crow.host.errors.DeviceError(address, port, number, info)
    elif number == 64:
        raise crow.host.errors.UnspecifiedServiceError(address, port, info)
    elif number == 65:
        raise crow.host.errors.UnknownCommandFormatError(address, port, info)
    elif number == 66:
        raise crow.host.errors.RequestTooLargeError(address, port, info)
    elif number == 67:
        raise crow.host.errors.ServiceLowResourcesError(address, port, info)
    elif number == 68:
        raise crow.host.errors.CommandNotAvailableError(address, port, info)
    elif number == 69:
        raise crow.host.errors.CommandNotImplementedError(address, port, info)
    elif number == 70:
        raise crow.host.errors.CommandNotAllowedError(address, port, info)
    elif number == 71:
        raise crow.host.errors.InvalidCommandError(address, port, info)
    elif number == 72:
        raise crow.host.errors.IncorrectCommandSizeError(address, port, info)
    elif number == 73:
        raise crow.host.errors.MissingCommandDataError(address, port, info)
    elif number == 74:
        raise crow.host.errors.TooMuchCommandDataError(address, port, info)
    elif number >= 75 and number < 128:
        raise crow.host.errors.UnknownServiceError(address, port, number, info)
    elif number >= 128 and number < 255:
        raise crow.host.errors.ServiceError(address, port, number, info)
  
    raise RuntimeError("Programming error. An error number (" + str(number) + ") was not handled.")



