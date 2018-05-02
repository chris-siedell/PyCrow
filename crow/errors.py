# errors.py
# Crow Errors
# 2 May 2018
# Chris Siedell
# project: https://pypi.org/project/crow-serial/
# source: https://github.com/chris-siedell/PyCrow
# homepage: http://siedell.com/projects/Crow/


# CrowError, base class for all Crow errors.
class CrowError(Exception):
    def __init__(self, address, port):
        self.address = address
        self.port = port
    def __str__(self):
        return "Generic Crow protocol error. " + self.extra_str()
    def extra_str(self):
        return "Address: " + str(self.address) + ", port: " + str(self.port) + "."


# Remote Errors

# Remote errors originate at the device, either in the device implementation (DeviceError)
#  or in the service (ServiceError). They are raised by the host when it receives an error
#  response. Error responses begin with a one-byte number indicating the error -- zero
#  is assigned if the error response is empty. The error response may contain additional
#  details, which will be provided in the details dictionary.

# RemoteError, base class for all Crow errors originating at the device.
class RemoteError(CrowError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port)
        self.number = number
        self.details = details
    def __str__(self):
        return "An error was detected remotely, either in the device implementation or the service code. " + self.extra_str()
    def extra_str(self):
        return "Number: " + str(self.number) + ", details: " + str(self.details) + ". " + super().extra_str()

# DeviceError, for errors originating in the device implementation.
class DeviceError(RemoteError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The device implementation has detected an error. " + super().extra_str()

# ServiceError, for errors originating in the service.
class ServiceError(RemoteError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The service has detected an error. " + super().extra_str()


# Standard Assigned Device Errors

# Device errors numbered 2 to 31 have special meanings assigned by the Crow standard.

class DeviceFaultError(DeviceError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "An unexpected error occurred in the device's Crow implementation. " + super().extra_str()

class ServiceFaultError(DeviceError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "An unexpected error occurred in the service implementation. " + super().extra_str()

class DeviceUnavailableError(DeviceError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The device is unavailable. " + super().extra_str()

class DeviceIsBusyError(DeviceUnavailableError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The device is busy. " + super().extra_str()

class OversizedCommandError(DeviceError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The command payload exceeded the device's capacity. " + super().extra_str()

class CorruptCommandPayloadError(DeviceError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The command payload checksum test failed. " + super().extra_str()

class PortNotOpenError(DeviceError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The port was not open. " + super().extra_str()

class DeviceLowResourcesError(DeviceError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The device reports low resources. " + super().extra_str()

class UnknownDeviceError(DeviceError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "Unknown device error. " + super().extra_str()


# Standard Assigned Service Errors

# Service errors numbered 65 to 127 have meanings assigned by the Crow standard.

class UnknownCommandFormatError(ServiceError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The service does not recognize the command format. " + super().extra_str()

class ServiceLowResourcesError(ServiceError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The service reports low resources. " + super().extra_str()

class InvalidCommandError(ServiceError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The command can not be performed. " + super().extra_str()

class RequestTooLargeError(ServiceError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The required response would exceed the device's capacity. " + super().extra_str() 

class CommandNotAvailableError(ServiceError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The command is not available. " + super().extra_str()

class CommandNotImplementedError(CommandNotAvailableError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The command is not implemented. " + super().extra_str()

class CommandNotAllowedError(CommandNotAvailableError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The command is not allowed. " + super().extra_str()

class IncorrectCommandSizeError(InvalidCommandError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The command payload had a different size than expected. " + super().extra_str()

class MissingCommandDataError(IncorrectCommandSizeError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The command payload was smaller than expected. " + super().extra_str()

class TooMuchCommandDataError(IncorrectCommandSizeError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "The command payload was larger than expected. " + super().extra_str()

class UnknownServiceError(ServiceError):
    def __init__(self, address, port, number, details):
        super().__init__(address, port, number, details)
    def __str__(self):
        return "Unknown service error. " + super().extra_str()


# Local Errors

# Local errors originate at the host, either in the host implementation (HostError) or
#  in the client (ClientError).

# LocalError, base class for errors originating at the host.
class LocalError(CrowError):
    def __init__(self, address, port, message=None):
        super().__init__(address, port)
        self.message = message;
    def extra_str(self):
        if self.message is not None:
            return self.message + " " + super().extra_str()
        else:
            return super().extra_str()

# HostError, for errors originating in the host implementation.
class HostError(LocalError):
    def __init__(self, address, port, message=None):
        super().__init__(address, port, message)
    def __str__(self):
        return "Host error. " + super().extra_str()

# ClientError, for errors originating in the client.
class ClientError(LocalError):
    def __init__(self, address, port, message=None):
        super().__init__(address, port, message)
    def __str__(self):
        return "Client error. " + super().extra_str()

# NoResponseError is raised by the host from send_command when it fails to
# receive a parseable, expected response.
class NoResponseError(HostError):
    def __init__(self, address, port, num_bytes, message=None):
        self.num_bytes = num_bytes
        super().__init__(address, port, message)
    def __str__(self):
        return "No response received before the transaction timed out. Received " + str(self.num_bytes) + " bytes. " + super().extra_str()


