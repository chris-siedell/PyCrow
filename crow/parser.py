# Crow Response Parser
# 3 April 2018
# Chris Siedell
# http://www.siedell.com/projects/Crow/


class Parser:

    def __init__(self):

        # Minimum number of bytes still expected by parser to complete the transaction.
        self.min_bytes_expected = 0

        # internal stuff
        self._payload_size = 0
        self._is_error = False
        self._token = 0
        self._payload = bytearray(2047)
        self._state = 0
        self._header = bytearray(5)
        self._payloadIndex = 0
        self._chunkRemaining = 0
        self._payloadRemaining = 0
        self._bodyRemaining = 0
        self._upperF16  = 0
        self._lowerF16 = 0

    def reset(self):
        self._state = 0
        self.min_bytes_expected = 5

    def parse_data(self, data, reset=False):

        # returns list of dictionaries which all have a type property:
        #  type: 'error' - for parsing errors
        #        'extra' - extraneous data
        #        'response' - a correctly formatted response
        # error properties:
        #  message (string)
        # extra properties:
        #  data (bytearray)
        # response properties:
        #  is_error (bool)
        #  token (int)
        #  payload (bytearray)

        # states (action to be performed on next byte):
        #  0 - buffer RH0
        #  1 - buffer RH1
        #  2 - buffer RH2
        #  3 - buffer RH3
        #  4 - buffer RH4 and evaluate
        #  5 - process response payload byte
        #  6 - process response payload F16 upper sum
        #  7 - process response payload F16 lower sum
        #  8 - process response body byte after failed payload F16

        if reset:
            self.reset()

        result = []

        extra_data = bytearray()

        dataInd = 0
        dataSize = len(data)

        while dataInd < dataSize:

            byte = data[dataInd]
            dataInd += 1

            if self._state == 5:
                # process payload byte
                self.min_bytes_expected -= 1
                self._lowerF16 += byte
                self._upperF16 += self._lowerF16
                self._payload[self._payloadIndex] = byte
                self._payloadIndex += 1
                self._chunkRemaining -= 1
                if self._chunkRemaining == 0:
                    # all chunk payload bytes received
                    self._state = 6
            elif self._state == 6:
                # process payload F16 upper sum
                self.min_bytes_expected -= 1
                if self._upperF16%0xff == byte%0xff:
                    # upper F16 correct
                    self._state = 7
                else:
                    # bad payload F16 upper sum
                    self._state = 8
            elif self._state == 7:
                # process payload F16 lower sum
                self.min_bytes_expected -= 1
                if self._lowerF16%0xff == byte%0xff:
                    # lower F16 correct
                    if self._payloadRemaining == 0:
                        # packet done -- all bytes received
                        result.append({'type':'response', 'is_error':self._is_error, 'token':self._token, 'payload':self._payload[0:self._payload_size]})
                        self.min_bytes_expected = 0
                        self._state = 0
                    else:
                        # more payload bytes will arrive in another chunk
                        self._chunkRemaining = min(self._payloadRemaining, 128)
                        self._payloadRemaining -= self._chunkRemaining
                        self._upperF16 = self._lowerF16 = 0
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
                self.min_bytes_expected = 0
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
                    self._payload_size = int.from_bytes(self._header[0:2], 'big')
                    self._token = self._header[2]
                    if self._payload_size > 0:
                        # prepare for first chunk of payload
                        remainder = self._payload_size%128
                        self.min_bytes_expected = (self._payload_size//128)*130 + ((remainder + 2) if (remainder > 0) else 0)
                        self._chunkRemaining = min(self._payload_size, 128)
                        self._payloadRemaining = self._payload_size - self._chunkRemaining
                        self._upperF16 = self._lowerF16 = 0
                        self._payloadIndex = 0
                        self._state = 5
                    else:
                        # packet is good, but empty (no payload)
                        result.append({'type':'response', 'is_error':self._is_error, 'token':self._token, 'payload':bytearray()})
                        self.min_bytes_expected = 0
                        self._state = 0
                else:
                    # bad header
                    # stay at state 4 but shift header bytes down and collect extraneous data
                    self.min_bytes_expected = 1
                    extra_data.append(self._header.pop(0))
                    self._header.append(0)
            elif self._state == 8:
                # process body byte after failed payload F16
                self.min_bytes_expected -= 1
                if self.min_bytes_expected == 0:
                    result.append({'type':'error', 'message':'response packet had bad checksums'})
                    self.min_bytes_expected = 0
                    self._state == 0
            else:
                raise Exception("invalid state in ResponseParser")

        if len(extra_data) > 0:
            result.append({'type':'extra', 'data':extra_data})

        return result


def response_header_is_valid(header):
    # Given a bytes-like object of len >= 5 this method returns a bool.
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

