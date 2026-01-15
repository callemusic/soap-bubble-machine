#!/usr/bin/env python3
"""
Test what DOREMiDi might actually send
DOREMiDi MTD-10-ABCD converts MIDI CC to DMX

If MIDI CC 1, value 120, Channel 1 worked, what DMX did it send?
Common mappings:
- MIDI CC 1 → DMX Channel 1 (direct)
- MIDI CC value 120 → DMX value 120 (direct) OR 240 (scaled)
- But DOREMiDi might use different mapping
"""

import serial
import time

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

def test_mapping(ser, dmx_channel, dmx_value, duration=8):
    """Test a specific DMX channel/value mapping"""
    print(f"\n{'='*60}")
    print(f"DMX Channel {dmx_channel} = {dmx_value}")
    print(f"{'='*60}")
    print(f"👀 Watch LED and smoke machine!")
    
    dmx = bytearray([0] * 512)
    dmx[dmx_channel - 1] = dmx_value
    
    packet = create_packet(dmx)
    
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
    time.sleep(2)

def main():
    port = '/dev/cu.usbserial-A10KRSG3'
    
    print("="*60)
    print("TESTING DOREMiDi POSSIBLE MAPPINGS")
    print("="*60)
    print("\nDOREMiDi MTD-10-ABCD might map:")
    print("  MIDI CC 1, value 120 → DMX Channel X, value Y")
    print("\nLet's test different possibilities...")
    
    try:
        ser = serial.Serial(port, 57600, timeout=2, write_timeout=2)
        time.sleep(0.3)
        print(f"\n✓ Connected to {port}\n")
        print("Starting in 2 seconds...\n")
        time.sleep(2)
        
        # Common DOREMiDi mappings to test:
        # 1. Direct: MIDI CC 1 → DMX Ch 1, value 120
        test_mapping(ser, 1, 120, duration=8)
        
        # 2. Scaled: MIDI CC 1 → DMX Ch 1, value 240 (120*2)
        test_mapping(ser, 1, 240, duration=8)
        
        # 3. Maybe DOREMiDi uses DMX channel = MIDI CC number?
        #    MIDI CC 1 → DMX Channel 1, but maybe it's different
        #    Some converters: MIDI CC 1 → DMX Channel 2
        
        # 4. Test DMX Channel 2 with value 120
        test_mapping(ser, 2, 120, duration=8)
        
        # 5. Test DMX Channel 2 with value 240
        test_mapping(ser, 2, 240, duration=8)
        
        # 6. Some DOREMiDi models map MIDI CC to DMX address blocks
        #    MIDI CC 1 might map to DMX Channel 1-8 range
        #    Let's test a few in that range
        print(f"\n{'='*60}")
        print("Testing DMX Channels 1-8 with value 120")
        print(f"{'='*60}")
        for ch in range(1, 9):
            print(f"\nChannel {ch} = 120...", end='', flush=True)
            dmx = bytearray([0] * 512)
            dmx[ch - 1] = 120
            packet = create_packet(dmx)
            start_time = time.time()
            while time.time() - start_time < 3:
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
        for _ in range(10):
            ser.write(packet_off)
            ser.flush()
            time.sleep(0.05)
        
        ser.close()
        
        print("\n" + "="*60)
        print("RESULTS")
        print("="*60)
        print("\nDid ANY of these produce smoke?")
        print("\nAlso, can you check:")
        print("  1. What model is the smoke machine?")
        print("  2. Does it have a manual with DMX channel mapping?")
        print("  3. When MIDI worked, was the smoke machine already warmed up?")
        print("  4. Does the smoke machine need to heat up first before producing smoke?")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
