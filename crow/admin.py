
import time

# todo: convert CrowAdminErrors to ClientErrors

class CrowAdminError(RuntimeError):
    pass


class CrowAdmin():

    def __init__(self):
        self.host = None

        self.address = 1
        self.port = 0
        self.propcr_order = False


    def ping(self):
        start = time.perf_counter()
        self._send_command(is_ping=True)
        return time.perf_counter() - start


    def echo(self, data):
        response = self._send_command(code=0, parameters=data)
        # The correct response consists of the three byte initial header (already verified), followed
        # by a verbatim echo of the data.
        expected_len = len(data) + 3
        if len(response) < expected_len:
            raise crow.errors.InvalidResponseError("The echo response has too few bytes.")
        elif len(response) > expected_len:
            raise crow.errors.InvalidResponseError("The echo response has too many bytes.")
        if response[3:] != data:
            raise crow.errors.InvalidResponseError("The echo response has incorrect bytes.")


    def host_presence(self, filler):
        response = self._send_command(code=0, parameters=filler, response_expected=False)

    def _extract_ascii(self, info, response, params, prop_name, cmd_name):
        # params should have ind (index) and rem (remaining) keys, where ind+rem <= len(response)
        if params['rem'] < 3:
            raise CrowAdminError("The " + cmd_name + " response has too few bytes for " + prop_name + ".")
        ind = params['ind']
        offset = int.from_bytes(response[ind:ind+2], 'big')
        length = response[ind+2]
        params['ind'] += 3
        params['rem'] -= 3
        if offset + length > len(response):
            raise CrowAdminError(prop_name + " exceeds the bounds of the " + cmd_name + " response.")
        info[prop_name] = response[offset:offset+length].decode(encoding='ascii', errors='replace')


    def get_device_info(self):
        response = self._send_command(code=1)
        if len(response) < 8:
            raise CrowAdminError("The get_device_info response has less than eight bytes.")
        info = {}
        info['crow_version'] = response[3]
        info['max_command_payload_size'] = int.from_bytes(response[4:6], 'big')
        info['max_response_payload_size'] = int.from_bytes(response[6:8], 'big')
        if len(response) == 8:
            return info
        details = response[8]
        params = {'ind': 9, 'rem': len(response) - 9}
        if details & 1:
            self._extract_ascii(info, response, params, 'impl_identifier', 'get_device_info')
        if details & 2:
            self._extract_ascii(info, response, params, 'impl_description', 'get_device_info')
        if details & 4:
            self._extract_ascii(info, response, params, 'device_identifier', 'get_device_info')
        if details & 8:
            self._extract_ascii(info, response, params, 'device_description', 'get_device_info')
        return info

    def get_open_ports(self):
        response = self._send_command(code=2)
        if len(response) < 4:
            raise CrowAdminError("The get_open_ports response has less than four bytes.")
        if response[3] == 0x01:
            raise RuntimeError("The bitfield option for get_open_ports is not implemented.") # todo: fix
        if response[3] != 0:
            raise CrowAdminError("Invalid format for get_open_ports response.")
        ports = []
        for p in response[4:]:
            ports.append(p)
        return ports


    def get_port_info(self, port):
        if port < 0 or port > 0xff:
            raise ValueError("port must be in the range [0, 255].")
        response = self._send_command(code=3, parameters=port.to_bytes(1, 'big'))
        if len(response) < 4:
            raise CrowAdminError("The get_port_info response has less than four bytes.")
        details = response[3]
        info = {}
        info['is_open'] = bool(details & 1)
        params = {'ind': 4, 'rem': len(response) - 4}
        if details & 2:
            self._extract_ascii(info, response, params, 'service_identifier', 'get_port_info')
        if details & 4:
            self._extract_ascii(info, response, params, 'service_description', 'get_port_info')
        return info


    def _send_command(self, code=0, is_ping=False, response_expected=True, parameters=None):

        if self.host is None:
            raise RuntimeError("The host must be defined in order to send admin commands.")

        if is_ping:
            payload = b''
        else:
            payload = bytearray(b'\x43\x41') + code.to_bytes(1, 'big')
            if parameters is not None:
                payload += parameters

        response = self.host.send_command(address=self.address, port=self.port, payload=payload, response_expected=response_expected, propcr_order=self.propcr_order)

        if not response_expected:
            return None

        if is_ping:
            if len(response):
                raise CrowAdminError("Received a non-empty response to ping command.")
            else:
                return None

        # Any non-ping response must have an initial three byte header identical to the commands: 0x43, 0x41, and command code

        if len(response) < 3:
            raise CrowAdminError("The response was too short -- less than three bytes.")

        if response[0] != 0x43 or response[1] != 0x41:
            raise CrowAdminError("The response did not have the correct initial identifying bytes.")

        if response[2] != code:
            raise CrowAdminError("The response does not include the correct command code.")

        # initial header OK, so return to caller for final processing
        return response
        

