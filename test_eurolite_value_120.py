#!/usr/bin/env python3
"""
Test DMX values around 120 (since MIDI CC 120 worked)
"""

import serial
import time

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

def test_value(ser, value, duration=5):
    """Test a specific DMX value"""
    print(f"\n{'='*60}")
    print(f"Testing Channel 1 = {value} (DMX value, was MIDI CC 120)")
    print(f"{'='*60}")
    print(f"👀 Watch the LED and smoke machine!")
    
    dmx = bytearray([0] * 512)
    dmx[0] = value  # Channel 1
    
    packet = create_packet(dmx)
    
    start_time = time.time()
    packet_count = 0
    
    while time.time() - start_time < duration:
        ser.write(packet)
        ser.flush()
        packet_count += 1
        if packet_count % 10 == 0:
            print(f"  Sent {packet_count} packets...", end='\r')
        time.sleep(0.05)
    
    print(f"\n  ✓ Sent {packet_count} packets")
    print(f"  Did LED turn green? Did smoke start?")
    time.sleep(2)

def main():
    port = '/dev/cu.usbserial-A10KRSG3'
    
    print("="*60)
    print("TESTING DMX VALUES AROUND 120")
    print("="*60)
    print("\nSince MIDI CC 120 worked, let's test DMX values:")
    print("  - MIDI CC values: 0-127")
    print("  - DMX values: 0-255")
    print("  - MIDI CC 120 ≈ DMX 120 (direct mapping)")
    print("  - Or MIDI CC 120 ≈ DMX 240 (scaled: 120*2)")
    
    try:
        ser = serial.Serial(port, 57600, timeout=2, write_timeout=2)
        time.sleep(0.3)
        print(f"\n✓ Connected to {port}\n")
        
        # Test the exact value that worked with MIDI
        print("\nStarting in 2 seconds...\n")
        time.sleep(2)
        
        # Test 1: Exact value 120 (direct mapping)
        test_value(ser, 120, duration=5)
        
        # Test 2: Scaled value (120 * 2 = 240)
        test_value(ser, 240, duration=5)
        
        # Test 3: Range around 120
        print(f"\n{'='*60}")
        print("Testing range 100-140 (5 seconds each)")
        print(f"{'='*60}")
        for value in [100, 110, 120, 130, 140]:
            print(f"\nTesting value {value}...", end='', flush=True)
            dmx = bytearray([0] * 512)
            dmx[0] = value
            packet = create_packet(dmx)
            start_time = time.time()
            while time.time() - start_time < 5:
                ser.write(packet)
                ser.flush()
                time.sleep(0.05)
            print(" ✓")
            time.sleep(1)
        
        # Test 4: Higher values (some machines need high values)
        print(f"\n{'='*60}")
        print("Testing higher values 200-255")
        print(f"{'='*60}")
        for value in [200, 220, 240, 255]:
            print(f"\nTesting value {value}...", end='', flush=True)
            dmx = bytearray([0] * 512)
            dmx[0] = value
            packet = create_packet(dmx)
            start_time = time.time()
            while time.time() - start_time < 5:
                ser.write(packet)
                ser.flush()
                time.sleep(0.05)
            print(" ✓")
            time.sleep(1)
        
        # Turn off
        print(f"\n{'='*60}")
        print("TURNING OFF")
        print(f"{'='*60}")
        dmx_off = bytearray([0] * 512)
        packet_off = create_packet(dmx_off)
        for _ in range(5):
            ser.write(packet_off)
            ser.flush()
            time.sleep(0.1)
        
        ser.close()
        
        print("\n" + "="*60)
        print("RESULTS")
        print("="*60)
        print("\nWhich value made the LED turn green?")
        print("Which value produced smoke?")
        print("\nOnce we know the working value, we can use it in the Pi!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
