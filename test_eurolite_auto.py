#!/usr/bin/env python3
"""
Automated test for Eurolite USB DMX512 Pro MK2
Runs without user interaction
"""

import serial
import time
import glob
import sys
import termios

def send_dmx_break(ser):
    """Send DMX break signal"""
    try:
        fd = ser.fileno()
        termios.tcsendbreak(fd, 0)
        time.sleep(0.0001)  # 100 microseconds
        return True
    except:
        try:
            if hasattr(ser, 'break_condition'):
                ser.break_condition = True
                time.sleep(0.0001)
                ser.break_condition = False
                time.sleep(0.00001)
                return True
        except:
            pass
    return False

def test_eurolite_dmx(port='/dev/cu.usbserial-A10KRSG3', channel=1, value=255, duration=5):
    """Test Eurolite DMX device"""
    print("="*60)
    print("Eurolite USB DMX512 Pro MK2 Test")
    print("="*60)
    print(f"Port: {port}")
    print(f"Channel: {channel}")
    print(f"Value: {value}")
    print(f"Duration: {duration}s")
    print("="*60)
    
    try:
        ser = serial.Serial(port, 250000, timeout=0.1, write_timeout=0.1)
        print("✓ Serial port opened at 250000 baud")
        
        # Prepare DMX data
        dmx_data = [0] * 512
        dmx_data[channel - 1] = value
        
        print(f"\nSending DMX packets for {duration} seconds...")
        print("Watch the smoke machine - it should respond!")
        
        start_time = time.time()
        packet_count = 0
        
        while time.time() - start_time < duration:
            # Break signal
            send_dmx_break(ser)
            
            # Start code
            ser.write(bytes([0x00]))
            
            # DMX data (512 channels)
            ser.write(bytes(dmx_data))
            ser.flush()
            
            packet_count += 1
            
            if packet_count % 20 == 0:
                print(f"  Sent {packet_count} packets...", end='\r')
            
            time.sleep(0.05)  # ~20 packets/second
        
        print(f"\n✓ Sent {packet_count} packets")
        
        # Turn off
        print("\nTurning off...")
        dmx_data[channel - 1] = 0
        for _ in range(10):
            send_dmx_break(ser)
            ser.write(bytes([0x00]))
            ser.write(bytes(dmx_data))
            ser.flush()
            time.sleep(0.05)
        
        ser.close()
        print("✓ Test completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    port = '/dev/cu.usbserial-A10KRSG3'
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
    
    test_eurolite_dmx(port, channel, 255, duration)
    
    print("\n" + "="*60)
    print("Did the smoke machine respond?")
    print("="*60)
