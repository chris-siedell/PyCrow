# Crow v2 Errors
# April 2018 - in active development
# Chris Siedell
# https://github.com/chris-siedell/PyCrow


class CrowError(Exception):
    pass

# Remote Errors

class RemoteError(CrowError):
    def __init__(self, number, address, port, details):
        self.number = number
        self.address = address
        self.port = port
        self.details = details
    def extra_str(self):
        return "Address: " + str(self.address) + ", port: " + str(self.port) + ", number: " + str(self.number) + ", details: " + str(self.details) + "."

class DeviceError(RemoteError):
    def __init__(self, number, address, port, details):
        super().__init__(number, address, port, details)
    def __str__(self):
        return "Device error number " + str(self.number) + ". " + super().extra_str()

class ServiceError(RemoteError):
    def __init__(self, number, address, port, details):
        super().__init__(number, address, port, details)
    def __str__(self):
        return "Service error number " + str(self.number) + ". " + super().extra_str()


# Standard Assigned Device Errors

class UnspecifiedDeviceError(DeviceError):
    def __init__(self, address, port, details):
        super().__init__(0, address, port, details)
    def __str__(self):
        return "The device experienced an unspecified error. " + super().extra_str()

class DeviceFaultError(DeviceError):
    def __init__(self, address, port, details):
        super().__init__(1, address, port, details)
    def __str__(self):
        return "An unexpected error occurred in the device's Crow implementation. " + super().extra_str()

class ServiceFaultError(DeviceError):
    def __init__(self, address, port, details):
        super().__init__(2, address, port, details)
    def __str__(self):
        return "An unexpected error occurred in the device's service implementation. " + super().extra_str()

class DeviceUnavailableError(DeviceError):
    def __init__(self, address, port, details):
        super().__init__(3, address, port, details)
    def __str__(self):
        return "The device is unavailable. " + super().extra_str()

class DeviceIsBusyError(DeviceUnavailableError):
    def __init__(self, address, port, details):
        super().__init__(4, address, port, details)
    def __str__(self):
        return "The device is busy. " + super().extra_str()

class OversizedCommandError(DeviceError):
    def __init__(self, address, port, details):
        super().__init__(5, address, port, details)
    def __str__(self):
        return "The command payload exceeded the device's capacity. " + super().extra_str()

class CorruptCommandPayloadError(DeviceError):
    def __init__(self, address, port, details):
        super().__init__(6, address, port, details)
    def __str__(self):
        return "The command payload checksum test failed. " + super().extra_str()

class PortNotOpenError(DeviceError):
    def __init__(self, address, port, details):
        super().__init__(7, address, port, details)
    def __str__(self):
        return "The port was not open. " + super().extra_str()

class DeviceLowResourcesError(DeviceError):
    def __init__(self, address, port, details):
        super().__init__(8, address, port, details)
    def __str__(self):
        return "The device reports low resources. " + super().extra_str()

class UnknownDeviceError(DeviceError):
    def __init__(self, number, address, port, details):
        super().__init__(number, address, port, details)
    def __str__(self):
        return "Unknown device error number " + str(self.number) + ". " + super().extra_str()


# Standard Assigned Service Errors

class UnspecifiedServiceError(ServiceError):
    def __init__(self, address, port, details):
        super().__init__(64, address, port, details)
    def __str__(self):
        return "The service experienced an unspecified error. " + super().extra_str()

class UnknownCommandFormatError(ServiceError):
    def __init__(self, address, port, details):
        super().__init__(65, address, port, details)
    def __str__(self):
        return "The service does not recognize the command format. " + super().extra_str()

class RequestTooLargeError(ServiceError):
    def __init__(self, address, port, details):
        super().__init__(66, address, port, details)
    def __str__(self):
        return "The required response would exceed the device's capacity. " + super().extra_str() 

class ServiceLowResourcesError(ServiceError):
    def __init__(self, address, port, details):
        super().__init__(67, address, port, details)
    def __str__(self):
        return "The service reports low resources. " + super().extra_str()

class CommandNotAvailableError(ServiceError):
    def __init__(self, address, port, details):
        super().__init__(68, address, port, details)
    def __str__(self):
        return "The command is not available. " + super().extra_str()

class CommandNotImplementedError(CommandNotAvailableError):
    def __init__(self, address, port, details):
        super().__init__(69, address, port, details)
    def __str__(self):
        return "The command is not implemented. " + super().extra_str()

class CommandNotAllowedError(CommandNotAvailableError):
    def __init__(self, address, port, details):
        super().__init__(70, address, port, details)
    def __str__(self):
        return "The command is not allowed. " + super().extra_str()

class InvalidCommandError(ServiceError):
    def __init__(self, address, port, details):
        super().__init__(71, address, port, details)
    def __str__(self):
        return "The command format was recognized, but it is invalid. " + super().extra_str()

class IncorrectCommandSizeError(InvalidCommandError):
    def __init__(self, address, port, details):
        super().__init__(72, address, port, details)
    def __str__(self):
        return "The command payload had a different size than expected. " + super().extra_str()

class MissingCommandDataError(IncorrectCommandSizeError):
    def __init__(self, address, port, details):
        super().__init__(73, address, port, details)
    def __str__(self):
        return "The command payload was smaller than expected. " + super().extra_str()

class TooMuchCommandDataError(IncorrectCommandSizeError):
    def __init__(self, address, port, details):
        super().__init__(74, address, port, details)
    def __str__(self):
        return "The command payload was larger than expected. " + super().extra_str()

