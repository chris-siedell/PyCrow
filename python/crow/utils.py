# Crow Utilities
# 24 April 2018
# Chris Siedell
# project: https://pypi.org/project/crow-serial/
# source: https://github.com/chris-siedell/PyCrow

# todo: revisit the errors raised by unpack functions

def unpack_int(info, transaction, num_bytes, prop_name, rsp_name, byteorder='big', signed=False):
    # Will raise RuntimeError if the value can not be extracted.
    # This function helps extract an integer from a response payload that was packed using the method
    #  employed by the CrowAdmin service and the Crow error response format.
    # Arguments:
    #   info - the dictionary to put the integer in
    #   transaction - a crow.Transaction object that, in addition to the response property, has an
    #                 arg_index property, which is the index into response where the next arg byte is located
    #   num_bytes - the number of bytes representing the integer
    #   prop_name - the name of the property, used for populating info and for composing error messages
    #   rsp_name - the name of the response, used for composing error messages
    # Before returning, info will be populated with the integer, and arg_index will be incremented by num_bytes.
    rsp = transaction.response
    ind = transaction.arg_index
    rem = len(rsp) - ind
    if rem < num_bytes:
        raise RuntimeError("The " + rsp_name + " response does not have enough bytes remaining for " + prop_name + ".")
    info[prop_name] = int.from_bytes(rsp[ind:ind+num_bytes], byteorder=byteorder, signed=signed)
    transaction.arg_index += num_bytes


def unpack_ascii(info, transaction, num_arg_bytes, prop_name, rsp_name):
    # Will raise RuntimeError if the value can not be extracted.
    # This function helps extract an ascii string from a response payload that was packed using the method
    #  employed by the CrowAdmin service and the Crow error response format. This packing method has three or
    #  four argument bytes, where the first two bytes are the offset to the string, and the next one or
    #  two bytes are the string length. The offset is from the beginning of the response. The length may
    #  include a terminating NUL. Multibyte values are in big-endian order.
    # Arguments:
    #   info - the dictionary to put the string in
    #   transaction - a crow.Transaction object that, in addition to the response property, has an
    #                 arg_index property, which is the index into response where the next arg byte is located
    #   num_arg_bytes - the number of argument bytes, which must be 3 or 4
    #   prop_name - the name of the property, used for populating info and for composing error messages
    #   rsp_name - the name of the response, used for composing error messages
    # Before returning, info will be populated with the string, and arg_index will be incremented by num_arg_bytes.
    rsp = transaction.response
    ind = transaction.arg_index
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
    transaction.arg_index += num_arg_bytes
    if offset + length > len(rsp):
        raise RuntimeError(prop_name + " exceeds the bounds of the " + rsp_name + " response.")
    info[prop_name] = rsp[offset:offset+length].decode(encoding='ascii', errors='replace')


def fletcher16(data):
    # Adapted from PropCRInternal.cpp (2 April 2018).
    # Overflow not a problem if called on short chunks of data (128 bytes is fine).
    lower = 0
    upper = 0
    for d in data:
        lower += d
        upper += lower
    lower %= 0xff
    upper %= 0xff
    return bytes([upper, lower])


def fletcher16_checkbytes(data):
    # Adapted from PropCRInternal.cpp (2 April 2018).
    # Overflow not a problem if called on short chunks of data (128 bytes is fine).
    lower = 0
    upper = 0
    for d in data:
        lower += d
        upper += lower
    check0 = 0xff - ((lower + upper) % 0xff)
    check1 = 0xff - ((lower + check0) % 0xff)
    return bytes([check0, check1])


