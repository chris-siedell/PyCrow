# A demonstration for using the Crow host.
# 3 April 2018
# Chris Siedell
# http://www.siedell.com/projects/Crow/

# The following assumes a peekpoke server at address 6, user port 0xafaf,
# and an echoing server at address 5, user port 0. Both servers are assumed
# to use PropCR. See "demo.spin".

import time
import serial
import sys
from crow import crowhost

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
            print('  is_final: ' + str(item['is_final']))
            if len(item['payload']) > 0:
                print('  payload: ' + item['payload'].hex())
            else:
                print('  payload: (empty)')
    
s = serial.Serial(sys.argv[1])
s.baudrate = 115200

host = crowhost.CrowHost()
host.serial = s

print("Crow Host v1 Demonstration")

# ping
print("Will ping address 6...")
start = time.perf_counter()
result = host.send_command(address=6, is_user=False)
end = time.perf_counter()
print_results(result)
print(" Time: " + str(end-start))

# read long at hub address 0
print("Will send PeekPoke command readLongs(0, 1) to address 6, port 0xafaf...")
readClkfreq = b'\x50\x50\x02\x00\x00\x00\x00\x00'
result = host.send_command(address=6, port=0xafaf, payload=readClkfreq, propcr_order=True)
print_results(result)
print(" The returned long should be the last four of eight bytes.")
print(" For reference: 80e6 = 0x04c4b400 (MSB first -- result will be reversed).")

# echo
print("Will send 0xdeadbeefabcdef01 to an echo server at address 5, port 0...")
test = b'\xde\xad\xbe\xef\xab\xcd\xef\x01'
result = host.send_command(address=5, payload=test, propcr_order=True)
print_results(result)

