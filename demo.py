# testing
# April 2018
# Chris Siedell
# http://siedell.com/projects/Crow/

# The following assumes a peekpoke server at address 6, user port 0xafaf,
# and an echoing server at address 5, user port 0. Both servers are assumed
# to use PropCR. See "demo.spin".

import time
import serial
import sys
from crow import host
import crow.errors
from crow.admin import CrowAdmin

if len(sys.argv) < 2:
    sys.exit("Please provide serial port name as command line argument.")
    
s = serial.Serial(sys.argv[1])
s.baudrate = 115200

host = host.Host()
host.serial = s

print("\nCrow Host v2 Demonstration")

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
print("\nSending hostPresence with data=0x555555 (will sleep 100ms afterwards)...")
a.host_presence(b'\x55\x55\x55')
time.sleep(0.1)

# getDeviceInfo
print("\nSending get_device_info command...")
info = a.get_device_info()
print("device_info: " + str(info))

#print("type: "+str(type(ports[0])))
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
payload = host.send_command(address=5, payload=test, port=100, propcr_order=True)
print("payload: " + str(payload))

# max packet
print("\nWill send max sized packet (expect CommandTooLargeError)...")
max_payload = bytearray(2047)
try:
    payload = host.send_command(address=5, payload=max_payload, port=100, propcr_order=True)
    print("payload: " + str(payload))
except crow.errors.CommandTooLargeError as e:
    print("CommandTooLargeError caught")
    print(str(e))

# ping again
print("\nWill ping address 5...")
start = time.perf_counter()
payload = host.send_command(address=5, port=0)
end = time.perf_counter()
print("payload: " + str(payload))
print("time: " + str(end-start))

# broadcast ping (shouldn't see any response)
print("\nWill ping address 0 (no response expected)...")
start = time.perf_counter()
payload = host.send_command(address=0, port=0, response_expected=False)
end = time.perf_counter()
print("payload: " + str(payload))
print("time: " + str(end-start))

# no response command
print("\nWill send payload to 5:100 with response_expected == False...")
payload = host.send_command(address=5, payload=b'Please do not respond.', port=100, response_expected=False, propcr_order=True)
print("payload: " + str(payload))

# ping again
print("\nWill ping address 5...")
start = time.perf_counter()
payload = host.send_command(address=5, port=0)
end = time.perf_counter()
print("payload: " + str(payload))
print("time: " + str(end-start))

# wrong address
print("\nWill send 'is anyone there?' to 20:100 (expect NoResponseError)...")
try:
    payload = host.send_command(address=20, payload=b'is anyone there?', port=100, propcr_order=True)
    print("payload: " + str(payload))
except crow.errors.NoResponseError as e:
    print("Caught NoResponseError")
    print(str(e))

# wrong port
print("\nWill send 'port should be closed' to 5:101 (expect PortNotOpenError)...")
try:
    payload = host.send_command(address=5, payload=b'port should be closed', port=101, propcr_order=True)
    print("payload: " + str(payload))
except crow.errors.PortNotOpenError as e:
    print("Cause PortNotOpenError")
    print(str(e))

# admin echo
print("\nWill send echo() admin command...")
echo = b'\x43\x41\x00Hello there! echo echo echo'
payload = host.send_command(address=5, payload=echo, port=0, propcr_order=True)
print("payload: " + str(payload))

# admin getDeviceInfo
print("\nWill send getDeviceInfo() admin command...")
getDeviceInfo = b'\x43\x41\x01'
payload = host.send_command(address=5, payload=getDeviceInfo, port=0, propcr_order=True)
print("payload: " + str(payload))

# non-admin command to admin port (expect UnknownProtocolError)
print("\nWill send non-admin command to admin port...")
try:
    payload = host.send_command(address=5, payload=b'gooblygook', port=0, propcr_order=True)
    print("payload: " + str(payload))
except crow.errors.UnknownProtocolError as e:
    print("Caught UnknownProtocolError")
    print(str(e))

# final echo
print("\nWill send 'goodbye!' to 5:100...")
payload = host.send_command(address=5, payload=b'goodbye!', port=100, propcr_order=True)
print("payload: " + str(payload))

