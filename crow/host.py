# Crow v2 Host
# April 2018 - in active development
# Chris Siedell
# http://siedell.com/projects/Crow/


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
                        raise crow.errors.NoResponseError(address, port, item['message'])
            raise RuntimeError("Program logic error. Expected to find a response with the correct token in parser results, but none was found.")
        else:
            # Failed to receive a response with the expected token.
            if byte_count == 0:
                raise crow.errors.NoResponseError(address, port, "Timeout occurred with no data received.")
            for item in results:
                if item['type'] == 'response':
                    if item['token'] != token:
                        raise crow.errors.NoResponseError(address, port, "A response was received, but with an incorrect identifying token. It may be a stale response, or the responding device may be misconfigured.")
                    else:
                        raise RuntimeError("Program logic error. Did not expect to find a response with the correct token in the parser results at this point.")
            raise crow.errors.NoResponseError(address, port, "Received " + str(byte_count) + " bytes, but could not parse a valid response.")


    def _handle_error_response(self, payload, address, port):

        # If the error response payload is empty we use UnspecifiedError by default.
        if len(payload) == 0:
            raise UnspecifiedError(address, port, {}, False)

        # The error type is in the bottom five bits of the first byte.
        number = payload[0] & 0x1f

        # details will hold any additional details included in the response.
        details = {}

        # This flag is set if the payload is not large enough for the details
        #  it claims to include.
        too_short = False

        # Optional byte E1 is a bitfield that specifies what additional details are included.
        if len(payload) >= 2:
            pay_ind = 2
            pay_rem = len(payload) - 2
            E1 = payload[1]
            if E1 & 1:
                # crow_version
                if pay_rem >= 1:
                    details['crow_version'] = payload[pay_ind]
                    pay_ind += 1
                    pay_rem -= 1
                else:
                    too_short = True
            if E1 & 2:
                # address
                if pay_rem >= 1:
                    details['address'] = payload[pay_ind]
                    pay_ind += 1
                    pay_rem -= 1
                else:
                    too_short = True
            if E1 & 4:
                # port
                if pay_rem >= 1:
                    details['port'] = payload[pay_ind]
                    pay_ind += 1
                    pay_rem -= 1
                else:
                    too_short = True
            if E1 & 8:
                # max_command_size
                if pay_rem >= 2:
                    details['max_command_size'] = int.from_bytes(payload[pay_ind:pay_ind+2], 'big')
                    pay_ind += 2
                    pay_rem -= 2
                else:
                    too_short = True
            if E1 & 16:
                # max_response_size
                if pay_rem >= 2:
                    details['max_response_size'] = int.from_bytes(payload[pay_ind:pay_ind+2], 'big')
                    pay_ind += 2
                    pay_rem -= 2
                else:
                    too_short = True
            if E1 & 32:
                # ascii_message
                if pay_rem >= 4:
                    ascii_offset = int.from_bytes(payload[pay_ind:pay_ind+2], 'big')
                    ascii_length = int.from_bytes(payload[pay_ind+2:pay_ind+4], 'big')
                    pay_ind += 4
                    pay_rem -= 4
                    if ascii_offset + ascii_length <= len(payload):
                        details['ascii_message'] = payload[ascii_offset:ascii_offset+ascii_length].decode(encoding='ascii', errors='replace')
                    else:
                        too_short = True
                else:
                    too_short = True

        if number == 0:
            raise crow.errors.UnspecifiedError(address, port, details, too_short)
        elif number == 1:
            raise crow.errors.DeviceUnavailableError(address, port, details, too_short)
        elif number == 2:
            raise crow.errors.DeviceIsBusyError(address, port, details, too_short)
        elif number == 3:
            raise crow.errors.CommandTooLargeError(address, port, details, too_short)
        elif number == 4:
            raise crow.errors.CorruptPayloadError(address, port, details, too_short)
        elif number == 5:
            raise crow.errors.PortNotOpenError(address, port, details, too_short)
        elif number == 6:
            raise crow.errors.LowResourcesError(address, port, details, too_short)
        elif number == 7:
            raise crow.errors.UnknownProtocolError(address, port, details, too_short)
        elif number == 8:
            raise crow.errors.RequestTooLargeError(address, port, details, too_short)
        elif number == 9:
            raise crow.errors.ImplementationFaultError(address, port, details, too_short)
        elif number == 10:
            raise crow.errors.ServiceFaultError(address, port, details, too_short)
        else:
            raise crow.errors.UnknownError(address, port, details, too_short, number)
    

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


