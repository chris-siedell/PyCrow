# Crow Host (v1 standard)
# 6 April 2018
# Chris Siedell
# http://www.siedell.com/projects/Crow/


import time
import serial
import crow.parser


class Host:

    def __init__(self):

        self.serial = None
        self.timeout = 0.25

        self._next_token = 2

        self._parser = crow.parser.Parser()


    def send_command(self, address=1, port=16, payload=None, response_expected=True, propcr_order=False):

        if self.serial is None:
            raise RuntimeError("send_command requires serial to be defined")
        
        self.serial.reset_input_buffer()

        token = self._next_token
        self._next_token = (self._next_token + 1)%256

        packet = make_command_packet(address, port, response_expected, payload, token, propcr_order)
        
        self.serial.write(packet)

        if not response_expected:
            return []

        results = []
        self._parser.reset()

        # the time limit is <time start receiving> + <timeout> + <time necessary to transmit data at baudrate>
        seconds_per_byte = 10 / self.serial.baudrate
       
        now = time.perf_counter()
        time_limit = now + self.timeout + seconds_per_byte*self._parser.min_bytes_expected
        
        while self._parser.min_bytes_expected > 0 and now < time_limit:
            
            self.serial.timeout = time_limit - now 
            data = self.serial.read(self._parser.min_bytes_expected)
            results += self._parser.parse_data(data)
            
            time_limit += seconds_per_byte*len(data)
            now = time.perf_counter()

        # convert responses with incorrect tokens into errors
        for item in results:
            if item['type'] == 'response':
                if item['token'] != token:
                    item['type'] = 'error'
                    item['message'] = 'response received with incorrect token -- possibly a late or stale response'

        return results


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


