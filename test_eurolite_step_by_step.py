#!/usr/bin/env python3
"""
Step-by-step test for Eurolite USB DMX512 Pro MK2
Let's test each step methodically
"""

import serial
import time
import glob
import sys
import termios
import fcntl

def find_eurolite_device():
    """Find the Eurolite device"""
    ports = glob.glob('/dev/cu.usbserial*') + glob.glob('/dev/tty.usbserial*')
    print("="*60)
    print("STEP 1: Finding DMX Device")
    print("="*60)
    
    if not ports:
        print("❌ No USB serial devices found!")
        return None
    
    print("Found USB serial devices:")
    for port in ports:
        print(f"  ✓ {port}")
    
    # Use first one (should be Eurolite)
    device = ports[0]
    print(f"\nUsing: {device}")
    return device

def test_connection(port):
    """Test basic serial connection"""
    print("\n" + "="*60)
    print("STEP 2: Testing Serial Connection")
    print("="*60)
    
    baud_rates = [250000, 115200, 38400, 9600]
    
    for baud in baud_rates:
        print(f"\nTrying baud rate: {baud}...")
        try:
            ser = serial.Serial(port, baud, timeout=1, write_timeout=1)
            print(f"  ✓ Opened successfully at {baud} baud")
            time.sleep(0.1)
            
            # Try to read any data (some devices send status)
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                print(f"  ✓ Device sent data: {data.hex()}")
            
            ser.close()
            return baud
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            try:
                ser.close()
            except:
                pass
    
    return None

def send_dmx_break_mark_after(ser):
    """Send DMX break and mark-after-break signal"""
    # Break: set line low for 88 microseconds (minimum)
    # Mark-after-break: set line high for 8 microseconds (minimum)
    
    # Method 1: Using termios (Linux/Mac)
    try:
        fd = ser.fileno()
        
        # Get current settings
        attrs = termios.tcgetattr(fd)
        
        # Set break condition
        termios.tcsendbreak(fd, 0)  # 0 = default break duration
        
        # Small delay
        time.sleep(0.0001)  # 100 microseconds
        
        return True
    except Exception as e:
        print(f"  Note: termios break failed: {e}")
    
    # Method 2: Using serial break_condition (if available)
    try:
        if hasattr(ser, 'break_condition'):
            ser.break_condition = True
            time.sleep(0.0001)  # 100 microseconds
            ser.break_condition = False
            time.sleep(0.00001)  # 10 microseconds (mark-after-break)
            return True
    except Exception as e:
        print(f"  Note: break_condition failed: {e}")
    
    # Method 3: Manual break using baud rate manipulation
    # (Not always reliable, but worth trying)
    try:
        # Temporarily change baud to create break
        original_baud = ser.baudrate
        ser.baudrate = 100  # Very slow = break signal
        time.sleep(0.0001)
        ser.baudrate = original_baud
        time.sleep(0.00001)
        return True
    except Exception as e:
        print(f"  Note: baud manipulation failed: {e}")
    
    return False

