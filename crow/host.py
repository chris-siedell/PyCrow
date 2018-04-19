# Crow v2 Host
# April 2018 - in active development
# Chris Siedell
# https://github.com/chris-siedell/PyCrow


import time
import serial
import crow.parser
import crow.errors


class Host:

    def __init__(self):

        self.serial = None
        self.timeout = 0.25

        self._next_token = 2

        self._parser = crow.parser.Parser()


    def send_command(self, address=1, port=16, payload=None, response_expected=True, propcr_order=False):

        # Either returns None (when response_expected==False), a payload, or raises an exception.

        if self.serial is None:
            raise RuntimeError("send_command requires serial to be defined.")
        
        self.serial.reset_input_buffer()

        token = self._next_token
        self._next_token = (self._next_token + 1)%256

        packet = make_command_packet(address, port, response_expected, payload, token, propcr_order) # may raise ValueError
        
        self.serial.write(packet)

        if not response_expected:
            return None

        self._parser.reset()

        # The time limit is <time start receiving> + <timeout> + <time to transmit data at baudrate>.
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
                            self._handle_error_response(item['payload'], address, port) # this will raise an exception
                        else:
                            # normal response
                            return item['payload']
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
                        raise crow.errors.NoResponseError(address, port, byte_count, "An invalid response was received (incorrect token). It may be a stale response, or the responding device may be misconfigured.")
                    else:
                        raise RuntimeError("Program logic error. Should not have a response with the correct token in the parser results at this point.")
            raise crow.errors.NoResponseError(address, port, byte_count)


    def _handle_error_response(self, payload, address, port):

        # If the error response payload is empty we raise UnspecifiedDeviceError.
        if len(payload) == 0:
            raise UnspecifiedDeviceError()


        # The error number is in the first byte of the payload.
        number = payload[0]

        # rsp_name is used if there is an error parsing the error response
        rsp_name = "error number " + str(number)

        # details will hold any additional details included in the error
        details = {}

        # Optional byte E1 is a bitfield that specifies what additional details are included.
        if len(payload) >= 2:
         
            E1 = payload[1]

            # params holds the argument parsing parameters
            #  ind - index of next argument byte
            #  rem - remaining number of bytes available in payload
            params = {'ind': 2, 'rem': len(payload) - 2}

            if E1 & 1:
                # message (message_ascii_str)
                extract_ascii(details, response, params, 4, 'message', rsp_name)

            if E1 & 2:
                # crow_version
                extract_int(details, response, params, 1, 'crow_version', rsp_name)

            if E1 & 4:
                # max_command_size
                extract_int(details, response, params, 2, 'max_command_size', rsp_name)

            if E1 & 8:
                # max_response_size
                extract_int(details, response, params, 2, 'max_response_size', rsp_name)

            if E1 & 16:
                # address
                extract_int(details, response, params, 1, 'address', rsp_name)

            if E1 & 32:
                # port
                extract_int(details, response, params, 1, 'port', rsp_name)

            if E1 & 64:
                # service_identifier
                extract_ascii(details, response, params, 3, 'service_identifier', rsp_name)

        if number == 0:
            raise crow.errors.UnspecifiedDeviceError(address, port, details)
        elif number == 1:
            raise crow.errors.DeviceFaultError(address, port, details)
        elif number == 2:
            raise crow.errors.ServiceFaultError(address, port, details)
        elif number == 3:
            raise crow.errors.DeviceUnavailableError(address, port, details)
        elif number == 4:
            raise crow.errors.DeviceIsBusyError(address, port, details)
        elif number == 5:
            raise crow.errors.OversizedCommandError(address, port, details)
        elif number == 6:
            raise crow.errors.CorruptCommandPayloadError(address, port, details)
        elif number == 7:
            raise crow.errors.PortNotOpenError(address, port, details)
        elif number == 8:
            raise crow.errors.DeviceLowResourcesError(address, port, details)
        elif number >= 9 and number < 32:
            raise crow.errors.UnknownDeviceError(number, address, port, details)
        elif number >= 32 and number < 64:
            raise crow.errors.DeviceError(number, address, port, details)
        elif number == 64:
            raise crow.errors.UnspecifiedServiceError(address, port, details)
        elif number == 65:
            raise crow.errors.UnknownCommandFormatError(address, port, details)
        elif number == 66:
            raise crow.errors.RequestTooLargeError(address, port, details)
        elif number == 67:
            raise crow.errors.ServiceLowResourcesError(address, port, details)
        elif number == 68:
            raise crow.errors.CommandNotAvailableError(address, port, details)
        elif number == 69:
            raise crow.errors.CommandNotImplementedError(address, port, details)
        elif number == 70:
            raise crow.errors.CommandNotAllowedError(address, port, details)
        elif number == 71:
            raise crow.errors.InvalidCommandError(address, port, details)
        elif number == 72:
            raise crow.errors.IncorrectCommandSizeError(address, port, details)
        elif number == 73:
            raise crow.errors.MissingCommandDataError(address, port, details)
        elif number == 74:
            raise crow.errors.TooMuchCommandDataError(address, port, details)
        elif number >= 75 and number < 128:
            raise crow.errors.UnknownServiceError(number, address, port, details)
        elif number >= 128 and number < 255:
            raise crow.errors.ServiceError(number, address, port, details)
        else:
            raise RuntimeError("An error number was not correctly handled. Number: " + str(number) + ".")


