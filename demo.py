# demo for PyCrow
# April 2018
# Chris Siedell

# The following assumes an echoing server at address 5, user port 100, using
#  propcr byte ordering. See "demo.spin".

import time
import serial
import sys

import crow.host.errors
from crow.host.host import Host
from crow.host.admin import CrowAdmin

if len(sys.argv) < 2:
    sys.exit("Please provide serial port name as command line argument.")

port = sys.argv[1]

#s = serial.Serial(sys.argv[1])
#s.baudrate = 115200

host = Host(port)

print("\nCrow Host v2 Demonstration")
print(" port: " + str(port))

s = host.serial

a = CrowAdmin()
a.host = host
a.address = 5
a.propcr_order = True

# ping
print("\nSending ping command...")
t = a.ping()
print("time: " + str(t))

# echo
print("\nSending echo command with no data...")
a.echo(b'')

# echo
print("\nSending echo command with data='echo echo echo'...")
a.echo(b'echo echo echo')

# hostPresence
print("\nSending hostPresence with data=0x555555 (will wait 250ms for serial data -- none expected)...")
a.host_presence(b'\x55\x55\x55')
s.timeout = 0.25
data = s.read(1)
if len(data) > 0:
    raise RuntimeError("Data was received after host_presence -- that shouldn't happen.")

# getDeviceInfo
print("\nSending get_device_info command...")
info = a.get_device_info()
print("device_info: " + str(info))

# getOpenPorts
print("\nSending getOpenPorts command...")
ports = a.get_open_ports()
print("ports: " + str(ports))

# getPortInfo
print("\nWill send getPortInfo command for above ports, plus port 7...")
for p in ports:
    info = a.get_port_info(p)
    print("port " + str(p) + ": " + str(info))
info = a.get_port_info(7)
print("port 7: " + str(info))

# echo
print("\nWill send 0xdeadbeefabcdef01 to an echo server at address 5, port 100...")
test = b'\xde\xad\xbe\xef\xab\xcd\xef\x01'
payload = host.send_command(address=5, payload=test, port=100, propcr_order=True).response
print("payload: " + str(payload))

# max packet
print("\nWill send max sized packet (expect OversizedCommandError)...")
max_payload = bytearray(2047)
try:
    host.send_command(address=5, payload=max_payload, port=100, propcr_order=True)
    raise RuntimeError("Expected sending a max sized packet to raise OversizedCommandError.")
except crow.host.errors.OversizedCommandError as e:
    print("OversizedCommandError caught")
    print(str(e))

# ping again
print("\nWill send empty command to address 5, port 0 (ping, expect empty response)...")
start = time.perf_counter()
payload = host.send_command(address=5, port=0).response
end = time.perf_counter()
print("payload: " + str(payload))
print("time: " + str(end-start))

# broadcast ping (shouldn't see any response)
print("\nWill ping address 0 (no response expected)...")
start = time.perf_counter()
payload = host.send_command(address=0, port=0, response_expected=False).response
end = time.perf_counter()
print("payload: " + str(payload))
print("time: " + str(end-start))
s.timeout = 0.25
data = s.read(1)
if len(data) > 0:
    raise RuntimeError("Data was received after broadcast ping -- that shouldn't happen.")

# no response command
print("\nWill send payload to 5:100 with response_expected == False...")
payload = host.send_command(address=5, payload=b'Please do not respond.', port=100, response_expected=False, propcr_order=True).response
print("payload: " + str(payload))
s.timeout = 0.25
data = s.read(1)
if len(data) > 0:
    raise RuntimeError("Data was received after packet send to port 100 with response_expected=False -- that shouldn't happen.")

# ping again
print("\nWill ping address 5...")
start = time.perf_counter()
payload = host.send_command(address=5, port=0).response
end = time.perf_counter()
print("payload: " + str(payload))
print("time: " + str(end-start))

# wrong address
print("\nWill send 'is anyone there?' to 20:100 (expect NoResponseError)...")
try:
    host.send_command(address=20, payload=b'is anyone there?', port=100, propcr_order=True)
    raise RuntimeError("Expected send_command to raise NoResponseError.")
except crow.host.errors.NoResponseError as e:
    print("Caught NoResponseError")
    print(str(e))

# wrong port
print("\nWill send 'port should be closed' to 5:101 (expect PortNotOpenError)...")
try:
    host.send_command(address=5, payload=b'port should be closed', port=101, propcr_order=True)
    raise RuntimeError("Expected send_command to raise PortNotOpenError.")
except crow.host.errors.PortNotOpenError as e:
    print("Caught PortNotOpenError")
    print(str(e))

# admin echo
print("\nWill send raw echo admin command...")
echo = b'\x43\x41\x00Hello there! echo echo echo'
payload = host.send_command(address=5, payload=echo, port=0, propcr_order=True).response
print("payload: " + str(payload))

# admin getDeviceInfo
print("\nWill send raw getDeviceInfo admin command...")
getDeviceInfo = b'\x43\x41\x01'
payload = host.send_command(address=5, payload=getDeviceInfo, port=0, propcr_order=True).response
print("payload: " + str(payload))

# non-admin command to admin port (expect UnknownProtocolError)
print("\nWill send non-admin command to admin port...")
try:
    host.send_command(address=5, payload=b'gooblygook', port=0, propcr_order=True)
    raise RuntimeError("Expected send_command to raise UnknownCommandFormatError.")
except crow.host.errors.UnknownCommandFormatError as e:
    print("Caught UnknownCommandFormat")
    print(str(e))

# final echo
print("\nWill send 'goodbye!' to 5:100...")
payload = host.send_command(address=5, payload=b'goodbye!', port=100, propcr_order=True).response
print("payload: " + str(payload))

