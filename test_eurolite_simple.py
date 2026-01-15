#!/usr/bin/env python3
"""
Simple, robust test for Eurolite DMX -> Smoke Machine
Focuses on most common scenarios
"""

import serial
import time
import sys

ENTTEC_PRO_START_OF_MSG = 0x7E
ENTTEC_PRO_SEND_DMX_RQ = 0x06
ENTTEC_PRO_END_OF_MSG = 0xE7

def create_packet(dmx_data):
    """Create Enttec Pro DMX packet"""
    data_length = len(dmx_data)
    packet = bytearray()
    packet.append(ENTTEC_PRO_START_OF_MSG)
    packet.append(ENTTEC_PRO_SEND_DMX_RQ)
    packet.append(data_length & 0xFF)
    packet.append((data_length >> 8) & 0xFF)
    packet.extend(dmx_data)
    packet.append(ENTTEC_PRO_END_OF_MSG)
    return bytes(packet)

def test_scenario(ser, channels, values, duration=5, description=""):
    """Test a specific channel/value scenario"""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"{'='*60}")
    print(f"Channels: {channels}")
    print(f"Values: {values}")
    print(f"Duration: {duration}s")
    print(f"\n👀 Watch the smoke machine NOW!")
    
    dmx = bytearray([0] * 512)
    for ch, val in zip(channels, values):
        dmx[ch - 1] = val
    
    packet = create_packet(dmx)
    
    start_time = time.time()
    packet_count = 0
    
    try:
        while time.time() - start_time < duration:
            try:
                ser.write(packet)
                ser.flush()
                packet_count += 1
                if packet_count % 10 == 0:
                    print(f"  Sent {packet_count} packets...", end='\r')
                time.sleep(0.05)
            except Exception as e:
                print(f"\n  ⚠ Write error: {e}")
                time.sleep(0.2)
                break
        
        print(f"\n  ✓ Sent {packet_count} packets")
        time.sleep(1)
        
    except Exception as e:
        print(f"\n  ✗ Error: {e}")

def main():
    port = '/dev/cu.usbserial-A10KRSG3'
    
    print("="*60)
    print("EUROLITE DMX -> SMOKE MACHINE TEST")
    print("="*60)
    
    # Get test parameters
    test_num = 1
    if len(sys.argv) > 1:
        try:
            test_num = int(sys.argv[1])
        except:
            pass
    
    try:
        ser = serial.Serial(port, 57600, timeout=2, write_timeout=2)
        time.sleep(0.3)
        print(f"\n✓ Connected to {port} at 57600 baud\n")
        
        if test_num == 1:
            # Test 1: Channel 1 only
            test_scenario(ser, [1], [255], duration=5, 
                        description="Channel 1 = 255 (DMX Address 1)")
        
        elif test_num == 2:
            # Test 2: Channel 1 + 2
            test_scenario(ser, [1, 2], [255, 255], duration=5,
                        description="Channel 1 = 255, Channel 2 = 255")
        
        elif test_num == 3:
            # Test 3: Channel 10
            test_scenario(ser, [10], [255], duration=5,
                        description="Channel 10 = 255 (DMX Address 10)")
        
        elif test_num == 4:
            # Test 4: Scan channels 1-5
            for ch in range(1, 6):
                test_scenario(ser, [ch], [255], duration=3,
                            description=f"Channel {ch} = 255")
        
        elif test_num == 5:
            # Test 5: Try different intensity values
            for intensity in [50, 127, 200, 255]:
                test_scenario(ser, [1], [intensity], duration=3,
                            description=f"Channel 1 = {intensity}")
        
        # Turn off
        print(f"\n{'='*60}")
        print("TURNING OFF")
        print(f"{'='*60}")
        dmx_off = bytearray([0] * 512)
        packet_off = create_packet(dmx_off)
        for i in range(5):
            try:
                ser.write(packet_off)
                ser.flush()
                time.sleep(0.1)
            except:
                pass
        
        ser.close()
        print("✓ Test completed\n")
        
        print("="*60)
        print("RESULTS")
        print("="*60)
        print("\nDid the smoke machine respond?")
        print("  - LED indicator?")
        print("  - Sound/beep?")
        print("  - Heating up?")
        print("  - Fan spinning?")
        print("  - Smoke output?")
        print("\nIf NO response, try:")
        print("  python3 test_eurolite_simple.py 2  # Test channels 1+2")
        print("  python3 test_eurolite_simple.py 3  # Test channel 10")
        print("  python3 test_eurolite_simple.py 4  # Scan channels 1-5")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
