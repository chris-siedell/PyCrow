# Crow Host
# Version 0.2.0 (alpha/experimental)
# 19 April 2018
# Chris Siedell
# https://github.com/chris-siedell/PyCrow

# todo: introduce params method CrowAdmin
# todo: simplify errors

import time
import serial
import crow.errors
import crow.parser
from crow.utils import make_command_packet


class Host:

    def __init__(self):

        self.serial = None
        self.timeout = 0.25

        self._next_token = 2

        self._parser = crow.parser.Parser()


    def send_command(self, address=1, port=32, payload=None, response_expected=True, propcr_order=False):

        # Either returns None (when response_expected==False), a payload, or raises an exception.

        if self.serial is None:
            raise RuntimeError("send_command requires serial to be defined.")
        
        self.serial.reset_input_buffer()

        token = self._next_token
        self._next_token = (self._next_token + 1)%256

        packet = make_command_packet(address, port, response_expected, payload, token, propcr_order)
        
        self.serial.write(packet)

        if not response_expected:
            return None

        self._parser.reset()

        # The time limit is <time start receiving> + <timeout> + <time to transmit data at baudrate>.
        # todo: fix
        seconds_per_byte = 10 / self.serial.baudrate
        now = time.perf_counter()
        time_limit = now + self.timeout

        byte_count = 0
        results = []
        
        while self._parser.min_bytes_expected > 0 and now < time_limit:
            
            self.serial.timeout = time_limit - now 
            data = self.serial.read(self._parser.min_bytes_expected)
            byte_count += len(data)
            results += self._parser.parse_data(data, token)
            
            time_limit += seconds_per_byte*len(data)
            now = time.perf_counter()
        
        if self._parser.min_bytes_expected == 0:
            # This means we received a response with the expected token.
            # Currently we are ignoring other items in results besides the expected response (i.e. other responses, extraneous bytes, leftovers).
            for item in results:
                if item['type'] == 'response':
                    if item['token'] == token:
                        if item['is_error']:
                            # error response
                            item['address'] = address
                            item['port'] = port
                            raise_remote_error(item)
                        else:
                            # normal response
                            return item['response']
                elif item['type'] == 'error':
                    if item['token'] == token:
                        # A packet was received with the correct token, but it could not be parsed.
                        raise crow.errors.NoResponseError(address, port, byte_count, item['message'])
            raise RuntimeError("Program logic error. Expected to find a response with the correct token in parser results, but none was found.")
        else:
            # Failed to receive a response with the expected token.
            if byte_count == 0:
                raise crow.errors.NoResponseError(address, port, byte_count)
            for item in results:
                if item['type'] == 'response':
                    if item['token'] != token:
                        raise crow.errors.NoResponseError(address, port, byte_count, "An invalid response was received (incorrect token). It may be a stale response, or the responding device may have malfunctioned.")
                    else:
                        raise RuntimeError("Program logic error. Should not have a response with the correct token in the parser results at this point.")
            raise crow.errors.NoResponseError(address, port, byte_count)


def raise_remote_error(params):

    rsp = params['response']
    address = params['address']
    port = params['port']

    # If the error response payload is empty we raise UnspecifiedDeviceError.
    if len(rsp) == 0:
        raise crow.errors.UnspecifiedDeviceError(address, port, None)

    # The error number is in the first byte of the payload.
    number = rsp[0]

    # rsp_name is used if there is an error parsing the error response
    rsp_name = "error number " + str(number)

    # info will hold any additional details included in the error
    info = {}

    # Optional byte E1 is a bitfield that specifies what additional details are included.
    if len(rsp) >= 2:
        E1 = rsp[1]
        params['arg_index'] = 2
        try:
            # The extract_* functions may raise RuntimeError.
            if E1 & 1:
                extract_ascii(info, params, 4, 'message', rsp_name)
            if E1 & 2:
                extract_int(info, params, 1, 'crow_version', rsp_name)
            if E1 & 4:
                extract_int(info, params, 2, 'max_command_size', rsp_name)
            if E1 & 8:
                extract_int(info, params, 2, 'max_response_size', rsp_name)
            if E1 & 16:
                extract_int(info, params, 1, 'address', rsp_name)
            if E1 & 32:
                extract_int(info, params, 1, 'port', rsp_name)
            if E1 & 64:
                extract_ascii(info, params, 3, 'service_identifier', rsp_name)
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
  
    raise RuntimeError("Programming error. An error number (" + str(number) + ") was not handled.")



