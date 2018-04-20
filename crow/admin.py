# CrowAdmin Client
# Version 0.2.0 (alpha/experimental)
# 19 April 2018
# Chris Siedell
# https://github.com/chris-siedell/PyCrow


import time
from crow.utils import extract_ascii
from crow.errors import ClientError


class CrowAdmin():

    def __init__(self):
        self.host = None
        self.address = 1
        self.port = 0
        self.propcr_order = False

    def ping(self):
        """Returns the time, in seconds, taken to perform a successful ping."""
        start = time.perf_counter()
        params = self._send_command(None)
        ca_parse_ping(params)
        return time.perf_counter() - start

    def echo(self, data=None):
        """Sends an echo command. Returns nothing. Raises an error if the echo fails."""
        params = self._send_command(0, data)
        ca_parse_echo(params)

    def host_presence(self, data):
        """Sends a host presence packet. Returns nothing since there is no response."""
        self._send_command(0, data, response_expected=False)

    def get_device_info(self):
        """Returns a dictionary with information about the device."""
        params = self._send_command(1)
        return ca_parse_get_device_info(params)

    def get_open_ports(self):
        """Returns a list of open ports on the device."""
        params = self._send_command(2)
        return ca_parse_get_open_ports(params)

    def get_port_info(self, port):
        """Returns a dictionary with information about the given port."""
        if port < 0 or port > 255:
            raise ValueError("port must be in the range [0, 255].")
        params = self._send_command(3, port.to_bytes(1, 'big'))
        return ca_parse_get_port_info(params)

    def _send_command(self, command_code, data=None, response_expected=True):
        # A helper method for sending CrowAdmin commands.
        # Returns a params dictionary suitable for the ca_parse_* methods.
        # data, if not None, is appended to the command payload after the third byte.
        params = {}
        params['address'] = self.address
        params['port'] = self.port
        params['command_code'] = command_code
        if command_code is not None:
            # not ping
            params['command'] = bytearray(b'\x43\x41') + command_code.to_bytes(1, 'big')
            if data is not None:
                params['command'] += data
        else:
            # ping
            params['command'] = None
        params['response'] = self.host.send_command(address=self.address, port=self.port, payload=params['command'], response_expected=response_expected, propcr_order=self.propcr_order)
        return params


class CrowAdminError(ClientError):
    def __init__(self, address, port, message, command_code):
        super().__init__(address, port, message)
        self.command_code = command_code
    def __str__(self):
        return super().extra_str() + " Command code: " + str(self.command_code) + "."


# These ca_parse_* functions are helper functions for CrowAdmin. They are separated out
#  to simplify testing. These functions take a params dictionary that always has the
#  following properties:
#       address, port - the address and port used to send the command
#       command_code - the command's code (will be None for ping)
#       command - the command payload (will be None for ping)
#       response - the response payload (will be None if no response expected)
# Some of these functions will add arg_index, which is an index into response used for
#  extracting details.
# On failure, these functions will raise CrowAdminError.

def ca_parse_raise_error(params, message):
    raise CrowAdminError(params['address'], params['port'], message, params['command_code'])

def ca_parse_ping(params):
    # Returns nothing. The ping response should be empty.
    if len(params['response']) > 0:
        ca_parse_raise_error(params, "The ping response was not empty.")

def ca_parse_header(params):
    # Returns nothing -- it simply validates the initial header (the first three bytes). Not applicable to ping.
    # The first two bytes are the protocol identifying bytes 0x43 and 0x41 (ascii "CA" for "CrowAdmin").
    # The third byte is a repeat of the command code.
    rsp = params['response']
    if len(rsp) == 0:
        ca_parse_raise_error(params, "The response is empty. At least three bytes are required.")
    if len(rsp) < 3:
        ca_parse_raise_error(params, "The response has less than three bytes.")
    if rsp[0] != 0x43 or rsp[1] != 0x41:
        ca_parse_raise_error(params, "The response does not have the correct identifying bytes.")
    if rsp[2] != params['command_code']:
        ca_parse_raise_error(params, "The response does not include the correct command code.")

def ca_parse_echo(params):
    # Returns nothing. It raises an error if the echo failed.
    # There is actually no need to check the response header separately since it
    #  should be identical to the command header, but doing so provides more a
    #  more granular error message.
    ca_parse_header(params)
    cmd = params['command']
    rsp = params['response']
    if len(rsp) < len(cmd):
        ca_parse_raise_error(params, "The echo response has too few bytes.")
    elif len(rsp) > len(cmd):
        ca_parse_raise_error(params, "The echo response has too many bytes.")
    if rsp != cmd:
        ca_parse_raise_error(params, "The echo response has incorrect bytes.")


def ca_parse_get_device_info(params):
    # Returns a dictionary with device information.
    ca_parse_header(params)
    rsp = params['response']
    if len(rsp) < 9:
        ca_parse_raise_error(params, "The get_device_info response has less than nine bytes.")
    info = {}
    info['crow_version'] = rsp[3]
    info['crow_admin_version'] = rsp[4]
    info['max_command_size'] = int.from_bytes(rsp[5:7], 'big')
    info['max_response_size'] = int.from_bytes(rsp[7:9], 'big')
    if len(rsp) == 9:
        return info
    details = rsp[9]
    params['arg_index'] = 10
    try:
        # extract_ascii will raise RuntimeError on failure
        rsp_name = 'get_device_info'
        if details & 1:
            extract_ascii(info, params, 3, 'impl_identifier', rsp_name)
        if details & 2:
            extract_ascii(info, params, 3, 'impl_description', rsp_name)
        if details & 4:
            extract_ascii(info, params, 3, 'device_identifier', rsp_name)
        if details & 8:
            extract_ascii(info, params, 3, 'device_description', rsp_name)
    except RuntimeError as e:
        ca_parse_raise_error(params, str(e))
    return info


def ca_parse_get_open_ports(params):
    # Returns a list of open port numbers.
    ca_parse_header(params)
    rsp = params['response']
    if len(rsp) < 4:
        ca_parse_raise_error(params, "The get_open_ports response has less than four bytes.")
    ports = []
    if rsp[3] == 0:
        # todo: check for redundancies
        for p in rsp[4:]:
            ports.append(p)
    elif rsp[3] == 1:
        # todo: implement
        raise RuntimeError("The bitfield option for get_open_ports is not implemented.")
    else:
        ca_parse_raise_error(params, "Invalid format for the get_open_ports response.")
    return ports


def ca_parse_get_port_info(params):
    ca_parse_header(params)
    rsp = params['response']
    if len(rsp) < 4:
        ca_parse_raise_error(params, "The get_port_info response has less than four bytes.")
    details = rsp[3]
    params['arg_index'] = 4
    info = {}
    info['is_open'] = bool(details & 1)
    try:
        # extract_ascii will raise RuntimeError on failure
        rsp_name = 'get_port_info'
        if details & 2:
            extract_ascii(info, params, 3, 'service_identifier', rsp_name)
        if details & 4:
            extract_ascii(info, params, 3, 'service_description', rsp_name)
    except RuntimeError as e:
        ca_parse_raise_error(params, str(e))
    return info



