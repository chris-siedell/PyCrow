# testing
# April 2018
# Chris Siedell
# http://www.siedell.com/projects/Crow/

# The following assumes a peekpoke server at address 6, user port 0xafaf,
# and an echoing server at address 5, user port 0. Both servers are assumed
# to use PropCR. See "demo.spin".

import time
import serial
import sys
from crow import host

if len(sys.argv) < 2:
    sys.exit("Please provide serial port name as command line argument.")

def print_results(results):
    for item in results:
        print(" Result type: " + item['type'])
        if item['type'] == 'extra':
            print("  data: " + item['data'].hex())
        elif item['type'] == 'error':
            print('  message: ' + item['message'])
        elif item['type'] == 'response':
            print('  is_error: ' + str(item['is_error']))
            if len(item['payload']) > 0:
                print('  payload: ' + item['payload'].hex())
            else:
                print('  payload: (empty)')
    
s = serial.Serial(sys.argv[1])
s.baudrate = 115200

host = host.Host()
host.serial = s

print("Crow Host v2 Demonstration")

# ping
print("Will ping address 5...")
start = time.perf_counter()
result = host.send_command(address=5, port=0)
end = time.perf_counter()
print_results(result)
print(" Time: " + str(end-start))

#'# read long at hub address 0
#'print("Will send PeekPoke command readLongs(0, 1) to address 6, port 0xafaf...")
#'readClkfreq = b'\x50\x50\x02\x00\x00\x00\x00\x00'
#'result = host.send_command(address=6, port=0xafaf, payload=readClkfreq, propcr_order=True)
#'print_results(result)
#'print(" The returned long should be the last four of eight bytes.")
#'print(" For reference: 80e6 = 0x04c4b400 (MSB first -- result will be reversed).")
#'

# echo
print("Will send 0xdeadbeefabcdef01 to an echo server at address 5, port 100...")
test = b'\xde\xad\xbe\xef\xab\xcd\xef\x01'
result = host.send_command(address=5, payload=test, port=100, propcr_order=True)
print_results(result)

# max packet
print("Will send max sized packet (expect CommandTooBig error)...")
max_payload = bytearray(2047)
result = host.send_command(address=5, payload=max_payload, port=100, propcr_order=True)
print_results(result)

# ping again
print("Will ping address 5...")
start = time.perf_counter()
result = host.send_command(address=5, port=0)
end = time.perf_counter()
print_results(result)
print(" Time: " + str(end-start))

# broadcast ping (shouldn't see any response)
print("Will ping address 0 (no response expected)...")
start = time.perf_counter()
result = host.send_command(address=0, port=0, response_expected=False)
end = time.perf_counter()
print_results(result)
print(" Time: " + str(end-start))

# no response command
print("Will send payload to 5:100 with response_expected == False...")
result = host.send_command(address=5, payload=b'Please do not respond.', port=100, response_expected=False, propcr_order=True)
print_results(result)

# ping again
print("Will ping address 5...")
start = time.perf_counter()
result = host.send_command(address=5, port=0)
end = time.perf_counter()
print_results(result)
print(" Time: " + str(end-start))

# wrong address
print("Will send 'is anyone there?' to 20:100...")
result = host.send_command(address=20, payload=b'is anyone there?', port=100, propcr_order=True)
print_results(result)

# wrong port
print("Will send 'port should be closed' to 5:101...")
result = host.send_command(address=5, payload=b'port should be closed', port=101, propcr_order=True)
print_results(result)


# admin echo
print("Will send echo() admin command...")
echo = b'\x53\x41\x00Hello there! echo echo echo'
result = host.send_command(address=5, payload=echo, port=0, propcr_order=True)
print_results(result)

# admin getDeviceInfo
print("Will send getDeviceInfo() admin command...")
getDeviceInfo = b'\x53\x41\x01'
result = host.send_command(address=5, payload=getDeviceInfo, port=0, propcr_order=True)
print_results(result)

# non-admin command to admin port (expect UnknownProtocol error)
print("Will send non-admin command to admin port...")
result = host.send_command(address=5, payload=b'gooblygook', port=0, propcr_order=True)
print_results(result)

# final echo
print("Will send 'goodbye!' to 5:100...")
result = host.send_command(address=5, payload=b'goodbye!', port=100, propcr_order=True)
print_results(result)
