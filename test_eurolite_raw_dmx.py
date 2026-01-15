#!/usr/bin/env python3
"""
Test RAW DMX512 protocol (not Enttec Pro wrapper)
The DOREMiDi might have been sending raw DMX, not Enttec Pro protocol
"""

import serial
import time
import termios

def send_raw_dmx(ser, dmx_data, duration=5):
    """Send raw DMX512 protocol (break + start code + data)"""
    print(f"\nSending RAW DMX512 protocol...")
    print(f"  Channel 1 = {dmx_data[0]}")
    print(f"  Watch LED and smoke machine!")
    
    start_time = time.time()
    packet_count = 0
    
    while time.time() - start_time < duration:
        try:
            # Break signal (88+ microseconds low)
            fd = ser.fileno()
            termios.tcsendbreak(fd, 0)
            time.sleep(0.0001)  # 100 microseconds
            
            # Mark-after-break (8+ microseconds high)
            time.sleep(0.00001)  # 10 microseconds
            
            # Start code (0x00)
            ser.write(bytes([0x00]))
            
            # DMX data (512 channels)
            ser.write(bytes(dmx_data))
            ser.flush()
            
            packet_count += 1
            if packet_count % 20 == 0:
                print(f"  Sent {packet_count} packets...", end='\r')
            
            time.sleep(0.05)  # ~20 packets/second
            
        except Exception as e:
            print(f"\n  Error: {e}")
            break
    
    print(f"\n  ✓ Sent {packet_count} packets")
    return packet_count

def main():
    port = '/dev/cu.usbserial-A10KRSG3'
    
    print("="*60)
    print("TESTING RAW DMX512 PROTOCOL")
    print("="*60)
    print("\nThe DOREMiDi converter might send RAW DMX512,")
    print("not Enttec Pro protocol. Let's test both!")
    
    # Try different baud rates for raw DMX
    baud_rates = [250000, 115200, 57600]
    
    for baud in baud_rates:
        print(f"\n{'='*60}")
        print(f"Testing RAW DMX512 at {baud} baud")
        print(f"{'='*60}")
        
        try:
            ser = serial.Serial(port, baud, timeout=1, write_timeout=1)
            time.sleep(0.2)
            print(f"✓ Opened at {baud} baud")
            
            # Test value 120 (what worked with MIDI)
            print("\nTest 1: Channel 1 = 120 (5 seconds)")
            dmx = bytearray([0] * 512)
            dmx[0] = 120
            send_raw_dmx(ser, dmx, duration=5)
            time.sleep(2)
            
            # Test value 255
            print("\nTest 2: Channel 1 = 255 (5 seconds)")
            dmx[0] = 255
            send_raw_dmx(ser, dmx, duration=5)
            time.sleep(2)
            
            # Test Channel 2 = 120 (maybe it's channel 2?)
            print("\nTest 3: Channel 2 = 120 (5 seconds)")
            dmx = bytearray([0] * 512)
            dmx[1] = 120  # Channel 2
            send_raw_dmx(ser, dmx, duration=5)
            time.sleep(2)
            
            # Turn off
            print("\nTurning off...")
            dmx = bytearray([0] * 512)
            for _ in range(10):
                try:
                    termios.tcsendbreak(ser.fileno(), 0)
                    time.sleep(0.0001)
                    ser.write(bytes([0x00]))
                    ser.write(bytes(dmx))
                    ser.flush()
                    time.sleep(0.05)
                except:
                    pass
            
            ser.close()
            print(f"\n✓ Completed test at {baud} baud")
            print("\nDid any test produce smoke?")
            break  # If we got here, the baud rate works
            
        except Exception as e:
            print(f"✗ Failed at {baud} baud: {e}")
            try:
                ser.close()
            except:
                pass
            continue
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print("\nDid RAW DMX512 work better than Enttec Pro protocol?")

if __name__ == '__main__':
    main()
