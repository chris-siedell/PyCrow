# Crow v2 Errors
# April 2018 - in active development
# Chris Siedell
# http://siedell.com/projects/Crow

class CrowError(Exception):
    """Base class for Crow exceptions."""
    pass


class CrowHostError(CrowError):
    """Base class for exceptions raised for errors detected by the host."""
    
    def __init__(self, address, port, message):
        self.address = address
        self.port = port
        self.message = message

    def __str__(self):
        return self.message + " Address: " + str(self.address) + ", port: " + str(self.port) + "."


class NoResponseError(CrowHostError):
    pass


class CrowDeviceError(CrowError):
    """Base class for exceptions raised for errors detected by the device."""

    def __init__(self, address, port, details, too_short):
        self.address = address
        self.port = port
        self.details = details
        self.too_short = too_short

    def __str__(self):
        result = "Address: " + str(self.address) + ", port: " + str(self.port) + "."
        if self.too_short:
            result += " Warning: the response payload was too short for the details it claimed to include."
        if 'crow_version' in self.details:
            result += " Implementation's Crow version: " + str(self.details['crow_version']) + "."
        if 'address' in self.details:
            if self.details['address'] != self.address:
                result += " Warning: there is a discrepancy in the address (local: " + str(self.address) + ", remote: " + str(self.details['address']) + "."
        if 'port' in self.details:
            if self.details['port'] != self.port:
                result += " Warning: there is a discrepancy in the port (local: " + str(self.port) + ", remote: " + str(self.details['port']) + "."
        if 'max_command_size' in self.details:
            result += " Max supported command size: " + str(self.details['max_command_size']) + "."
        if 'max_response_size' in self.details:
            result += " Max supported response size: " + str(self.details['max_response_size']) + "."
        if 'ascii_message' in self.details:
            result += " Device message: " + self.details['ascii_message']
        return result


class UnspecifiedError(CrowDeviceError):
    def __init__(self, address, port, details, too_short):
        super().__init__(address, port, details, too_short)
    def __str__(self):
        return "The device reports an unspecified error. " + super().__str__()

class DeviceUnavailableError(CrowDeviceError):
    def __init__(self, address, port, details, too_short):
        super().__init__(address, port, details, too_short)
    def __str__(self):
        return "The device is unavailable. " + super().__str__()

class DeviceIsBusyError(CrowDeviceError):
    def __init__(self, address, port, details, too_short):
        super().__init__(address, port, details, too_short)
    def __str__(self):
        return "The device is busy. " + super().__str__()

class CommandTooLargeError(CrowDeviceError):
    def __init__(self, address, port, details, too_short):
        super().__init__(address, port, details, too_short)
    def __str__(self):
        return "The command payload size exceeds the device's capacity. " + super().__str__()

class CorruptPayloadError(CrowDeviceError):
    def __init__(self, address, port, details, too_short):
        super().__init__(address, port, details, too_short)
    def __str__(self):
        return "The device reports that the command payload had a bad checksum. " + super().__str__()

class PortNotOpenError(CrowDeviceError):
    def __init__(self, address, port, details, too_short):
        super().__init__(address, port, details, too_short)
    def __str__(self):
        return "The port is not open. " + super().__str__()

class LowResourcesError(CrowDeviceError):
    def __init__(self, address, port, details, too_short):
        super().__init__(address, port, details, too_short)
    def __str__(self):
        return "The device can not process the command due to low resources. " + super().__str__()

class UnknownProtocolError(CrowDeviceError):
    def __init__(self, address, port, details, too_short):
        super().__init__(address, port, details, too_short)
    def __str__(self):
        return "The service did not understand the command. " + super().__str__()

class RequestTooLargeError(CrowDeviceError):
    def __init__(self, address, port, details, too_short):
        super().__init__(address, port, details, too_short)
    def __str__(self):
        return "The required response payload size exceeds the device's capacity. " + super().__str__()

class ImplementationFaultError(CrowDeviceError):
    def __init__(self, address, port, details, too_short):
        super().__init__(address, port, details, too_short)
    def __str__(self):
        return "An unexpected error occurred in the device's Crow implementation. " + super().__str__()

class ServiceFaultError(CrowDeviceError):
    def __init__(self, address, port, details, too_short):
        super().__init__(address, port, details, too_short)
    def __str__(self):
        return "An unexpected error occurred in the device's service code. " + super().__str__()

class UnknownError(CrowDeviceError):
    def __init__(self, address, port, details, too_short, number):
        super().__init__(address, port, details, too_short)
    def __str__(self):
        return "An unknown error occurred (type " + str(self.number) + "). " + super().__str__()


