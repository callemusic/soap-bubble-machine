#!/usr/bin/env python3
"""
Test MIDI messages specifically for smoke machine control via DOREMiDi MTD-10
"""

import mido
import time
import sys

def find_midi_port(search_term="DOREMiDi"):
    """Find MIDI port containing search term"""
    ports = mido.get_output_names()
    for port in ports:
        if search_term.lower() in port.lower():
            return port
    return ports[0] if ports else None

def send_smoke_test(port_name, channel=0, cc_number=1, intensity=127, duration=3.0):
    """
    Send MIDI CC to trigger smoke machine
    
    Args:
        port_name: MIDI output port
        channel: MIDI channel (0-15)
        cc_number: Control Change number (often 1 for intensity)
        intensity: Intensity value (0-127)
        duration: How long to hold the intensity
    """
    try:
        with mido.open_output(port_name) as port:
            print(f"\n{'='*60}")
            print(f"SMOKE TEST")
            print(f"{'='*60}")
            print(f"Port: {port_name}")
            print(f"Channel: {channel}")
            print(f"CC Number: {cc_number}")
            print(f"Intensity: {intensity}/127")
            print(f"Duration: {duration}s")
            print(f"{'='*60}\n")
            
            # Send full intensity
            print(f"→ Sending CC {cc_number} = {intensity} (ON)")
            port.send(mido.Message('control_change', channel=channel, control=cc_number, value=intensity))
            
            # Hold for duration
            print(f"→ Holding for {duration} seconds...")
            time.sleep(duration)
            
            # Turn off
            print(f"→ Sending CC {cc_number} = 0 (OFF)")
            port.send(mido.Message('control_change', channel=channel, control=cc_number, value=0))
            
            print("\n✅ Test completed!")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_multiple_ccs(port_name, channel=0, cc_numbers=[1, 2, 3, 4, 5], intensity=127):
    """Test multiple CC numbers to find which one controls smoke"""
    print(f"\n{'='*60}")
    print(f"TESTING MULTIPLE CC NUMBERS")
    print(f"{'='*60}")
    print(f"Port: {port_name}")
    print(f"Channel: {channel}")
    print(f"CC Numbers to test: {cc_numbers}")
    print(f"{'='*60}\n")
    
    try:
        with mido.open_output(port_name) as port:
            for cc in cc_numbers:
                print(f"\nTesting CC {cc}...")
                print(f"  → ON (value={intensity})")
                port.send(mido.Message('control_change', channel=channel, control=cc, value=intensity))
                time.sleep(2)
                print(f"  → OFF (value=0)")
                port.send(mido.Message('control_change', channel=channel, control=cc, value=0))
                time.sleep(1)
                
                response = input(f"  Did smoke machine respond to CC {cc}? (y/n/q to quit): ")
                if response.lower() == 'q':
                    break
                if response.lower() == 'y':
                    print(f"\n✅ Found working CC: {cc}")
                    return cc
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return None

def test_multiple_channels(port_name, cc_number=1, intensity=127):
    """Test multiple MIDI channels"""
    print(f"\n{'='*60}")
    print(f"TESTING MULTIPLE MIDI CHANNELS")
    print(f"{'='*60}")
    print(f"Port: {port_name}")
    print(f"CC Number: {cc_number}")
    print(f"{'='*60}\n")
    
    try:
        with mido.open_output(port_name) as port:
            for channel in range(16):
                print(f"\nTesting Channel {channel}...")
                print(f"  → ON (CC {cc_number} = {intensity})")
                port.send(mido.Message('control_change', channel=channel, control=cc_number, value=intensity))
                time.sleep(2)
                print(f"  → OFF (CC {cc_number} = 0)")
                port.send(mido.Message('control_change', channel=channel, control=cc_number, value=0))
                time.sleep(1)
                
                response = input(f"  Did smoke machine respond on channel {channel}? (y/n/q to quit): ")
                if response.lower() == 'q':
                    break
                if response.lower() == 'y':
                    print(f"\n✅ Found working channel: {channel}")
                    return channel
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return None

if __name__ == '__main__':
    print("=" * 60)
    print("MIDI Smoke Machine Test")
    print("=" * 60)
    
    # Find DOREMiDi port
    port = find_midi_port("DOREMiDi")
    
    if not port:
        print("❌ No MIDI port found!")
        sys.exit(1)
    
    print(f"\n✅ Found MIDI port: {port}\n")
    
    # Quick test with default values
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            # Quick test
            channel = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            cc = int(sys.argv[3]) if len(sys.argv) > 3 else 1
            intensity = int(sys.argv[4]) if len(sys.argv) > 4 else 127
            send_smoke_test(port, channel=channel, cc_number=cc, intensity=intensity, duration=3.0)
        elif sys.argv[1] == 'test-ccs':
            # Test multiple CCs
            channel = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            test_multiple_ccs(port, channel=channel)
        elif sys.argv[1] == 'test-channels':
            # Test multiple channels
            cc = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            test_multiple_channels(port, cc_number=cc)
        else:
            print("Usage:")
            print("  python3 test_midi_smoke.py test [channel] [cc] [intensity]")
            print("  python3 test_midi_smoke.py test-ccs [channel]")
            print("  python3 test_midi_smoke.py test-channels [cc]")
    else:
        # Interactive mode
        print("\nChoose test mode:")
        print("1. Quick test (default: Channel 0, CC 1, Intensity 127)")
        print("2. Test multiple CC numbers")
        print("3. Test multiple MIDI channels")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            channel = input("MIDI channel (0-15, default 0): ").strip()
            channel = int(channel) if channel else 0
            
            cc = input("CC number (default 1): ").strip()
            cc = int(cc) if cc else 1
            
            intensity = input("Intensity (0-127, default 127): ").strip()
            intensity = int(intensity) if intensity else 127
            
            send_smoke_test(port, channel=channel, cc_number=cc, intensity=intensity, duration=3.0)
        elif choice == '2':
            channel = input("MIDI channel (0-15, default 0): ").strip()
            channel = int(channel) if channel else 0
            test_multiple_ccs(port, channel=channel)
        elif choice == '3':
            cc = input("CC number (default 1): ").strip()
            cc = int(cc) if cc else 1
            test_multiple_channels(port, cc_number=cc)
        else:
            print("Invalid choice. Running quick test with defaults...")
            send_smoke_test(port, channel=0, cc_number=1, intensity=127, duration=3.0)
