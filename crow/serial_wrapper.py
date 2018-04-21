


import serial


class SerialObj():
    def __init__(self, serial_port):
        self.retain_count = 1
        self.serial = serial.Serial(serial_port)


class SerialWrapper():

    # The purpose of SerialWrapper is to limit the number of serial objects
    #  to one object per serial port.

    _objs = set()

    def __del__(self):
        self._obj.retain_count -= 1
        if self._obj.retain_count == 0:
            SerialWrapper._objs.remove(self._obj)

    def __init__(self, serial_port):
        for obj in SerialWrapper._objs:
            if obj.serial.port == serial_port:
                obj.retain_count += 1
                self._obj = obj
                return
        obj = SerialObj(serial_port)
        SerialWrapper._objs.add(obj)
        self._obj = obj

    @property
    def serial(self):
        return self._obj.serial

    @property
    def serial_port(self):
        return self._obj.serial.port

