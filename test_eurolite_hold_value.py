#!/usr/bin/env python3
"""
Hold specific DMX values longer to test smoke machine response
Some machines need values held for several seconds
"""

import serial
import time
import sys

ENTTEC_PRO_START_OF_MSG = 0x7E
ENTTEC_PRO_SEND_DMX_RQ = 0x06
ENTTEC_PRO_END_OF_MSG = 0xE7

def create_packet(dmx_data):
    data_length = len(dmx_data)
    packet = bytearray()
    packet.append(ENTTEC_PRO_START_OF_MSG)
    packet.append(ENTTEC_PRO_SEND_DMX_RQ)
    packet.append(data_length & 0xFF)
    packet.append((data_length >> 8) & 0xFF)
    packet.extend(dmx_data)
    packet.append(ENTTEC_PRO_END_OF_MSG)
    return bytes(packet)

def main():
    port = '/dev/cu.usbserial-A10KRSG3'
    
    # Get value to test (default 120)
    value = 120
    if len(sys.argv) > 1:
        try:
            value = int(sys.argv[1])
        except:
            pass
    
    duration = 10  # Hold for 10 seconds
    if len(sys.argv) > 2:
        try:
            duration = int(sys.argv[2])
        except:
            pass
    
    print("="*60)
    print(f"HOLDING DMX VALUE {value} FOR {duration} SECONDS")
    print("="*60)
    print(f"\nThis will continuously send Channel 1 = {value}")
    print("Watch for:")
    print("  - LED turning green")
    print("  - Smoke machine heating up")
    print("  - Smoke output")
    print(f"\nStarting in 2 seconds...\n")
    time.sleep(2)
    
    try:
        ser = serial.Serial(port, 57600, timeout=2, write_timeout=2)
        time.sleep(0.3)
        
        dmx = bytearray([0] * 512)
        dmx[0] = value
        packet = create_packet(dmx)
        
        start_time = time.time()
        packet_count = 0
        
        print(f"Sending packets...")
        while time.time() - start_time < duration:
            ser.write(packet)
            ser.flush()
            packet_count += 1
            elapsed = time.time() - start_time
            if packet_count % 20 == 0:
                print(f"  {elapsed:.1f}s - {packet_count} packets sent...", end='\r')
            time.sleep(0.05)
        
        print(f"\n✓ Sent {packet_count} packets over {duration} seconds")
        
        # Turn off
        print("\nTurning off...")
        dmx_off = bytearray([0] * 512)
        packet_off = create_packet(dmx_off)
        for _ in range(10):
            ser.write(packet_off)
            ser.flush()
            time.sleep(0.05)
        
        ser.close()
        
        print("\n" + "="*60)
        print("Did the smoke machine respond?")
        print("="*60)
        print(f"\nIf YES, the working value is: {value}")
        print(f"If NO, try:")
        print(f"  python3 test_eurolite_hold_value.py 240 10  # Test value 240")
        print(f"  python3 test_eurolite_hold_value.py 255 10  # Test value 255")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
