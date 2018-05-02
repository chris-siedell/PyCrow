# errorTests001.py
# 2 May 2018
# Chris Siedell
# project: https://pypi.org/project/crow-serial/
# source: https://github.com/chris-siedell/PyCrow
# homepage: http://siedell.com/projects/Crow/


from crow.host import Host
from crow.transaction import Transaction
import crow.errors


host = Host(None)

t = Transaction()
t.response = b''


print("PyCrow Error Tests 001, 2 May 2018")
print(" The following tests verify the host's error throwing method for remote errors. They also verify that error numbers have been correctly assigned to specific error types.")
print(" Visual inspection required.\n")


def raise_error():
    try:
        host._raise_error(t)
        raise RuntimeError("No error thrown.")
    except crow.errors.DeviceFaultError as e:
        print(" caught DeviceFaultError")
        print(" " + str(e) + "\n")
    except crow.errors.ServiceFaultError as e:
        print(" caught ServiceFaultError")
        print(" " + str(e) + "\n")
    except crow.errors.DeviceIsBusyError as e:
        # DeviceIsBusyError inherits from DeviceUnavailableError
        print(" caught DeviceIsBusyError")
        print(" " + str(e) + "\n")
    except crow.errors.DeviceUnavailableError as e:
        print(" caught DeviceUnavailableError")
        print(" " + str(e) + "\n")
    except crow.errors.OversizedCommandError as e:
        print(" caught OversizedCommandError")
        print(" " + str(e) + "\n")
    except crow.errors.CorruptCommandPayloadError as e:
        print(" caught CorruptCommandPayloadError")
        print(" " + str(e) + "\n")
    except crow.errors.PortNotOpenError as e:
        print(" caught PortNotOpenError")
        print(" " + str(e) + "\n")
    except crow.errors.DeviceLowResourcesError as e:
        print(" caught DeviceLowResourcesError")
        print(" " + str(e) + "\n")
    except crow.errors.UnknownDeviceError as e:
        print(" caught UnknownDeviceError")
        print(" " + str(e) + "\n")
    except crow.errors.UnknownCommandFormatError as e:
        print(" caught UnknownCommandFormatError")
        print(" " + str(e) + "\n")
    except crow.errors.ServiceLowResourcesError as e:
        print(" caught ServiceLowResourcesError")
        print(" " + str(e) + "\n")
    except crow.errors.RequestTooLargeError as e:
        # RequestTooLargeError inherits from InvalidCommandError
        print(" caught RequestTooLargeError")
        print(" " + str(e) + "\n")
    except crow.errors.CommandNotImplementedError as e:
        # CommandNotImplementedError inherits from CommandNotAvailableError
        print(" caught CommandNotImplementedError")
        print(" " + str(e) + "\n")
    except crow.errors.CommandNotAllowedError as e:
        # CommandNotAllowedError inherits from CommandNotAvailableError
        print(" caught CommandNotAllowedError")
        print(" " + str(e) + "\n")
    except crow.errors.CommandNotAvailableError as e:
        # CommandNotAvailableError inherits from InvalidCommandError
        print(" caught CommandNotAvailableError")
        print(" " + str(e) + "\n")
    except crow.errors.MissingCommandDataError as e:
        # MissingCommandDataError inherits from IncorrectCommandSizeError
        print(" caught MissingCommandDataError")
        print(" " + str(e) + "\n")
    except crow.errors.TooMuchCommandDataError as e:
        # TooMuchCommandDataError inherits from IncorrectCommandSizeError
        print(" caught TooMuchCommandDataError")
        print(" " + str(e) + "\n")
    except crow.errors.IncorrectCommandSizeError as e:
        # IncorrectCommandSizeError inherits from InvalidCommandError
        print(" caught IncorrectCommandSizeError")
        print(" " + str(e) + "\n")
    except crow.errors.InvalidCommandError as e:
        print(" caught InvalidCommandError")
        print(" " + str(e) + "\n")
    except crow.errors.UnknownServiceError as e:
        print(" caught UnknownServiceError")
        print(" " + str(e) + "\n")
    except crow.errors.DeviceError as e:
        print(" caught DeviceError")
        print(" " + str(e) + "\n")
    except crow.errors.ServiceError as e:
        print(" caught ServiceError")
        print(" " + str(e) + "\n")
    except crow.errors.RemoteError as e:
        print(" caught RemoteError")
        print(" " + str(e) + "\n")

def raise_error_number(number, expected_name):
    print("Will raise error number " + str(number) + ", expect " + expected_name + "...")
    t.response = number.to_bytes(1, 'big')
    raise_error()


print("Will raise CrowError...")
try:
    raise crow.errors.CrowError(1, 32)
except crow.errors.CrowError as e:
    print(" caught CrowError")
    print(" " + str(e) + "\n")

print("Will raise error for empty error response, expect RemoteError...")
raise_error()

raise_error_number(0, "RemoteError")
raise_error_number(1, "DeviceError")
raise_error_number(2, "DeviceFaultError")
raise_error_number(3, "ServiceFaultError")
raise_error_number(4, "DeviceUnavailableError")
raise_error_number(5, "DeviceIsBusyError")
raise_error_number(6, "OversizedCommandError")
raise_error_number(7, "CorruptCommandPayloadError")
raise_error_number(8, "PortNotOpenError")
raise_error_number(9, "DeviceLowResourcesError")

print("Will now raise error numbers 10 to 31, which should all result in UnknownDeviceError...\n")
for i in range(10, 32):
    raise_error_number(i, "UnknownDeviceError")

print("Will now raise error numbers 32 to 63, which should all result in DeviceError...\n")
for i in range(32, 64):
    raise_error_number(i, "DeviceError")

raise_error_number(64, "ServiceError")
raise_error_number(65, "UnknownCommandFormatError")
raise_error_number(66, "ServiceLowResourcesError")
raise_error_number(67, "InvalidCommandError")
raise_error_number(68, "RequestTooLargeError")
raise_error_number(69, "CommandNotAvailableError")
raise_error_number(70, "CommandNotImplementedError")
raise_error_number(71, "CommandNotAllowedError")
raise_error_number(72, "IncorrectCommandSizeError")
raise_error_number(73, "MissingCommandDataError")
raise_error_number(74, "TooMuchCommandDataError")

print("Will now raise error numbers 75 to 127, which should all result in UnknownServiceError...\n")
for i  in range(75, 128):
    raise_error_number(i, "UnknownServiceError")

print("Will now raise error numbers 128 to 255, which should all result in ServiceError...\n")
for i in range(128, 256):
    raise_error_number(i, "ServiceError")


