# Crow Response Parser
# 3 April 2018
# Chris Siedell
# http://www.siedell.com/projects/Crow/


class Parser:

    def __init__(self):

        # Minimum number of bytes still expected by parser to complete the transaction.
        self.min_bytes_expected = 0

        # Indicates if a final response has been received.
        self.final_received = False

        # internal stuff
        self._is_final = True
        self._payload_size = 0
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
        self.final_received = False
        self.min_bytes_expected = 5

    def parse_data(self, data, reset=False):

        # returns list of dictionaries which all have a type property:
        #  type: 'error', 'extra', or 'response'
        # error properties:
        #  message (string)
        # extra properties:
        #  data (bytearray)
        # response properties:
        #  is_final (bool)
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
                        result.append({'type':'response', 'is_final':self._is_final, 'token':self._token, 'payload':self._payload[0:self._payloadSize]})
                        if self._is_final:
                            self.min_bytes_expected = 0
                            self.final_received = True
                        else:
                            self.min_bytes_expected = 5
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
                    self._is_final = bool(self._header[0] & 0x10)
                    self._header[0] &= 0x03
                    self._payloadSize = int.from_bytes(self._header[0:2], 'big')
                    self._token = self._header[2]
                    if self._payloadSize > 0:
                        # prepare for first chunk of payload
                        remainder = self._payloadSize%128
                        self.min_bytes_expected = (self._payloadSize//128)*130 + ((remainder + 2) if (remainder > 0) else 0)
                        self._chunkRemaining = min(self._payloadSize, 128)
                        self._payloadRemaining = self._payloadSize - self._chunkRemaining
                        self._upperF16 = self._lowerF16 = 0
                        self._payloadIndex = 0
                        self._state = 5
                    else:
                        # packet is good, but empty (no payload)
                        result.append({'type':'response', 'is_final':self._is_final, 'token':self._token, 'payload':bytearray()})
                        if self._is_final:
                            self.min_bytes_expected = 0
                            self.final_received = True
                        else:
                            self.min_bytes_expected = 5
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
                    if self._is_final:
                        self.min_bytes_expected = 0
                        self.final_received = True
                    else:
                        self.min_bytes_expected = 5
                    self._state == 0
            else:
                raise Exception("invalid state in ResponseParser")

        if len(extra_data) > 0:
            result.append({'type':'extra', 'data':extra_data})

        return result


def response_header_is_valid(header):
    # Given a bytes-like object of len >= 5 this method returns a bool.
    # From "Crow Specification v1.txt":
    #   
    #   A response header is always 5 bytes and has the following format:
    #   
    #                   |7|6|5|4|3|2|1|0|
    #             ------|---------------|
    #              RH0  |1|0|0|F|0| Lu  |
    #              RH1  |      Ll       |
    #              RH2  |       K       |
    #              RH3  |      Fu       |
    #              RH4  |      Fl       |
    #   
    #   The fields have the following definitions:
    #   
    #       L = Lu << 8 | Ll = payload length (0-2047 bytes, exclusive of error detection bytes)
    #       F = final flag: 0 - intermediate response
    #                       1 - final response
    #       K = token, the same value that was sent by the host with the command
    #       Fu, Fl - The Fletcher 16 checksum after being initialized to zero and processing
    #                bytes RH0-RH2. Fu is the upper sum, and Fl is the lower sum.
    if header[0] & 0xE8 != 0x80:
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
