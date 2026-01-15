#!/usr/bin/env python3
"""
DMX Cable/Adapter Diagnostic Test
Tests if the signal is actually reaching the smoke machine
"""

import serial
import time
import glob

print("="*60)
print("DMX Cable/Adapter Diagnostic")
print("="*60)

# Find device
ports = glob.glob('/dev/cu.usbserial*')
if not ports:
    print("No DMX device found!")
    exit(1)

port = ports[0]
print(f"Using: {port}")

print("\n" + "="*60)
print("CHECKLIST:")
print("="*60)
print("1. Cable Connections:")
print("   - DMX device 5-pin OUT → Adapter → Smoke machine 3-pin INPUT")
print("   - Make sure it's INPUT (not OUTPUT) on smoke machine")
print("   - Check that adapter cable is properly connected")
print("\n2. Adapter Cable Wiring:")
print("   5-pin DMX → 3-pin DMX:")
print("   - Pin 1 (GND) → Pin 1 (GND)")
print("   - Pin 2 (Data-) → Pin 2 (Data-)")
print("   - Pin 3 (Data+) → Pin 3 (Data+)")
print("   - Pins 4 & 5 on 5-pin are unused")
print("\n3. Smoke Machine:")
print("   - Is there a 'DMX' mode button or switch?")
print("   - Does the remote have a 'DMX' mode?")
print("   - Check for DMX indicator LED")
print("   - All DIP switches OFF = address 1")
print("="*60)

input("\nPress Enter to start test...")

try:
    ser = serial.Serial(port, 250000, timeout=0.1)
    print("\n✓ Port opened")
    
    print("\nSending test pattern:")
    print("- Channel 1 = 255 (full intensity)")
    print("- 10 seconds duration")
    print("- Watch smoke machine for ANY response\n")
    
    start = time.time()
    count = 0
    
    while time.time() - start < 10:
        # Break signal
        if hasattr(ser, 'break_condition'):
            ser.break_condition = True
            time.sleep(0.0001)
            ser.break_condition = False
            time.sleep(0.00001)
        
        # Start code
        ser.write(bytes([0]))
        
        # Channel 1 = 255
        dmx = [0] * 512
        dmx[0] = 255
        ser.write(bytes(dmx))
        ser.flush()
        
        count += 1
        if count % 20 == 0:
            print(f"  Packet {count}...", end='\r')
        
        time.sleep(0.05)
    
    # Stop
    if hasattr(ser, 'break_condition'):
        ser.break_condition = True
        time.sleep(0.0001)
        ser.break_condition = False
        time.sleep(0.00001)
    
    ser.write(bytes([0]))
    ser.write(bytes([0] * 512))
    ser.flush()
    ser.close()
    
    print(f"\n✓ Sent {count} packets")
    
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    print("Did the smoke machine:")
    print("  - Show any indicator lights?")
    print("  - Make any sound?")
    print("  - Start heating up?")
    print("  - Produce any smoke?")
    print("="*60)
    
    print("\nIf NO response at all:")
    print("1. Check adapter cable wiring (use multimeter if possible)")
    print("2. Try connecting directly without adapter (if you have 5-pin cable)")
    print("3. Check smoke machine manual for DMX mode activation")
    print("4. Try different DMX address (switch 1 ON = address 1)")
    print("5. Some machines need channel 1 + channel 2 (intensity + fan)")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
