# Crow Utilities
# Version 0.2.0 (alpha/experimental)
# 19 April 2018
# Chris Siedell
# https://github.com/chris-siedell/PyCrow


def extract_int(info, params, num_bytes, prop_name, rsp_name, byteorder='big', signed=False):
    # Will raise RuntimeError if the value can not be extracted.
    # This function helps extract an integer from a response payload that was packed using the method
    #  employed by the CrowAdmin service and the Crow error response format.
    # Arguments:
    #   info - the dictionary to put the integer in
    #   params - a dictionary with these properties:
    #               response - the response payload containing the integer
    #               arg_index - the index into response where the next argument byte (i.e. first integer byte) is located
    #   num_bytes - the number of bytes representing the integer
    #   prop_name - the name of the property, used for populating info and for composing error messages
    #   rsp_name - the name of the response, used for composing error messages
    # Before returning, info will be populated with the integer, and arg_index will be incremented by num_bytes.
    rsp = params['response']
    ind = params['arg_index']
    rem = len(rsp) - ind
    if rem < num_bytes:
        raise RuntimeError("The " + rsp_name + " response does not have enough bytes remaining for " + prop_name + ".")
    info[prop_name] = int.from_bytes(rsp[ind:ind+num_bytes], byteorder=byteorder, signed=signed)
    params['arg_index'] += num_bytes


def extract_ascii(info, params, num_arg_bytes, prop_name, rsp_name):
    # Will raise RuntimeError if the value can not be extracted.
    # This function helps extract an ascii string from a response payload that was packed using the method
    #  employed by the CrowAdmin service and the Crow error response format. This packing method has three or
    #  four argument bytes, where the first two bytes are the offset to the string, and the next one or
    #  two bytes are the string length. The offset is from the beginning of the response. The length may
    #  include a terminating NUL. Multibyte values are in big-endian order.
    # Arguments:
    #   info - the dictionary to put the string in
    #   params - a dictionary with these properties:
    #               response - the response payload containing the string
    #               arg_index - the index into response where the next argument byte is located
    #   num_arg_bytes - the number of argument bytes, which must be 3 or 4
    #   prop_name - the name of the property, used for populating info and for composing error messages
    #   rsp_name - the name of the response, used for composing error messages
    # Before returning, info will be populated with the string, and arg_index will be incremented by num_arg_bytes.
    rsp = params['response']
    ind = params['arg_index']
    rem = len(rsp) - ind
    if rem < num_arg_bytes:
        raise RuntimeError("The " + rsp_name + " response does not have enough bytes remaining for " + prop_name + ".")
    offset = int.from_bytes(rsp[ind:ind+2], 'big')
    if num_arg_bytes == 3:
        length = rsp[ind+2]
    elif num_arg_bytes == 4:
        length = int.from_bytes(rsp[ind+2:ind+4], 'big')
    else:
        raise RuntimeError("Programming error. num_arg_bytes should always be 3 or 4.")
    params['arg_index'] += num_arg_bytes
    if offset + length > len(rsp):
        raise RuntimeError(prop_name + " exceeds the bounds of the " + rsp_name + " response.")
    info[prop_name] = rsp[offset:offset+length].decode(encoding='ascii', errors='replace')


def make_command_packet(address, port, response_expected, payload, token, propcr_order=False):

    if address < 0 or address > 31:
        raise ValueError('address must be 0 to 31.')

    if port < 0 or port > 255:
        raise ValueError('port must be 0 to 255.')

    if address == 0 and response_expected:
        raise ValueError('Broadcast commands (address 0) must have response_expected=False.')

    if token < 0 or token > 255:
        raise ValueError('token must be 0 to 255.')

    # begin with a bytearray of the required packet length
    # body_size is the size of the payload plus the payload check bytes
    if payload is not None:
        pay_size = len(payload)
        if pay_size > 2047:
            raise ValueError("The payload must be 2047 bytes or less.")
        remainder = pay_size%128
        body_size = (pay_size//128)*130 + ((remainder + 2) if (remainder > 0) else 0)
    else:
        pay_size = 0
        body_size = 0
    packet = bytearray(7 + body_size)

    # The command header is always 7 bytes.

    # CH0, CH1
    s = pay_size.to_bytes(2, 'big')
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
    pkt_ind = 7
    if propcr_order:
        # PropCR uses non-standard payload byte ordering (for command payloads only)
        pay_rem = pay_size
        pay_ind = 0
        while pay_rem > 0:
            chk_size = min(pay_rem, 128)
            pay_rem -= chk_size
            startPktIndex = pkt_ind

            # in PropCR every group of up to four bytes is reversed
            chunkRem = chk_size
            while chunkRem > 0:
                groupSize = min(chunkRem, 4)
                chunkRem -= groupSize
                packet[pkt_ind:pkt_ind+groupSize] = payload[pay_ind:pay_ind+groupSize][::-1]
                pkt_ind += groupSize
                pay_ind += groupSize
            
            check = fletcher16_checkbytes(packet[startPktIndex:pkt_ind])
            packet[pkt_ind] = check[0]
            packet[pkt_ind+1] = check[1]
            pkt_ind += 2
    else:
        # standard order
        pay_rem = pay_size
        pay_ind = 0
        while pay_rem > 0:
            chk_size = min(pay_rem, 128)
            pay_rem -= chk_size
            next_pay_ind = pay_ind + chk_size
            packet[pkt_ind:pkt_ind+chk_size] = payload[pay_ind:next_pay_ind]
            pkt_ind += chk_size
            check = fletcher16_checkbytes(payload[pay_ind:next_pay_ind])
            packet[pkt_ind] = check[0]
            packet[pkt_ind+1] = check[1]
            pkt_ind += 2
            pay_ind = next_pay_ind

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


