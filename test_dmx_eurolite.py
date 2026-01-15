#!/usr/bin/env python3
"""
Test DMX with Eurolite USB DMX 512 Pro
This device may use a different protocol than Enttec
"""

import serial
import time
import glob
import sys

def find_dmx_devices():
    """Find available DMX devices"""
    devices = []
    
    # Check for Eurolite (often shows as different USB ID)
    eurolite_ports = glob.glob('/dev/cu.usbserial*') + glob.glob('/dev/tty.usbserial*')
    
    # Also check for other common USB serial ports
    all_ports = glob.glob('/dev/cu.*') + glob.glob('/dev/tty.*')
    
    print("Available USB serial devices:")
    for port in eurolite_ports:
        print(f"  - {port}")
    
    return eurolite_ports

def test_eurolite_dmx(port, channel=1, value=255, duration=10):
    """Test Eurolite USB DMX 512 Pro
    
    Eurolite devices may use:
    - Different baud rate (115200 or 250000)
    - Different protocol
    - May need specific initialization
    """
    print("="*60)
    print("Eurolite USB DMX 512 Pro Test")
    print("="*60)
    print(f"Port: {port}")
    print(f"Channel: {channel}")
    print(f"Value: {value}")
    print(f"Duration: {duration}s")
    print("="*60)
    
    # Try different baud rates
    baud_rates = [250000, 115200, 38400]
    
    for baud in baud_rates:
        print(f"\nTrying baud rate: {baud}")
        try:
            ser = serial.Serial(port, baud, timeout=0.1, write_timeout=0.1)
            print(f"✓ Opened at {baud} baud")
            
            # Some Eurolite devices need initialization
            # Try sending a reset or initialization sequence
            time.sleep(0.1)
            
            start = time.time()
            count = 0
            
            print("Sending DMX packets...")
            while time.time() - start < duration:
                # Break signal
                try:
                    if hasattr(ser, 'break_condition'):
                        ser.break_condition = True
                        time.sleep(0.0001)  # 100 microseconds
                        ser.break_condition = False
                        time.sleep(0.00001)  # 10 microseconds
                except:
                    pass
                
                # Start code
                ser.write(bytes([0]))
                
                # DMX data
                dmx = [0] * 512
                dmx[channel - 1] = value
                ser.write(bytes(dmx))
                ser.flush()
                
                count += 1
                if count % 20 == 0:
                    print(f"  Sent {count} packets...", end='\r')
                
                time.sleep(0.05)  # 20 packets/sec
            
            # Stop
            try:
                if hasattr(ser, 'break_condition'):
                    ser.break_condition = True
                    time.sleep(0.0001)
                    ser.break_condition = False
                    time.sleep(0.00001)
            except:
                pass
            
            ser.write(bytes([0]))
            ser.write(bytes([0] * 512))
            ser.flush()
            
            ser.close()
            print(f"\n✓ Success at {baud} baud! Sent {count} packets.")
            print("\nDid the smoke machine respond?")
            return True
            
        except Exception as e:
            print(f"✗ Failed at {baud} baud: {e}")
            try:
                ser.close()
            except:
                pass
            continue
    
    print("\n✗ All baud rates failed")
    return False

if __name__ == '__main__':
    print("Looking for DMX devices...\n")
    ports = find_dmx_devices()
    
    if not ports:
        print("No USB serial devices found!")
        print("Make sure the Eurolite device is connected.")
        sys.exit(1)
    
    # Use first port found, or let user choose
    if len(ports) > 1:
        print(f"\nMultiple devices found. Using: {ports[0]}")
        print("(If wrong, edit the script to use a different port)")
    
    port = ports[0]
    
    channel = 1
    if len(sys.argv) > 1:
        try:
            channel = int(sys.argv[1])
        except:
            pass
    
    duration = 10
    if len(sys.argv) > 2:
        try:
            duration = int(sys.argv[2])
        except:
            pass
    
    print(f"\nMake sure:")
    print(f"- Smoke machine is set to DMX address {channel}")
    print(f"- All DIP switches OFF = address 1")
    print(f"- Smoke machine is powered ON")
    print(f"- Cable connected: Eurolite OUT → Adapter → Smoke machine IN")
    
    input("\nPress Enter to start test...")
    
    test_eurolite_dmx(port, channel, 255, duration)
