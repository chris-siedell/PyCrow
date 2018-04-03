
import random



def createCommand(address=1, port=0, isUser=True, muteResponse=False, payload=None, token=None, propcrOrder=False):

    _token = random.randint(0, 255)

    if address < 1 or address > 31:
        raise ValueError('address must be 1 to 31')

    if port < 0 or port > 65535:
        raise ValueError('port must be a two-byte value (0 to 65535)')

    if address == 0 and not muteResponse:
        raise ValueError('broadcast commands (address 0) must have muteResponse=True')

    if token is None:
        token = _token
        _token = (_token + 1)%256
    else:
        if token < 0 or token > 255:
            raise ValueError('token must be a one-byte value (0 to 255)')

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
    packetSize = (6 + bodySize) if (port == 0) else (8 + bodySize)
    packet = bytearray(packetSize)

    # From "Crow Specification v1.txt" (note "protocol number" is "port"):
    #
    #   A command header consists of 6 or 8 bytes with the following format:
    # 
    #                |7|6|5|4|3|2|1|0|
    #          ------|---------------|
    #           CH0  |0|1|0|T|0| Lu  |
    #           CH1  |      Ll       |
    #           CH2  |       K       |
    #           CH3  |X|M|0|    A    |
    #          (CH4) |      Pu       |
    #          (CH5) |      Pl       |
    #           CH6  |      C0       |
    #           CH7  |      C1       |
    # 
    #   The fields have the following definitions:
    # 
    #     L = Lu << 8 | Ll = payload length (0-2047 bytes, exclusive of error detection bytes)
    #     T = command type: 0 - admin,
    #                       1 - user
    #     K = token, a byte that the device must send with all responses to this command
    #     A = address (0-31)
    #     M = muted responses flag: 0 - response expected,
    #                               1 - responses forbidden (must be set if address = 0)
    #     X = protocol specified: 0 - none specified, so use implicit value of 0; no CH4 and CH5 bytes
    #                             1 - protocol is specified in bytes CH4 and CH5, to follow
    #     P = Pu << 8 | Pl = protocol number, if X=1 (if X=0 P is implicitly set to 0)
    #     C0, C1 = check bytes that cause the running Fletcher 16 checksum to evaluate to zero if initialized to zero before CH0.
    
    # CH0, CH1
    s = paySize.to_bytes(2, 'big')
    ch0 = 0x40 | s[0]
    if isUser:
        ch0 |= 0x10
    packet[0] = ch0
    packet[1] = s[1]

    # CH2
    packet[2] = token

    # CH3
    ch3 = address
    if muteResponse:
        ch3 |= 0x40
    if port > 0:
        ch3 |= 0x80
        # CH4, CH5 - explicit port
        p = port.to_bytes(2, 'big')
        packet[4] = p[0]
        packet[5] = p[1]
        pktInd = 6
    else:
        pktInd = 4
    packet[3] = ch3

    # CH6, CH7 
    check = fletcher16Checkbytes(packet[0:pktInd])
    packet[pktInd] = check[0]
    packet[pktInd+1] = check[1]
    pktInd += 2

    # send the payload in chunks with up to 128 payload bytes followed by 2 F16 check bytes
    if propcrOrder:
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
            
            check = fletcher16Checkbytes(packet[startPktIndex:pktInd])
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
            check = fletcher16Checkbytes(payload[payInd:nextPayInd])
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


def fletcher16Checkbytes(data):
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


