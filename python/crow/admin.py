# CrowAdmin Client
# 24 April 2018
# Chris Siedell
# project: https://pypi.org/project/crow-serial/
# source: https://github.com/chris-siedell/PyCrow


import time
import crow.utils
import crow.errors
import crow.host


class CrowAdmin():


    # CrowAdmin is used to send admin commands defined by the Crow standard, such
    #  as ping and getDeviceInfo.
    # A CrowAdmin instance can be used to communicate with a single address on a
    #  serial port by using the default address, or with any address
    #  by using the address argument to the command methods.


    def __init__(self, serial_port_name, default_address=1, default_port=0):
        self.host = crow.host.Host(serial_port_name)
        self.default_address = default_address
        self.default_port = default_port


    def ping(self, address=None, port=None):
        """Returns the time, in seconds, taken to perform a successful ping."""
        start = time.perf_counter()
        transaction = self._send_command(address, port, None)
        CrowAdmin.validate_ping(transaction)
        return time.perf_counter() - start


    def echo(self, data=None, address=None, port=None):
        """Sends an echo command. Returns nothing. Raises an error if the echo fails."""
        transaction = self._send_command(address, port, 0, data)
        CrowAdmin.validate_echo(transaction)


    def host_presence(self, data=None, address=None, port=None):
        """Sends a host presence packet. Returns nothing since there is no response."""
        self._send_command(address, port, 0, data, response_expected=False)


    def get_device_info(self, address=None, port=None):
        """Returns a dictionary with information about the device."""
        transaction = self._send_command(address, port, 1)
        return CrowAdmin.parse_get_device_info(transaction)


    def get_open_ports(self, address=None, port=None):
        """Returns a list of open ports on the device."""
        transaction = self._send_command(address, port, 2)
        return CrowAdmin.parse_get_open_ports(transaction)


    def get_port_info(self, query_port, address=None, admin_port=None):
        """Returns a dictionary with information about the given port."""
        if query_port < 0 or query_port > 255:
            raise ValueError("query_port must be 0 to 255.")
        transaction = self._send_command(address, admin_port, 3, query_port.to_bytes(1, 'big'))
        return CrowAdmin.parse_get_port_info(transaction)


    def _send_command(self, address, port, command_code, data=None, response_expected=True):
        # A helper method for sending CrowAdmin commands.
        # data, if not None, is appended to the command payload after the third byte.
        
        if address is None:
            address = self.default_address
        if port is None:
            port = self.default_port

        if response_expected:
            if address < 0 or address > 31:
                raise ValueError("The address for this command must be 1 to 31.")
            elif address == 0:
                raise ValueError("This command is not a broadcast command (address 0).")
        else:
            if address < 0 or address > 31:
                raise ValueError("The address for this command must be 0 to 31.")

        if port < 0 or port > 255:
            raise ValueError("The port must be 0 to 255.")

        if command_code is not None:
            # not ping
            command = bytearray(b'\x43\x41') + command_code.to_bytes(1, 'big')
            if data is not None:
                command += data
        else:
            # ping
            command = None

        transaction = self.host.send_command(address=address, port=port, payload=command, response_expected=response_expected)
        transaction.command_code = command_code
        return transaction


    # The following validate_* and parse_* methods raise CrowAdminError on failure.


    @staticmethod
    def validate_ping(transaction):
        # The ping response should be empty.
        if len(transaction.response) > 0:
            raise CrowAdminError(transaction, "The ping response was not empty.")


    @staticmethod
    def validate_header(transaction):
        # Returns nothing -- it simply validates the initial header (the first three bytes). Not applicable to ping.
        # The first two bytes are the protocol identifying bytes 0x43 and 0x41 (ascii "CA" for "CrowAdmin").
        # The third byte is a repeat of the command code.
        rsp = transaction.response
        if len(rsp) == 0:
            raise CrowAdminError(transaction, "The response is empty. At least three bytes are required.")
        if len(rsp) < 3:
            raise CrowAdminError(transaction, "The response has less than three bytes.")
        if rsp[0] != 0x43 or rsp[1] != 0x41:
            raise CrowAdminError(transaction, "The response does not have the correct identifying bytes.")
        if rsp[2] != transaction.command_code:
            raise CrowAdminError(transaction, "The response does not include the correct command code.")


    @staticmethod
    def validate_echo(transaction):
        # Returns nothing. It raises an error if the echo failed.
        # There is actually no need to check the response header separately since it
        #  should be identical to the command header, but doing so provides more a
        #  more granular error message.
        CrowAdmin.validate_header(transaction)
        cmd = transaction.command
        rsp = transaction.response
        if len(rsp) < len(cmd):
            raise CrowAdminError(transaction, "The echo response has too few bytes.")
        elif len(rsp) > len(cmd):
            raise CrowAdminError(transaction, "The echo response has too many bytes.")
        if rsp != cmd:
            raise CrowAdminError(transaction, "The echo response has incorrect bytes.")


    @staticmethod
    def parse_get_device_info(transaction):
        # Returns a dictionary with device information.
        CrowAdmin.validate_header(transaction)
        rsp = transaction.response
        if len(rsp) < 9:
            raise CrowAdminError(transaction, "The get_device_info response has less than nine bytes.")
        info = {}
        info['crow_version'] = rsp[3]
        info['crow_admin_version'] = rsp[4]
        info['max_command_size'] = int.from_bytes(rsp[5:7], 'big')
        info['max_response_size'] = int.from_bytes(rsp[7:9], 'big')
        if len(rsp) == 9:
            return info
        details = rsp[9]
        transaction.arg_index = 10
        try:
            # unpack_ascii will raise RuntimeError on failure
            rsp_name = 'get_device_info'
            if details & 1:
                crow.utils.unpack_ascii(info, transaction, 3, 'impl_identifier', rsp_name)
            if details & 2:
                crow.utils.unpack_ascii(info, transaction, 3, 'impl_description', rsp_name)
            if details & 4:
                crow.utils.unpack_ascii(info, transaction, 3, 'device_identifier', rsp_name)
            if details & 8:
                crow.utils.unpack_ascii(info, transaction, 3, 'device_description', rsp_name)
        except RuntimeError as e:
            raise CrowAdminError(transaction, str(e))
        return info


    @staticmethod
    def parse_get_open_ports(transaction):
        # Returns a list of open port numbers.
        CrowAdmin.validate_header(transaction)
        rsp = transaction.response
        if len(rsp) < 4:
            raise CrowAdminError(transaction, "The get_open_ports response has less than four bytes.")
        ports = []
        if rsp[3] == 0:
            # todo: check for redundancies / oversized response
            for p in rsp[4:]:
                ports.append(p)
        elif rsp[3] == 1:
            # todo: implement
            raise RuntimeError("The bitfield option for get_open_ports is not implemented.")
        else:
            raise CrowAdminError(transaction, "Invalid format for the get_open_ports response.")
        return ports


    @staticmethod
    def parse_get_port_info(transaction):
        # Returns a dictionary with information about the port.
        # The only key guaranteed to be in the dictionary is 'is_open'.
        CrowAdmin.validate_header(transaction)
        rsp = transaction.response
        if len(rsp) < 4:
            raise CrowAdminError(transaction, "The get_port_info response has less than four bytes.")
        details = rsp[3]
        transaction.arg_index = 4
        info = {}
        info['is_open'] = bool(details & 1)
        try:
            # unpack_ascii will raise RuntimeError on failure
            rsp_name = 'get_port_info'
            if details & 2:
                crow.utils.unpack_ascii(info, transaction, 3, 'service_identifier', rsp_name)
            if details & 4:
                crow.utils.unpack_ascii(info, transaction, 3, 'service_description', rsp_name)
        except RuntimeError as e:
            raise CrowAdminError(transaction, str(e))
        return info


class CrowAdminError(crow.errors.ClientError):
    def __init__(self, transaction, message):
        super().__init__(transaction.address, transaction.port, message)
        self.command_code = transaction.command_code
    def __str__(self):
        return super().extra_str() + " Command code: " + str(self.command_code) + "."


