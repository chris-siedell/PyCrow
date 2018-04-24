# Crow Host Serial Port
# 24 April 2018
# Chris Siedell
# project: https://pypi.org/project/crow-serial/
# source: https://github.com/chris-siedell/PyCrow


import serial


class HostSerialPort():

    # HostSerialPort represents a serial port used by a Crow host. It maintains a reference
    #  to a serial.Serial instance and manages the settings for all 32 Crow addresses
    #  associated with the serial port.
    # HostSerialPort objects are intended to be created internally by the Host class.
    # The port property of the wrapped serial.Serial object should not change.
    # Host is designed so that only one SerialPort object is created for each port name,
    #  regardless of how many hosts are using that port. Settings changes made by one user
    #  to a serial port and address will apply to all users.

    # Using HostSerialPort.ALL as the address for the set_<serial setting> methods will cause
    #  the change to be applied to all addresses.
    ALL = -1

    def __init__(self, serial_port_name, baudrate=115200, transaction_timeout=0.25, propcr_order=False, _magic_word=None):
        if _magic_word != "abracadabra":
            raise RuntimeError("Cannot create HostSerialPort instance. HostSerialPort instances are created internally by the Host class.")
        self.retain_count = None
        self._serial = serial.Serial(serial_port_name)
        self._settings = []
        for i in range(0, 32):
            self._settings.append(HostSerialSettings());
        self.default_baudrate = baudrate
        self.default_transaction_timeout = transaction_timeout
        self.default_propcr_order = propcr_order

    def __repr__(self):
        return "<{0} instance at {1:#x}, name='{2}', retain_count={3}>".format(self.__class__.__name__, id(self), self._serial.port, self.retain_count)

    # Warning: do not change the port property of the serial object.
    @property
    def serial(self):
        return self._serial

    @property
    def name(self):
        return self._serial.port

    def get_baudrate(self, address):
        if address < 0 or address > 31:
            raise ValueError("The address must be 0 to 31.")
        value = self._settings[address].baudrate
        if value is not None:
            return value
        else:
            return self.default_baudrate

    def get_transaction_timeout(self, address):
        if address < 0 or address > 31:
            raise ValueError("The address must be 0 to 31.")
        value = self._settings[address].transaction_timeout
        if value is not None:
            return value
        else:
            return self.default_transaction_timeout

    def get_propcr_order(self, address):
        if address < 0 or address > 31:
            raise ValueError("The address must be 0 to 31.")
        value = self._settings[address].propcr_order
        if value is not None:
            return value
        else:
            return self.default_propcr_order

    def set_baudrate(self, address, baudrate):
        if address == HostSerialPort.ALL:
            for s in self._settings:
                s.baudrate = baudrate
        elif address >= 0 and address <= 31:
            self._settings[address].baudrate = baudrate
        else:
            raise ValueError("The address must be 0 to 31, or HostSerialPort.ALL.")

    def set_transaction_timeout(self, address, transaction_timeout):
        if address == HostSerialPort.ALL:
            for s in self._settings:
                s.transaction_timeout = transaction_timeout
        elif address >= 0 and address <= 31:
            self._settings[address].transaction_timeout = transaction_timeout
        else:
            raise ValueError("The address must be 0 to 31, or HostSerialPort.ALL.")

    def set_propcr_order(self, address, propcr_order):
        if address == HostSerialPort.ALL:
            for s in self._settings:
                s.propcr_order = propcr_order
        elif address >= 0 and address <= 31:
            self._settings[address].propcr_order = propcr_order
        else:
            raise ValueError("The address must be 0 to 31, or HostSerialPort.ALL.")


class HostSerialSettings():

    # SerialSettings stores settings used by Crow hosts and clients.
    # Values of None indicate that defaults should be used.

    def __init__(self):
        self.baudrate = None
        self.transaction_timeout = None
        self.propcr_order = None

    def __repr__(self):
        return "<{0} instance at {1:#x}, baudrate={2}, transaction_timeout={3}, propcr_order={4}>".format(self.__class__.__name__, id(self), self.baudrate, self.transaction_timeout, self.propcr_order)



