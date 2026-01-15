#!/usr/bin/env python3
"""
Test Enttec Pro protocol at all common baud rates
"""

import serial
import time

# Enttec Pro protocol constants
ENTTEC_PRO_START_OF_MSG = 0x7E
ENTTEC_PRO_SEND_DMX_RQ = 0x06
ENTTEC_PRO_END_OF_MSG = 0xE7

def create_enttec_pro_dmx_packet(dmx_data):
    """Create an Enttec Pro DMX packet"""
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

def test_baud_rate(port, baud, channel=1, value=255, duration=3):
    """Test a specific baud rate"""
    try:
        ser = serial.Serial(port, baud, timeout=0.1, write_timeout=0.1)
        time.sleep(0.2)
        
        # Create DMX data
        dmx_data = bytearray([0] * 512)
        dmx_data[channel - 1] = value
        
        # Create packet
        packet = create_enttec_pro_dmx_packet(dmx_data)
        
        # Send packets
        start_time = time.time()
        packet_count = 0
        
        while time.time() - start_time < duration:
            ser.write(packet)
            ser.flush()
            packet_count += 1
            time.sleep(0.05)
        
        # Turn off
        dmx_data[channel - 1] = 0
        packet_off = create_enttec_pro_dmx_packet(bytes(dmx_data))
        for _ in range(5):
            ser.write(packet_off)
            ser.flush()
            time.sleep(0.05)
        
        ser.close()
        return True, packet_count
        
    except Exception as e:
        try:
            ser.close()
        except:
            pass
        return False, str(e)

def main():
    port = '/dev/cu.usbserial-A10KRSG3'
    baud_rates = [57600, 115200, 38400, 9600, 19200, 250000]
    
    print("="*60)
    print("Testing Enttec Pro Protocol at Different Baud Rates")
    print("="*60)
    print(f"Port: {port}\n")
    
    results = []
    
    for baud in baud_rates:
        print(f"Testing {baud} baud...", end=' ')
        success, result = test_baud_rate(port, baud, duration=3)
        
        if success:
            print(f"✓ SUCCESS ({result} packets)")
            results.append((baud, True, result))
        else:
            print(f"✗ FAILED ({result})")
            results.append((baud, False, result))
        
        time.sleep(0.5)
    
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    
    successful = [r for r in results if r[1]]
    if successful:
        print("\n✓ Working baud rates:")
        for baud, _, packets in successful:
            print(f"  • {baud} baud ({packets} packets sent)")
        print(f"\nRecommended: {successful[0][0]} baud")
    else:
        print("\n✗ No working baud rates found")
    
    print("\nDid the smoke machine respond at any baud rate?")

if __name__ == '__main__':
    main()
