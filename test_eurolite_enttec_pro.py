#!/usr/bin/env python3
"""
Test Eurolite DMX512 Pro MK2 using Enttec Pro protocol
Some Eurolite devices are compatible with Enttec Pro protocol
"""

import serial
import time
import struct

# Enttec Pro protocol constants
ENTTEC_PRO_START_OF_MSG = 0x7E
ENTTEC_PRO_END_OF_MSG = 0xE7
ENTTEC_PRO_SEND_DMX_RQ = 0x06  # Request to send DMX
ENTTEC_PRO_RECV_DMX = 0x05
ENTTEC_PRO_GET_WIDGET_PARAMS = 0x03
ENTTEC_PRO_SET_WIDGET_PARAMS = 0x04

def create_enttec_pro_dmx_packet(dmx_data):
    """Create an Enttec Pro DMX packet"""
    # Packet structure:
    # START (0x7E) | LABEL (0x06) | LSB | MSB | DATA | END (0xE7)
    
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

def get_widget_params(ser):
    """Get widget parameters (Enttec Pro command)"""
    packet = bytearray()
    packet.append(ENTTEC_PRO_START_OF_MSG)
    packet.append(ENTTEC_PRO_GET_WIDGET_PARAMS)
    packet.append(0x00)  # LSB
    packet.append(0x00)  # MSB
    packet.append(ENTTEC_PRO_END_OF_MSG)
    
    ser.write(bytes(packet))
    ser.flush()
    time.sleep(0.1)
    
    # Try to read response
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting)
        print(f"  Widget response: {response.hex()}")
        return response
    return None

def test_enttec_pro_protocol(port='/dev/cu.usbserial-A10KRSG3', channel=1, value=255, duration=5):
    """Test using Enttec Pro protocol"""
    print("="*60)
    print("Eurolite DMX512 Pro MK2 - Enttec Pro Protocol Test")
    print("="*60)
    print(f"Port: {port}")
    print(f"Channel: {channel}")
    print(f"Value: {value}")
    print(f"Duration: {duration}s")
    print("="*60)
    
    # Try different baud rates (Enttec Pro typically uses 57600 or 115200)
    baud_rates = [57600, 115200, 38400, 9600]
    
    for baud in baud_rates:
        print(f"\nTrying baud rate: {baud}")
        try:
            ser = serial.Serial(port, baud, timeout=0.1, write_timeout=0.1)
            print(f"  ✓ Opened at {baud} baud")
            
            # Small delay for device initialization
            time.sleep(0.2)
            
            # Test 1: Get widget parameters (identifies device)
            print("\n  Test 1: Getting widget parameters...")
            response = get_widget_params(ser)
            if response:
                print(f"  ✓ Device responded: {len(response)} bytes")
            else:
                print("  ⚠ No response (may still work)")
            
            # Test 2: Send DMX data using Enttec Pro protocol
            print(f"\n  Test 2: Sending DMX data (Channel {channel} = {value})...")
            
            # Create DMX data (512 channels)
            dmx_data = bytearray([0] * 512)
            dmx_data[channel - 1] = value
            
            # Create Enttec Pro packet
            packet = create_enttec_pro_dmx_packet(dmx_data)
            
            print(f"  Packet structure: START | LABEL | LSB | MSB | DATA({len(dmx_data)} bytes) | END")
            print(f"  Packet hex: {packet[:10].hex()}...{packet[-5:].hex()}")
            
            # Send packets continuously
            start_time = time.time()
            packet_count = 0
            
            print(f"\n  Sending packets for {duration} seconds...")
            print("  Watch the smoke machine!")
            
            while time.time() - start_time < duration:
                ser.write(packet)
                ser.flush()
                
                packet_count += 1
                
                if packet_count % 20 == 0:
                    print(f"    Sent {packet_count} packets...", end='\r')
                
                time.sleep(0.05)  # ~20 packets/second
            
            print(f"\n  ✓ Sent {packet_count} packets")
            
            # Test 3: Turn off
            print("\n  Test 3: Turning off...")
            dmx_data[channel - 1] = 0
            packet_off = create_enttec_pro_dmx_packet(bytes(dmx_data))
            
            for _ in range(10):
                ser.write(packet_off)
                ser.flush()
                time.sleep(0.05)
            
            ser.close()
            print(f"\n✓ Success at {baud} baud!")
            print("\nDid the smoke machine respond?")
            return True
            
        except Exception as e:
            print(f"  ✗ Failed at {baud} baud: {e}")
            try:
                ser.close()
            except:
                pass
            continue
    
    print("\n✗ All baud rates failed")
    return False

if __name__ == '__main__':
    import sys
    
    channel = 1
    duration = 5
    
    if len(sys.argv) > 1:
        try:
            channel = int(sys.argv[1])
        except:
            pass
    
    if len(sys.argv) > 2:
        try:
            duration = int(sys.argv[2])
        except:
            pass
    
    print("\nMake sure:")
    print(f"  • Smoke machine DMX address = {channel}")
    print(f"  • All DIP switches OFF = address 1")
    print(f"  • Smoke machine is powered ON")
    print(f"  • Cable: Eurolite OUT → Adapter → Smoke machine IN")
    print("\nStarting test in 2 seconds...\n")
    time.sleep(2)
    
    test_enttec_pro_protocol(channel=channel, value=255, duration=duration)
