#!/usr/bin/env python3
"""
Test script to send MIDI messages to MIDI-to-DMX converter
"""

import mido
import time
import sys

def list_midi_outputs():
    """List all available MIDI output ports"""
    try:
        outputs = mido.get_output_names()
        print("Available MIDI output ports:")
        for i, port in enumerate(outputs):
            print(f"  [{i}] {port}")
        return outputs
    except Exception as e:
        print(f"Error listing MIDI outputs: {e}")
        return []

def send_midi_note(port_name, channel=0, note=60, velocity=127, duration=1.0):
    """
    Send a MIDI note on/off message
    
    Args:
        port_name: Name of the MIDI output port
        channel: MIDI channel (0-15)
        note: MIDI note number (0-127)
        velocity: Note velocity (0-127)
        duration: How long to hold the note (seconds)
    """
    try:
        with mido.open_output(port_name) as port:
            print(f"Sending MIDI Note On: Channel={channel}, Note={note}, Velocity={velocity}")
            port.send(mido.Message('note_on', channel=channel, note=note, velocity=velocity))
            
            time.sleep(duration)
            
            print(f"Sending MIDI Note Off: Channel={channel}, Note={note}")
            port.send(mido.Message('note_off', channel=channel, note=note, velocity=0))
            print("MIDI message sent successfully!")
            
    except Exception as e:
        print(f"Error sending MIDI: {e}")
        return False
    return True

def send_midi_cc(port_name, channel=0, control=1, value=127):
    """
    Send a MIDI Control Change (CC) message
    
    Args:
        port_name: Name of the MIDI output port
        channel: MIDI channel (0-15)
        control: CC number (0-127)
        value: CC value (0-127)
    """
    try:
        with mido.open_output(port_name) as port:
            print(f"Sending MIDI CC: Channel={channel}, Control={control}, Value={value}")
            port.send(mido.Message('control_change', channel=channel, control=control, value=value))
            print("MIDI CC message sent successfully!")
            
    except Exception as e:
        print(f"Error sending MIDI CC: {e}")
        return False
    return True

def send_continuous_midi_cc(port_name, channel=0, control=1, start_value=0, end_value=127, steps=10, delay=0.1):
    """
    Send a series of MIDI CC messages to ramp up/down
    
    Args:
        port_name: Name of the MIDI output port
        channel: MIDI channel (0-15)
        control: CC number (0-127)
        start_value: Starting CC value
        end_value: Ending CC value
        steps: Number of steps in the ramp
        delay: Delay between steps (seconds)
    """
    try:
        with mido.open_output(port_name) as port:
            print(f"Ramping MIDI CC: Channel={channel}, Control={control}, {start_value} -> {end_value}")
            step_size = (end_value - start_value) / steps
            
            for i in range(steps + 1):
                value = int(start_value + (step_size * i))
                value = max(0, min(127, value))  # Clamp to 0-127
                print(f"  Step {i+1}/{steps+1}: CC value = {value}")
                port.send(mido.Message('control_change', channel=channel, control=control, value=value))
                time.sleep(delay)
            
            print("MIDI CC ramp completed!")
            
    except Exception as e:
        print(f"Error sending MIDI CC ramp: {e}")
        return False
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("MIDI to DMX Test Script")
    print("=" * 60)
    print()
    
    # List available ports
    ports = list_midi_outputs()
    
    if not ports:
        print("\nNo MIDI output ports found!")
        print("Make sure your MIDI-to-DMX converter is connected and recognized.")
        sys.exit(1)
    
    print()
    
    # If port name provided as argument, use it
    if len(sys.argv) > 1:
        port_name = sys.argv[1]
        if port_name not in ports:
            print(f"Warning: '{port_name}' not found in available ports")
            print("Using first available port instead.")
            port_name = ports[0]
    else:
        # Use first available port
        port_name = ports[0]
    
    print(f"Using MIDI port: {port_name}")
    print()
    
    # Test different MIDI messages
    print("Test 1: Sending MIDI Note On/Off (Channel 0, Note 60)")
    send_midi_note(port_name, channel=0, note=60, velocity=127, duration=2.0)
    time.sleep(1)
    
    print("\nTest 2: Sending MIDI Control Change (Channel 0, CC 1, Value 127)")
    send_midi_cc(port_name, channel=0, control=1, value=127)
    time.sleep(1)
    
    print("\nTest 3: Ramping MIDI CC from 0 to 127 (Channel 0, CC 1)")
    send_continuous_midi_cc(port_name, channel=0, control=1, start_value=0, end_value=127, steps=20, delay=0.1)
    time.sleep(1)
    
    print("\nTest 4: Ramping MIDI CC from 127 to 0 (Channel 0, CC 1)")
    send_continuous_midi_cc(port_name, channel=0, control=1, start_value=127, end_value=0, steps=20, delay=0.1)
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
    print("\nIf your smoke machine didn't respond, try:")
    print("  - Different MIDI channels (0-15)")
    print("  - Different CC numbers (1-127)")
    print("  - Different note numbers (0-127)")
    print("  - Check your MIDI-to-DMX converter manual for channel/CC mappings")
