#!/usr/bin/env python3
"""
Compare what we're sending via DMX vs what DOREMiDi might send
Since MIDI CC 1, value 120, Channel 1 worked, let's figure out the mapping
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

def send_dmx_test(ser, dmx_data, duration=8):
    """Send DMX data continuously"""
    packet = create_packet(dmx_data)
    start_time = time.time()
    packet_count = 0
    
    while time.time() - start_time < duration:
        ser.write(packet)
        ser.flush()
        packet_count += 1
        if packet_count % 20 == 0:
            elapsed = time.time() - start_time
            print(f"  {elapsed:.1f}s - {packet_count} packets...", end='\r')
        time.sleep(0.05)
    
    print(f"\n  ✓ Sent {packet_count} packets")
    return packet_count

def main():
    port = '/dev/cu.usbserial-A10KRSG3'
    
    print("="*70)
    print("DOREMiDi MAPPING INVESTIGATION")
    print("="*70)
    print("\nDOREMiDi MTD-10-ABCD converts:")
    print("  MIDI CC 1, value 120, Channel 1 → DMX ???")
    print("\nCommon DOREMiDi mappings:")
    print("  - MIDI Channel 1 → DMX Address Block (channels 1-8 or 1-16)")
    print("  - MIDI CC 1 → DMX Channel 1 (or Channel 2, or CC number)")
    print("  - MIDI CC value 120 → DMX value 120 (or scaled)")
    print("\nLet's test different possibilities...")
    
    try:
        ser = serial.Serial(port, 57600, timeout=2, write_timeout=2)
        time.sleep(0.3)
        print(f"\n✓ Connected to {port}\n")
        print("Starting in 2 seconds...\n")
        time.sleep(2)
        
        # Theory 1: DOREMiDi might map MIDI CC 1 to DMX Channel 2
        # (Some converters use CC number + 1, or start from channel 2)
        print("="*70)
        print("THEORY 1: MIDI CC 1 → DMX Channel 2, value 120")
        print("="*70)
        dmx = bytearray([0] * 512)
        dmx[1] = 120  # Channel 2
        send_dmx_test(ser, dmx, duration=8)
        print("  Did this work?\n")
        time.sleep(2)
        
        # Theory 2: DOREMiDi might send value 120 to multiple channels
        # Some converters send to both intensity and fan channels
        print("="*70)
        print("THEORY 2: MIDI CC 1 → DMX Channel 1=120, Channel 2=120")
        print("="*70)
        dmx = bytearray([0] * 512)
        dmx[0] = 120  # Channel 1
        dmx[1] = 120  # Channel 2
        send_dmx_test(ser, dmx, duration=8)
        print("  Did this work?\n")
        time.sleep(2)
        
        # Theory 3: DOREMiDi might scale MIDI value 120 to DMX 240
        # (Some converters double the MIDI value)
        print("="*70)
        print("THEORY 3: MIDI CC 1 → DMX Channel 1, value 240 (120*2)")
        print("="*70)
        dmx = bytearray([0] * 512)
        dmx[0] = 240  # Scaled value
        send_dmx_test(ser, dmx, duration=8)
        print("  Did this work?\n")
        time.sleep(2)
        
        # Theory 4: DOREMiDi might use DMX Channel = MIDI CC number
        # So MIDI CC 1 → DMX Channel 1, but maybe it's in a different address block
        # If smoke machine is at DMX address 10, MIDI CC 1 might map to DMX Channel 10
        print("="*70)
        print("THEORY 4: MIDI CC 1 → DMX Channel 10 (if smoke machine at address 10)")
        print("="*70)
        dmx = bytearray([0] * 512)
        dmx[9] = 120  # Channel 10
        send_dmx_test(ser, dmx, duration=8)
        print("  Did this work?\n")
        time.sleep(2)
        
        # Theory 5: DOREMiDi might send to DMX Channel 1 but with a threshold
        # Maybe it needs value >= 100 or >= 127 to activate
        print("="*70)
        print("THEORY 5: DMX Channel 1, value 120, but needs Channel 2 = 255 (fan)")
        print("="*70)
        dmx = bytearray([0] * 512)
        dmx[0] = 120  # Intensity
        dmx[1] = 255  # Fan (max)
        send_dmx_test(ser, dmx, duration=8)
        print("  Did this work?\n")
        time.sleep(2)
        
        # Turn off
        print("="*70)
        print("TURNING OFF")
        print("="*70)
        dmx_off = bytearray([0] * 512)
        packet_off = create_packet(dmx_off)
        for _ in range(10):
            ser.write(packet_off)
            ser.flush()
            time.sleep(0.05)
        
        ser.close()
        
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print("\nWhich theory (if any) produced smoke?")
        print("\nAlso, can you:")
        print("  1. Check the DOREMiDi manual/instructions for channel mapping?")
        print("  2. Try connecting DOREMiDi again and see if it still works?")
        print("  3. Check if DOREMiDi has any DIP switches or configuration?")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