def test_dmx_protocol(port, baud_rate):
    """Test DMX protocol step by step"""
    print("\n" + "="*60)
    print("STEP 3: Testing DMX Protocol")
    print("="*60)
    
    print(f"\nProtocol details:")
    print(f"  - Break: 88+ microseconds (low)")
    print(f"  - Mark-after-break: 8+ microseconds (high)")
    print(f"  - Start code: 0x00")
    print(f"  - Data: 512 channels (0-255 each)")
    print(f"  - Refresh rate: ~20-40 packets/second")
    
    try:
        ser = serial.Serial(port, baud_rate, timeout=0.1, write_timeout=0.1)
        print(f"\n✓ Serial port opened at {baud_rate} baud")
        
        # Test 1: Send break signal
        print("\nTest 1: Sending break signal...")
        break_sent = send_dmx_break_mark_after(ser)
        if break_sent:
            print("  ✓ Break signal sent")
        else:
            print("  ⚠ Break signal method not available (may still work)")
        
        # Test 2: Send start code
        print("\nTest 2: Sending start code (0x00)...")
        ser.write(bytes([0x00]))
        ser.flush()
        print("  ✓ Start code sent")
        
        # Test 3: Send single channel
        print("\nTest 3: Sending channel 1 = 255...")
        dmx_data = [0] * 512
        dmx_data[0] = 255  # Channel 1 = full intensity
        ser.write(bytes(dmx_data))
        ser.flush()
        print("  ✓ DMX data sent (512 channels)")
        
        # Test 4: Send continuous updates
        print("\nTest 4: Sending continuous updates (5 seconds)...")
        print("  Watch the smoke machine - it should respond!")
        
        start_time = time.time()
        packet_count = 0
        
        while time.time() - start_time < 5:
            # Break
            send_dmx_break_mark_after(ser)
            
            # Start code
            ser.write(bytes([0x00]))
            
            # Data
            ser.write(bytes(dmx_data))
            ser.flush()
            
            packet_count += 1
            
            if packet_count % 20 == 0:
                print(f"  Sent {packet_count} packets...", end='\r')
            
            time.sleep(0.05)  # ~20 packets/second
        
        print(f"\n  ✓ Sent {packet_count} packets")
        
        # Test 5: Turn off
        print("\nTest 5: Turning off (channel 1 = 0)...")
        dmx_data[0] = 0
        for _ in range(10):  # Send a few packets to ensure it's off
            send_dmx_break_mark_after(ser)
            ser.write(bytes([0x00]))
            ser.write(bytes(dmx_data))
            ser.flush()
            time.sleep(0.05)
        print("  ✓ Turned off")
        
        ser.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            ser.close()
        except:
            pass
        return False

def main():
    print("="*60)
    print("Eurolite USB DMX512 Pro MK2 - Step by Step Test")
    print("="*60)
    
    # Step 1: Find device
    device = find_eurolite_device()
    if not device:
        print("\n❌ No device found. Make sure:")
        print("  - Eurolite device is connected via USB")
        print("  - USB cable is working")
        print("  - Device is powered (if it needs external power)")
        sys.exit(1)
    
    # Step 2: Test connection
    baud_rate = test_connection(device)
    if not baud_rate:
        print("\n❌ Could not establish serial connection")
        print("Try:")
        print("  - Unplugging and replugging the device")
        print("  - Checking if another program is using the port")
        sys.exit(1)
    
    print(f"\n✓ Best baud rate: {baud_rate}")
    
    # Step 3: Test DMX protocol
    print("\n" + "="*60)
    print("PREPARATION CHECKLIST")
    print("="*60)
    print("Before testing, make sure:")
    print("  ✓ Smoke machine is powered ON")
    print("  ✓ Smoke machine is set to DMX mode")
    print("  ✓ Smoke machine DMX address is set to 1")
    print("    (All DIP switches OFF = address 1)")
    print("  ✓ Cable: Eurolite OUT → Adapter → Smoke machine IN")
    print("  ✓ DMX cable is properly connected")
    
    response = input("\nReady to test? (y/n): ")
    if response.lower() != 'y':
        print("Test cancelled.")
        sys.exit(0)
    
    success = test_dmx_protocol(device, baud_rate)
    
    print("\n" + "="*60)
    if success:
        print("✅ TEST COMPLETED")
        print("="*60)
        print("\nDid the smoke machine respond?")
        print("  - If YES: Great! DMX is working.")
        print("  - If NO: Check:")
        print("    • Smoke machine DMX address (should be 1)")
        print("    • Cable connections")
        print("    • Smoke machine DMX mode enabled")
    else:
        print("❌ TEST FAILED")
        print("="*60)
        print("\nTroubleshooting:")
        print("  • Check device connection")
        print("  • Try different baud rate")
        print("  • Check if device needs drivers")

if __name__ == '__main__':
    main()
