#!/usr/bin/env python3
"""
Automated troubleshooting - tests multiple scenarios
"""

import serial
import time

ENTTEC_PRO_START_OF_MSG = 0x7E
ENTTEC_PRO_SEND_DMX_RQ = 0x06
ENTTEC_PRO_END_OF_MSG = 0xE7

def create_enttec_pro_dmx_packet(dmx_data):
    data_length = len(dmx_data)
    lsb = data_length & 0xFF
    msb = (data_length >> 8) & 0xFF
    packet = bytearray()
    packet.append(ENTTEC_PRO_START_OF_MSG)
    packet.append(ENTTEC_PRO_SEND_DMX_RQ)
    packet.append(lsb)
    packet.append(msb)
    packet.extend(dmx_data)
    packet.append(ENTTEC_PRO_END_OF_MSG)
    return bytes(packet)

def send_dmx_test(ser, dmx_data, duration=3):
    """Send DMX data"""
    packet = create_enttec_pro_dmx_packet(dmx_data)
    start_time = time.time()
    packet_count = 0
    while time.time() - start_time < duration:
        try:
            ser.write(packet)
            ser.flush()
            packet_count += 1
            time.sleep(0.05)
        except Exception as e:
            print(f"    Warning: {e}")
            time.sleep(0.1)
            break
    return packet_count

def main():
    port = '/dev/cu.usbserial-A10KRSG3'
    
    print("="*70)
    print("AUTOMATED DMX TROUBLESHOOTING")
    print("="*70)
    print("\nStarting tests in 2 seconds...")
    print("Watch the smoke machine for ANY response!\n")
    time.sleep(2)
    
    try:
        ser = serial.Serial(port, 57600, timeout=1, write_timeout=1)
        time.sleep(0.2)
        print("✓ Serial port opened\n")
        
        # Test 1: Channel 1
        print("TEST 1: Channel 1 = 255 (3 seconds)")
        dmx = bytearray([0] * 512)
        dmx[0] = 255
        send_dmx_test(ser, dmx, duration=3)
        print("  ✓ Sent packets - did machine respond?\n")
        time.sleep(1)
        
        # Test 2: Channel 1 + 2
        print("TEST 2: Channel 1 = 255, Channel 2 = 255 (3 seconds)")
        dmx = bytearray([0] * 512)
        dmx[0] = 255
        dmx[1] = 255
        send_dmx_test(ser, dmx, duration=3)
        print("  ✓ Sent packets - did machine respond?\n")
        time.sleep(1)
        
        # Test 3: Channel 10
        print("TEST 3: Channel 10 = 255 (3 seconds)")
        dmx = bytearray([0] * 512)
        dmx[9] = 255
        send_dmx_test(ser, dmx, duration=3)
        print("  ✓ Sent packets - did machine respond?\n")
        time.sleep(1)
        
        # Test 4: Scan channels 1-10 quickly
        print("TEST 4: Scanning channels 1-10 (2 seconds each)")
        for channel in range(1, 11):
            dmx = bytearray([0] * 512)
            dmx[channel - 1] = 255
            print(f"  Channel {channel}...", end='', flush=True)
            send_dmx_test(ser, dmx, duration=2)
            print(" ✓")
            time.sleep(0.5)
        
        # Test 5: Different intensities on channel 1
        print("\nTEST 5: Channel 1 with different intensities")
        for intensity in [127, 200, 255]:
            dmx = bytearray([0] * 512)
            dmx[0] = intensity
            print(f"  Intensity {intensity}...", end='', flush=True)
            send_dmx_test(ser, dmx, duration=2)
            print(" ✓")
            time.sleep(0.5)
        
        # Test 6: High refresh rate
        print("\nTEST 6: High refresh rate (40 packets/sec)")
        dmx = bytearray([0] * 512)
        dmx[0] = 255
        packet = create_enttec_pro_dmx_packet(dmx)
        start_time = time.time()
        packet_count = 0
        while time.time() - start_time < 3:
            ser.write(packet)
            ser.flush()
            packet_count += 1
            time.sleep(0.025)
        print(f"  ✓ Sent {packet_count} packets")
        
        # Turn off
        print("\nTurning off...")
        dmx = bytearray([0] * 512)
        packet_off = create_enttec_pro_dmx_packet(dmx)
        for _ in range(10):
            ser.write(packet_off)
            ser.flush()
            time.sleep(0.05)
        
        ser.close()
        
        print("\n" + "="*70)
        print("TESTS COMPLETED")
        print("="*70)
        print("\nPlease answer:")
        print("1. Did the smoke machine show ANY response?")
        print("   - LED, sound, heating, fan, smoke?")
        print("\n2. What are the DIP switch settings?")
        print("   (All OFF = address 1, Switch 2+4 ON = address 10)")
        print("\n3. What model is the smoke machine?")
        print("   (Check manual for DMX channel mapping)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
