#!/usr/bin/env python3
"""
Test combinations - maybe smoke machine needs multiple channels
Some machines need: Channel 1 (intensity) + Channel 2 (fan/speed)
"""

import serial
import time
import termios

ENTTEC_PRO_START_OF_MSG = 0x7E
ENTTEC_PRO_SEND_DMX_RQ = 0x06
ENTTEC_PRO_END_OF_MSG = 0xE7

def create_enttec_packet(dmx_data):
    """Create Enttec Pro packet"""
    data_length = len(dmx_data)
    packet = bytearray()
    packet.append(ENTTEC_PRO_START_OF_MSG)
    packet.append(ENTTEC_PRO_SEND_DMX_RQ)
    packet.append(data_length & 0xFF)
    packet.append((data_length >> 8) & 0xFF)
    packet.extend(dmx_data)
    packet.append(ENTTEC_PRO_END_OF_MSG)
    return bytes(packet)

def test_combination(ser, ch1_val, ch2_val, duration=8, description=""):
    """Test a combination of channels"""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"{'='*60}")
    print(f"Channel 1 = {ch1_val}")
    print(f"Channel 2 = {ch2_val}")
    print(f"Duration: {duration}s")
    print(f"\n👀 Watch LED and smoke machine!")
    
    dmx = bytearray([0] * 512)
    dmx[0] = ch1_val  # Channel 1
    dmx[1] = ch2_val  # Channel 2
    
    packet = create_enttec_packet(dmx)
    
    start_time = time.time()
    packet_count = 0
    
    while time.time() - start_time < duration:
        ser.write(packet)
        ser.flush()
        packet_count += 1
        elapsed = time.time() - start_time
        if packet_count % 20 == 0:
            print(f"  {elapsed:.1f}s - {packet_count} packets...", end='\r')
        time.sleep(0.05)
    
    print(f"\n  ✓ Sent {packet_count} packets")
    print(f"  Did LED turn green? Did smoke start?")
    time.sleep(2)

def main():
    port = '/dev/cu.usbserial-A10KRSG3'
    
    print("="*60)
    print("TESTING CHANNEL COMBINATIONS")
    print("="*60)
    print("\nSome smoke machines need:")
    print("  - Channel 1: Intensity/Smoke level")
    print("  - Channel 2: Fan speed or on/off")
    print("\nSince MIDI CC 120 worked, let's test combinations...")
    
    try:
        ser = serial.Serial(port, 57600, timeout=2, write_timeout=2)
        time.sleep(0.3)
        print(f"\n✓ Connected to {port}\n")
        print("Starting in 2 seconds...\n")
        time.sleep(2)
        
        # Test 1: Ch1=120, Ch2=0 (what MIDI might have mapped to)
        test_combination(ser, 120, 0, duration=8,
                        description="Channel 1=120, Channel 2=0")
        
        # Test 2: Ch1=120, Ch2=255 (intensity + fan max)
        test_combination(ser, 120, 255, duration=8,
                        description="Channel 1=120, Channel 2=255 (fan max)")
        
        # Test 3: Ch1=255, Ch2=255 (both max)
        test_combination(ser, 255, 255, duration=8,
                        description="Channel 1=255, Channel 2=255 (both max)")
        
        # Test 4: Ch1=120, Ch2=120 (both same)
        test_combination(ser, 120, 120, duration=8,
                        description="Channel 1=120, Channel 2=120")
        
        # Test 5: Ch1=200, Ch2=200 (higher values)
        test_combination(ser, 200, 200, duration=8,
                        description="Channel 1=200, Channel 2=200")
        
        # Turn off
        print(f"\n{'='*60}")
        print("TURNING OFF")
        print(f"{'='*60}")
        dmx_off = bytearray([0] * 512)
        packet_off = create_enttec_packet(dmx_off)
        for _ in range(10):
            ser.write(packet_off)
            ser.flush()
            time.sleep(0.05)
        
        ser.close()
        
        print("\n" + "="*60)
        print("RESULTS")
        print("="*60)
        print("\nWhich combination (if any) made the smoke machine work?")
        print("\nAlso, when MIDI CC 120 worked yesterday:")
        print("  - Was it immediate smoke, or did it take time to heat up?")
        print("  - Did the LED turn green?")
        print("  - How long did you hold the MIDI CC value?")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
