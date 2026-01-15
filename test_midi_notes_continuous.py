#!/usr/bin/env python3
"""
Test all MIDI notes continuously - watch for smoke machine response
"""

import mido
import time
import sys

def note_to_name(note):
    """Convert MIDI note number to name"""
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (note // 12) - 1
    note_name = notes[note % 12]
    return f"{note_name}{octave}"

def find_midi_port(search_term="DOREMiDi"):
    """Find MIDI port containing search term"""
    ports = mido.get_output_names()
    for port in ports:
        if search_term.lower() in port.lower():
            return port
    return ports[0] if ports else None

def test_all_notes_continuous(port_name, channel=1, velocity=127, note_duration=1.5, pause_between=0.3):
    """
    Test all MIDI notes continuously - user watches for smoke response
    """
    try:
        with mido.open_output(port_name) as port:
            print(f"\n{'='*60}")
            print(f"TESTING ALL MIDI NOTES - WATCH FOR SMOKE!")
            print(f"{'='*60}")
            print(f"Port: {port_name}")
            print(f"Channel: {channel}")
            print(f"Velocity: {velocity}")
            print(f"Note duration: {note_duration}s")
            print(f"Pause between: {pause_between}s")
            print(f"{'='*60}\n")
            print("Testing all 128 notes... Watch the smoke machine!")
            print("Press Ctrl+C to stop when you see smoke respond\n")
            
            for note in range(128):
                note_name = note_to_name(note)
                print(f"[{note:3d}/127] Testing Note {note:3d} ({note_name:6s})...", end=" ", flush=True)
                
                # Send note on
                port.send(mido.Message('note_on', channel=channel, note=note, velocity=velocity))
                time.sleep(note_duration)
                
                # Send note off
                port.send(mido.Message('note_off', channel=channel, note=note, velocity=0))
                time.sleep(pause_between)
                
                print("✓")
            
            print("\n" + "="*60)
            print("Completed testing all 128 notes!")
            print("Did any note trigger the smoke machine?")
            print("="*60)
            
    except KeyboardInterrupt:
        print("\n\n✅ Test stopped by user")
        print("Which note number triggered the smoke?")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("MIDI Note Test - Continuous Mode")
    print("=" * 60)
    
    # Find DOREMiDi port
    port = find_midi_port("DOREMiDi")
    
    if not port:
        print("❌ No MIDI port found!")
        sys.exit(1)
    
    print(f"\n✅ Found MIDI port: {port}\n")
    
    channel = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 1
    
    test_all_notes_continuous(port, channel=channel)
