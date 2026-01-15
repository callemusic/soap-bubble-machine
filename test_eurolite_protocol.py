#!/usr/bin/env python3
"""
Test different Eurolite DMX512 Pro MK2 protocols
Some devices need specific initialization sequences
"""

import serial
import time
import glob

def test_protocol_variant(ser, variant_name, break_func, start_code_func):
    """Test a specific protocol variant"""
    print(f"\n--- Testing {variant_name} ---")
    
    try:
        dmx_data = [0] * 512
        dmx_data[0] = 255  # Channel 1 = full
        
        packet_count = 0
        start_time = time.time()
        
        while time.time() - start_time < 3:  # 3 second test
            # Break
            break_func(ser)
            
            # Start code
            start_code_func(ser)
            
            # Data
            ser.write(bytes(dmx_data))
            ser.flush()
            
            packet_count += 1
            time.sleep(0.05)
        
        print(f"  ✓ Sent {packet_count} packets")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    port = '/dev/cu.usbserial-A10KRSG3'
    
    print("="*60)
    print("Eurolite Protocol Variants Test")
    print("="*60)
    
    try:
        ser = serial.Serial(port, 250000, timeout=0.1, write_timeout=0.1)
        print(f"✓ Opened {port} at 250000 baud\n")
        
        # Variant 1: Standard DMX with termios break
        def break1(ser):
            try:
                import termios
                fd = ser.fileno()
                termios.tcsendbreak(fd, 0)
                time.sleep(0.0001)
            except:
                pass
        
        def start1(ser):
            ser.write(bytes([0x00]))
        
        test_protocol_variant(ser, "Standard DMX (termios break)", break1, start1)
        time.sleep(1)
        
        # Variant 2: Break condition
        def break2(ser):
            try:
                if hasattr(ser, 'break_condition'):
                    ser.break_condition = True
                    time.sleep(0.0001)
                    ser.break_condition = False
                    time.sleep(0.00001)
            except:
                pass
        
        test_protocol_variant(ser, "Break condition method", break2, start1)
        time.sleep(1)
        
        # Variant 3: No break, just start code (some devices don't need break)
        def break3(ser):
            pass  # No break
        
        test_protocol_variant(ser, "No break signal", break3, start1)
        time.sleep(1)
        
        # Variant 4: Longer break
        def break4(ser):
            try:
                import termios
                fd = ser.fileno()
                termios.tcsendbreak(fd, 0)
                time.sleep(0.0002)  # Longer break
            except:
                pass
        
        test_protocol_variant(ser, "Longer break (200us)", break4, start1)
        time.sleep(1)
        
        # Variant 5: Higher refresh rate
        def break5(ser):
            try:
                import termios
                fd = ser.fileno()
                termios.tcsendbreak(fd, 0)
                time.sleep(0.0001)
            except:
                pass
        
        print("\n--- Testing Higher Refresh Rate (40 packets/sec) ---")
        dmx_data = [0] * 512
        dmx_data[0] = 255
        packet_count = 0
        start_time = time.time()
        
        while time.time() - start_time < 3:
            break5(ser)
            ser.write(bytes([0x00]))
            ser.write(bytes(dmx_data))
            ser.flush()
            packet_count += 1
            time.sleep(0.025)  # 40 packets/sec
        
        print(f"  ✓ Sent {packet_count} packets at higher rate")
        
        # Turn off
        print("\nTurning off...")
        dmx_data[0] = 0
        for _ in range(10):
            break5(ser)
            ser.write(bytes([0x00]))
            ser.write(bytes(dmx_data))
            ser.flush()
            time.sleep(0.05)
        
        ser.close()
        print("\n✓ All protocol variants tested")
        print("\nDid any variant work?")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