def extract_int(info, response, params, num_bytes, prop_name, rsp_name, byteorder='big', signed=False):
    # info - the dict to put the property in
    # response - the buffer containing the response
    # params - parsing parameters dict, should have ind (index) and rem (remaining) keys, where ind+rem <= len(response)
    # num_bytes - the number of bytes in the integer (big-endian assumed)
    # prop_name - the name of the property, used for populating info and for composing error messages
    # rsp_name - the name of the response, used for composing error messages
    if params['rem'] < num_bytes:
        raise HostError("The " + rsp_name + " response does not have enough bytes remaining for " + prop_name + ".")
    info[prop_name] = int.from_bytes(response[params['ind']:params['ind']+num_bytes], byteorder=byteorder, signed=signed)
    params['ind'] += num_bytes
    params['rem'] -= num_bytes


def extract_ascii(info, response, params, num_arg_bytes, prop_name, rsp_name):
    # info - the dict to put the property in
    # response - the buffer containing the response
    # params - parsing parameters dict, should have ind (index) and rem (remaining) keys, where ind+rem <= len(response)
    # num_arg_bytes - the number of argument bytes (will either be 3 or 4; always 2 bytes for offset, followed by 1 or 2 bytes for length)
    # prop_name - the name of the property, used for populating info and for composing error messages
    # rsp_name - the name of the response, used for composing error messages
    if params['rem'] < num_arg_bytes:
        raise HostError("The " + rsp_name + " response does not have enough bytes remaining for " + prop_name + ".")
    ind = params['ind']
    offset = int.from_bytes(response[ind:ind+2], 'big')
    if num_arg_bytes == 3:
        length = response[ind+2]
    elif num_arg_bytes == 4:
        length = int.from_bytes(response[ind+2:ind+4], 'big')
    else:
        raise RuntimeError("Programming error -- num_arg_bytes should always be 3 or 4.")
    params['ind'] += num_arg_bytes
    params['rem'] -= num_arg_bytes
    if offset + length > len(response):
        raise HostError(prop_name + " exceeds the bounds of the " + rsp_name + " response.")
    info[prop_name] = response[offset:offset+length].decode(encoding='ascii', errors='replace')


def make_command_packet(address, port, response_expected, payload=None, token=0, propcr_order=False):

    if address < 0 or address > 31:
        raise ValueError('address must be 0 to 31')

    if port < 0 or port > 255:
        raise ValueError('port must be 0 to 255')

    if address == 0 and response_expected:
        raise ValueError('broadcast commands (address 0) must have response_expected=False')

    if token < 0 or token > 255:
        raise ValueError('token must be 0 to 255')

    # begin with a packet bytearray of the required length
    if payload is not None:
        paySize = len(payload)
        if paySize > 2047:
            raise ValueError('payload may have 0 to 2047 bytes')
        remainder = paySize%128
        bodySize = (paySize//128)*130 + ((remainder + 2) if (remainder > 0) else 0)
    else:
        paySize = 0
        bodySize = 0
    packet = bytearray(7 + bodySize)

    # CH0, CH1
    s = paySize.to_bytes(2, 'big')
    packet[0] = (s[0] << 3) | 1
    packet[1] = s[1]

    # CH2
    packet[2] = address
    if response_expected:
        packet[2] |= 0x80

    # CH3
    packet[3] = port

    # CH4
    packet[4] = token

    # CH5, CH6 
    check = fletcher16_checkbytes(packet[0:5])
    packet[5] = check[0]
    packet[6] = check[1]

    # send the payload in chunks with up to 128 payload bytes followed by 2 F16 check bytes
    pktInd = 7
    if propcr_order:
        # PropCR uses non-standard payload byte ordering (for command payloads only)
        payRem = paySize
        payInd = 0
        while payRem > 0:
            chunkSize = min(payRem, 128)
            payRem -= chunkSize
            startPktIndex = pktInd

            # in PropCR every group of up to four bytes is reversed
            chunkRem = chunkSize
            while chunkRem > 0:
                groupSize = min(chunkRem, 4)
                chunkRem -= groupSize
                packet[pktInd:pktInd+groupSize] = payload[payInd:payInd+groupSize][::-1]
                pktInd += groupSize
                payInd += groupSize
            
            check = fletcher16_checkbytes(packet[startPktIndex:pktInd])
            packet[pktInd] = check[0]
            packet[pktInd+1] = check[1]
            pktInd += 2
    else:
        # standard order
        payRem = paySize
        payInd = 0
        while payRem > 0:
            chunkSize = min(payRem, 128)
            payRem -= chunkSize
            nextPayInd = payInd + chunkSize
            packet[pktInd:pktInd+chunkSize] = payload[payInd:nextPayInd]
            pktInd += chunkSize
            check = fletcher16_checkbytes(payload[payInd:nextPayInd])
            packet[pktInd] = check[0]
            packet[pktInd+1] = check[1]
            pktInd += 2
            payInd = nextPayInd

    return packet

    
def fletcher16(data):
    # adapted from PropCRInternal.cpp (2 April 2018)
    # overflow not a problem if called on short chunks of data (128 bytes or less)
    lower = 0
    upper = 0
    for d in data:
        lower += d
        upper += lower
    lower %= 0xff
    upper %= 0xff
    return bytes([upper, lower])


def fletcher16_checkbytes(data):
    # adapted from PropCRInternal.cpp (2 April 2018)
    # overflow not a problem if called on short chunks of data (128 bytes or less)
    lower = 0
    upper = 0
    for d in data:
        lower += d
        upper += lower
    check0 = 0xff - ((lower + upper) % 0xff)
    check1 = 0xff - ((lower + check0) % 0xff)
    return bytes([check0, check1])


