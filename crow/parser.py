# Crow Packet Parser
# 24 April 2018
# Chris Siedell
# project: https://pypi.org/project/crow-serial/
# source: https://github.com/chris-siedell/PyCrow


class Parser:

    # As of April 2018 this parser just looks for response packets.
    # todo list:
    #   - add support for command packets
    #   - add ignore_extra and ignore_leftover options to parse_data

    def __init__(self):

        # Minimum number of bytes still expected by parser to complete the transaction.
        #  This will always be non-zero unless a specific token is passed to parse_data.
        self.min_bytes_expected = 5

        # internal stuff
        self._state = 0
        self._is_error = False
        self._token = 0
        self._pay_buff = bytearray(2047)
        self._pay_size = 0
        self._header = bytearray(5)
        self._pay_ind = 0
        self._chk_rem = 0
        self._pay_rem = 0
        self._upper_F16 = 0
        self._lower_F16 = 0

    def reset(self):
        self._state = 0
        self.min_bytes_expected = 5

    def parse_data(self, data, token=None, reset=False):

        # This method parses a data stream in search of Crow response packets. The
        #  data stream is provided using the data argument (a bytes-like object),
        #  potentially over several calls to parse_data. In other words, data does not
        #  need to contain a complete packet since the parser stores information as it
        #  is given and remembers its state between calls. The optional reset argument
        #  can be used to reset the parser's state.
        
        # The parser's min_bytes_expected property tells the user how much more data
        #  the parser needs (at minimum) in order to receive a complete response packet.
        #  It will always be non-zero unless the token argument is used.

        # The token argument can be used to inform the parser that it should
        #  look for a specific response. If token is defined then the parser will
        #  return as soon as it receives a response with that token. It will set
        #  min_bytes_expected to 0, and if there are any bytes in data after the
        #  response they will be returned as 'leftover' bytes. 

        # This method returns a list of parser results. A result describes a sequence of
        #  data given to the parser, potentially over several parse_data calls. Each
        #  result is a dictionary with a type property. The result types:
        #  type: 'error' - a response packet was received, but it could not be parsed
        #        'extra' - extraneous data, not recognized as part of a response packet
        #        'response' - a parsable response
        #        'leftover' - data following an expected (specific token) response
        # error properties:
        #  token (int)
        #  message (string)
        # extra properties:
        #  data (bytes)
        # leftover properties:
        #  data (bytes)
        # response properties:
        #  is_error (bool)
        #  token (int)
        #  payload (bytes)

        # states (action to be performed on next byte):
        #  0 - buffer RH0
        #  1 - buffer RH1
        #  2 - buffer RH2
        #  3 - buffer RH3
        #  4 - buffer RH4 and evaluate RH0-RH4
        #  5 - process response payload byte
        #  6 - process response payload F16 upper sum
        #  7 - process response payload F16 lower sum
        #  8 - process response body byte after failed payload F16

        if reset:
            self.reset()

        result = []

        extra_data = bytearray()

        data_ind = 0
        data_size = len(data)

        while data_ind < data_size:

            byte = data[data_ind]
            data_ind += 1

            if self._state == 5:
                # process payload byte
                self.min_bytes_expected -= 1
                self._lower_F16 += byte
                self._upper_F16 += self._lower_F16
                self._pay_buff[self._pay_ind] = byte
                self._pay_ind += 1
                self._chk_rem -= 1
                if self._chk_rem == 0:
                    # all chunk payload bytes received
                    self._state = 6
            elif self._state == 6:
                # process payload F16 upper sum
                self.min_bytes_expected -= 1
                if self._upper_F16%0xff == byte%0xff:
                    # upper F16 correct
                    self._state = 7
                else:
                    # bad payload F16 upper sum
                    self._state = 8
            elif self._state == 7:
                # process payload F16 lower sum
                self.min_bytes_expected -= 1
                if self._lower_F16%0xff == byte%0xff:
                    # lower F16 correct
                    if self._pay_rem == 0:
                        # packet done -- all bytes received
                        result.append({'type':'response', 'is_error':self._is_error, 'token':self._token, 'payload':self._pay_buff[0:self._pay_size]})
                        self.min_bytes_expected = 5
                        self._state = 0
                        if token is not None and token == self._token:
                            if data_ind < data_size:
                                result.append({'type':'leftover', 'data':data[data_ind:data_size]})
                            self.min_bytes_expected = 0
                            return result
                    else:
                        # more payload bytes will arrive in another chunk
                        self._chk_rem = min(self._pay_rem, 128)
                        self._pay_rem -= self._chk_rem
                        self._upper_F16 = self._lower_F16 = 0
                        self._state = 5
                else:
                    # bad payload F16 lower sum
                    self._state = 8
            elif self._state == 0:
                # buffer RH0 
                self.min_bytes_expected = 4
                self._header[0] = byte
                self._state = 1
            elif self._state == 1:
                # buffer RH1
                self.min_bytes_expected = 3
                self._header[1] = byte
                self._state = 2
            elif self._state == 2:
                # buffer RH2
                self.min_bytes_expected = 2
                self._header[2] = byte
                self._state = 3
            elif self._state == 3:
                # buffer RH3
                self.min_bytes_expected = 1
                self._header[3] = byte
                self._state = 4
            elif self._state == 4:
                # buffer RH4 and evaulate
                self._header[4] = byte
                if response_header_is_valid(self._header):
                    # valid header
                    # first off, dispose of any collected extraneous bytes 
                    if len(extra_data) > 0:
                        result.append({'type':'extra', 'data':extra_data})
                        extra_data = bytearray()
                    # extract packet parameters
                    self._is_error = bool(self._header[0] & 0x80)
                    self._header[0] = (self._header[0] & 0x38) >> 3
                    self._pay_size = int.from_bytes(self._header[0:2], 'big')
                    self._token = self._header[2]
                    if self._pay_size > 0:
                        # prepare for first chunk of payload
                        remainder = self._pay_size%128
                        self.min_bytes_expected = (self._pay_size//128)*130 + ((remainder + 2) if (remainder > 0) else 0)
                        self._pay_rem = self._pay_size
                        self._chk_rem = min(self._pay_rem, 128)
                        self._pay_rem -= self._chk_rem
                        self._upper_F16 = self._lower_F16 = 0
                        self._pay_ind = 0
                        self._state = 5
                    else:
                        # packet is good, but empty (no payload)
                        result.append({'type':'response', 'is_error':self._is_error, 'token':self._token, 'payload':bytearray()})
                        self.min_bytes_expected = 5
                        self._state = 0
                        if token is not None and token == self._token:
                            if data_ind < data_size:
                                result.append({'type':'leftover', 'data':data[data_ind:data_size]})
                            self.min_bytes_expected = 0
                            return result
                else:
                    # invalid header
                    # stay at state 4 but shift header bytes down and collect extraneous data
                    self.min_bytes_expected = 1
                    extra_data.append(self._header.pop(0))
                    self._header.append(0)
            elif self._state == 8:
                # process body byte after failed payload F16
                self.min_bytes_expected -= 1
                if self.min_bytes_expected == 0:
                    result.append({'type':'error', 'token':self._token, 'message':'The response packet has bad checksums.'})
                    self.min_bytes_expected = 5
                    self._state == 0
                    if token is not None and token == self._token:
                        if data_ind < data_size:
                            result.append({'type':'leftover', 'data':data[data_ind:data_size]})
                        self.min_bytes_expected = 0
                        return result
            else:
                raise RuntimeError("Programming error. Invalid state in Parser.")

        if len(extra_data) > 0:
            result.append({'type':'extra', 'data':extra_data})

        return result


def response_header_is_valid(header):
    # Given a bytes-like object of len >= 5 (not checked) this function returns a bool.
    if header[0] & 0x47 != 0x02:
        # bad reserved bits in RH0
        return False
    upper = lower = header[0]
    lower += header[1]
    upper += lower
    lower += header[2]
    upper += lower
    if upper%0xff != header[3]%0xff:
        # bad upper F16 checksum
        return False
    if lower%0xff != header[4]%0xff:
        # bad lower F16 checksum
        return False
    return True

