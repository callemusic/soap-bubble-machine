#!/usr/bin/env python3
"""
Comprehensive troubleshooting for Eurolite DMX -> Smoke Machine
Tests multiple scenarios to find what works
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

def send_dmx_test(ser, dmx_data, duration=5, description=""):
    """Send DMX data for specified duration"""
    packet = create_enttec_pro_dmx_packet(dmx_data)
    
    print(f"\n  {description}")
    print(f"  Channels: ", end="")
    active_channels = [i+1 for i, v in enumerate(dmx_data[:20]) if v > 0]
    if active_channels:
        print(f"{active_channels} = {[dmx_data[i-1] for i in active_channels]}")
    else:
        print("None (all zeros)")
    
    start_time = time.time()
    packet_count = 0
    
    while time.time() - start_time < duration:
        ser.write(packet)
        ser.flush()
        packet_count += 1
        time.sleep(0.05)
    
    print(f"  ✓ Sent {packet_count} packets")
    return packet_count

def main():
    port = '/dev/cu.usbserial-A10KRSG3'
    
    print("="*70)
    print("SMOKE MACHINE DMX TROUBLESHOOTING")
    print("="*70)
    
    print("\n📋 PRE-TEST CHECKLIST:")
    print("  [ ] Smoke machine is powered ON")
    print("  [ ] Smoke machine is in DMX mode (not remote mode)")
    print("  [ ] DMX cable: Eurolite OUT → Adapter → Smoke machine IN")
    print("  [ ] Adapter cable is properly connected")
    print("  [ ] Smoke machine has fluid/water")
    print("  [ ] Smoke machine is warmed up (if needed)")
    
    input("\nPress Enter when ready to start tests...")
    
    try:
        ser = serial.Serial(port, 57600, timeout=0.1, write_timeout=0.1)
        time.sleep(0.2)
        print("\n✓ Serial port opened\n")
        
        # Test 1: Channel 1 only (standard)
        print("="*70)
        print("TEST 1: Channel 1 = 255 (Standard DMX address 1)")
        print("="*70)
        dmx = bytearray([0] * 512)
        dmx[0] = 255  # Channel 1
        send_dmx_test(ser, dmx, duration=5, description="Channel 1 = 255")
        print("\n  👀 Did smoke machine show ANY sign of life?")
        print("     (LED, sound, heating, smoke, etc.)")
        time.sleep(2)
        
        # Test 2: Channel 1 + Channel 2 (some machines need fan + intensity)
        print("\n" + "="*70)
        print("TEST 2: Channel 1 = 255, Channel 2 = 255 (Intensity + Fan)")
        print("="*70)
        dmx = bytearray([0] * 512)
        dmx[0] = 255  # Channel 1 (intensity)
        dmx[1] = 255  # Channel 2 (fan/speed)
        send_dmx_test(ser, dmx, duration=5, description="Channel 1 = 255, Channel 2 = 255")
        print("\n  👀 Did smoke machine respond?")
        time.sleep(2)
        
        # Test 3: Try DMX address 10 (DIP switches 2+4 ON)
        print("\n" + "="*70)
        print("TEST 3: Channel 10 = 255 (DMX address 10)")
        print("="*70)
        print("  If smoke machine DIP switches are: 2=ON, 4=ON")
        print("  Then DMX address = 10, so we use channel 10")
        dmx = bytearray([0] * 512)
        dmx[9] = 255  # Channel 10 (address 10)
        send_dmx_test(ser, dmx, duration=5, description="Channel 10 = 255")
        print("\n  👀 Did smoke machine respond?")
        time.sleep(2)
        
        # Test 4: Try all channels sequentially (find the right one)
        print("\n" + "="*70)
        print("TEST 4: Scanning channels 1-20 (5 seconds each)")
        print("="*70)
        print("  This will test channels 1-20 one by one")
        print("  Watch for ANY response from smoke machine\n")
        
        for channel in range(1, 21):
            dmx = bytearray([0] * 512)
            dmx[channel - 1] = 255
            print(f"\n  Testing Channel {channel}...", end='')
            send_dmx_test(ser, dmx, duration=3, description=f"Channel {channel} = 255")
            time.sleep(1)
        
        # Test 5: Try different intensity values
        print("\n" + "="*70)
        print("TEST 5: Different intensity values on Channel 1")
        print("="*70)
        intensities = [127, 200, 255]
        for intensity in intensities:
            dmx = bytearray([0] * 512)
            dmx[0] = intensity
            send_dmx_test(ser, dmx, duration=3, description=f"Channel 1 = {intensity}")
            time.sleep(1)
        
        # Test 6: Continuous high refresh rate
        print("\n" + "="*70)
        print("TEST 6: High refresh rate (40 packets/sec)")
        print("="*70)
        dmx = bytearray([0] * 512)
        dmx[0] = 255
        packet = create_enttec_pro_dmx_packet(dmx)
        print("  Sending at 40 packets/sec for 5 seconds...")
        start_time = time.time()
        packet_count = 0
        while time.time() - start_time < 5:
            ser.write(packet)
            ser.flush()
            packet_count += 1
            time.sleep(0.025)  # 40 packets/sec
        print(f"  ✓ Sent {packet_count} packets")
        
        # Turn off
        print("\n" + "="*70)
        print("Turning off all channels...")
        print("="*70)
        dmx = bytearray([0] * 512)
        packet_off = create_enttec_pro_dmx_packet(dmx)
        for _ in range(10):
            ser.write(packet_off)
            ser.flush()
            time.sleep(0.05)
        
        ser.close()
        
        print("\n" + "="*70)
        print("TROUBLESHOOTING QUESTIONS")
        print("="*70)
        print("\n1. Did the smoke machine show ANY response during ANY test?")
        print("   - LED indicator?")
        print("   - Sound/beep?")
        print("   - Heating up?")
        print("   - Fan spinning?")
        print("   - Smoke output?")
        
        print("\n2. What are the DIP switch settings on the smoke machine?")
        print("   - All OFF = address 1")
        print("   - Switch 1 ON = address 2")
        print("   - Switch 2 ON = address 3")
        print("   - Switches 2+4 ON = address 10")
        
        print("\n3. Does the smoke machine have a DMX mode button/switch?")
        print("   - Some machines need to be switched to DMX mode")
        print("   - Check for a mode selector switch")
        
        print("\n4. What model is the smoke machine?")
        print("   - Check the manual for DMX channel mapping")
        print("   - Some machines use different channel assignments")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