class UnknownServiceError(ServiceError):
    def __init__(self, number, address, port, details):
        super().__init__(number, address, port, details)
    def __str__(self):
        return "Unknown service error number " + str(self.number) + ". " + super().extra_str()


# Host Errors

#class CrowHostError(CrowError):
#    """Base class for exceptions raised for errors detected by the host."""
#    
#    def __init__(self, address, port, message):
#        self.address = address
#        self.port = port
#        self.message = message
#
#    def __str__(self):
#        return self.message + " Address: " + str(self.address) + ", port: " + str(self.port) + "."
#

# Local Errors

class LocalError(CrowError):
    pass

class ClientError(LocalError):
    pass

class HostError(LocalError):
    def __init__(self, address, port, message=None):
        self.address = address
        self.port = port
        self.message = message
    def __str__(self):
        return "Host error (abstract)."
    def extra_str(self):
        extra = "Address: " + str(self.address) + ", port: " + str(self.port) + "."
        if self.message is not None:
            extra += " " + self.message
        return extra

class NoResponseError(HostError):
    def __init__(self, address, port, num_bytes, message=None):
        self.num_bytes = num_bytes
        super().__init__(address, port, message)
    def __str__(self):
        return "No response received before the transaction timed out. Received " + str(self.num_bytes) + " bytes. " + super().extra_str()


class InvalidResponseError(ClientError):
    pass


#
#class CrowDeviceError(CrowError):
#    """Base class for exceptions raised for errors detected by the device."""
#
#    def __init__(self, address, port, details, too_short):
#        self.address = address
#        self.port = port
#        self.details = details
#        self.too_short = too_short
#
#    def __str__(self):
#        result = "Address: " + str(self.address) + ", port: " + str(self.port) + "."
#        if self.too_short:
#            result += " Warning: the response payload was too short for the details it claimed to include."
#        if 'crow_version' in self.details:
#            result += " Implementation's Crow version: " + str(self.details['crow_version']) + "."
#        if 'address' in self.details:
#            if self.details['address'] != self.address:
#                result += " Warning: there is a discrepancy in the address (local: " + str(self.address) + ", remote: " + str(self.details['address']) + "."
#        if 'port' in self.details:
#            if self.details['port'] != self.port:
#                result += " Warning: there is a discrepancy in the port (local: " + str(self.port) + ", remote: " + str(self.details['port']) + "."
#        if 'max_command_size' in self.details:
#            result += " Max supported command size: " + str(self.details['max_command_size']) + "."
#        if 'max_response_size' in self.details:
#            result += " Max supported response size: " + str(self.details['max_response_size']) + "."
#        if 'ascii_message' in self.details:
#            result += " Device message: " + self.details['ascii_message']
#        return result
#
#
#class UnspecifiedError(CrowDeviceError):
#    def __init__(self, address, port, details, too_short):
#        super().__init__(address, port, details, too_short)
#    def __str__(self):
#        return "The device reports an unspecified error. " + super().__str__()
#
#class DeviceUnavailableError(CrowDeviceError):
#    def __init__(self, address, port, details, too_short):
#        super().__init__(address, port, details, too_short)
#    def __str__(self):
#        return "The device is unavailable. " + super().__str__()
#
#class DeviceIsBusyError(CrowDeviceError):
#    def __init__(self, address, port, details, too_short):
#        super().__init__(address, port, details, too_short)
#    def __str__(self):
#        return "The device is busy. " + super().__str__()
#
#class CommandTooLargeError(CrowDeviceError):
#    def __init__(self, address, port, details, too_short):
#        super().__init__(address, port, details, too_short)
#    def __str__(self):
#        return "The command payload size exceeds the device's capacity. " + super().__str__()
#
#class CorruptPayloadError(CrowDeviceError):
#    def __init__(self, address, port, details, too_short):
#        super().__init__(address, port, details, too_short)
#    def __str__(self):
#        return "The device reports that the command payload had a bad checksum. " + super().__str__()
#
#class PortNotOpenError(CrowDeviceError):
#    def __init__(self, address, port, details, too_short):
#        super().__init__(address, port, details, too_short)
#    def __str__(self):
#        return "The port is not open. " + super().__str__()
#
#class LowResourcesError(CrowDeviceError):
#    def __init__(self, address, port, details, too_short):
#        super().__init__(address, port, details, too_short)
#    def __str__(self):
#        return "The device can not process the command due to low resources. " + super().__str__()
#
#class UnknownProtocolError(CrowDeviceError):
#    def __init__(self, address, port, details, too_short):
#        super().__init__(address, port, details, too_short)
#    def __str__(self):
#        return "The service did not understand the command. " + super().__str__()
#
#class RequestTooLargeError(CrowDeviceError):
#    def __init__(self, address, port, details, too_short):
#        super().__init__(address, port, details, too_short)
#    def __str__(self):
#        return "The required response payload size exceeds the device's capacity. " + super().__str__()
#
#class ImplementationFaultError(CrowDeviceError):
#    def __init__(self, address, port, details, too_short):
#        super().__init__(address, port, details, too_short)
#    def __str__(self):
#        return "An unexpected error occurred in the device's Crow implementation. " + super().__str__()
#
#class ServiceFaultError(CrowDeviceError):
#    def __init__(self, address, port, details, too_short):
#        super().__init__(address, port, details, too_short)
#    def __str__(self):
#        return "An unexpected error occurred in the device's service code. " + super().__str__()
#
#class UnknownError(CrowDeviceError):
#    def __init__(self, address, port, details, too_short, number):
#        super().__init__(address, port, details, too_short)
#    def __str__(self):
#        return "An unknown error occurred (type " + str(self.number) + "). " + super().__str__()
#

