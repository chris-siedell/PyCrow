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

if len(sys.argv) < 2:
    sys.exit("Please provide serial port name as command line argument.")
    
s = serial.Serial(sys.argv[1])
s.baudrate = 115200

host = host.Host()
host.serial = s

print("\nCrow Host v2 Demonstration")

# ping
print("\nWill ping address 5...")
start = time.perf_counter()
payload = host.send_command(address=5, port=0)
end = time.perf_counter()
print("payload: " + str(payload))
print("time: " + str(end-start))

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
echo = b'\x53\x41\x00Hello there! echo echo echo'
payload = host.send_command(address=5, payload=echo, port=0, propcr_order=True)
print("payload: " + str(payload))

# admin getDeviceInfo
print("\nWill send getDeviceInfo() admin command...")
getDeviceInfo = b'\x53\x41\x01'
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

