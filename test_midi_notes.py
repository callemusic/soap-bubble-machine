#!/usr/bin/env python3
"""
Test all MIDI notes to find which one triggers the smoke machine
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

def note_to_name(note):
    """Convert MIDI note number to name"""
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (note // 12) - 1
    note_name = notes[note % 12]
    return f"{note_name}{octave}"

def test_all_notes(port_name, channel=1, velocity=127, note_duration=1.0, pause_between=0.5):
    """
    Test all MIDI notes (0-127) to find which triggers smoke
    
    Args:
        port_name: MIDI output port
        channel: MIDI channel (0-15)
        velocity: Note velocity (0-127)
        note_duration: How long to hold each note
        pause_between: Pause between notes
    """
    try:
        with mido.open_output(port_name) as port:
            print(f"\n{'='*60}")
            print(f"TESTING ALL MIDI NOTES")
            print(f"{'='*60}")
            print(f"Port: {port_name}")
            print(f"Channel: {channel}")
            print(f"Velocity: {velocity}")
            print(f"Note duration: {note_duration}s")
            print(f"Pause between: {pause_between}s")
            print(f"{'='*60}\n")
            
            print("Starting test... Press Ctrl+C to stop early\n")
            
            for note in range(128):
                note_name = note_to_name(note) if 0 <= note <= 127 else f"Note {note}"
                print(f"Testing Note {note:3d} ({note_name:4s})...", end=" ", flush=True)
                
                # Send note on
                port.send(mido.Message('note_on', channel=channel, note=note, velocity=velocity))
                time.sleep(note_duration)
                
                # Send note off
                port.send(mido.Message('note_off', channel=channel, note=note, velocity=0))
                time.sleep(pause_between)
                
                print("✓")
                
                # Every 10 notes, ask if we should continue
                if (note + 1) % 10 == 0:
                    response = input(f"\nTested {note + 1}/128 notes. Did any trigger smoke? (y/n/enter to continue): ")
                    if response.lower() == 'y':
                        which = input("Which note number triggered it? (or 'q' to quit): ")
                        if which.lower() != 'q':
                            try:
                                note_num = int(which)
                                print(f"\n✅ Found working note: {note_num} ({note_to_name(note_num)})")
                                return note_num
                            except ValueError:
                                pass
            
            print("\n" + "="*60)
            print("Completed testing all 128 notes!")
            print("="*60)
            return None
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return None
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None

def test_note_range(port_name, channel=1, start_note=0, end_note=127, velocity=127, note_duration=2.0):
    """
    Test a specific range of MIDI notes with longer duration
    """
    try:
        with mido.open_output(port_name) as port:
            print(f"\n{'='*60}")
            print(f"TESTING NOTES {start_note}-{end_note}")
            print(f"{'='*60}")
            print(f"Port: {port_name}")
            print(f"Channel: {channel}")
            print(f"Velocity: {velocity}")
            print(f"Note duration: {note_duration}s")
            print(f"{'='*60}\n")
            
            for note in range(start_note, end_note + 1):
                note_name = note_to_name(note) if 0 <= note <= 127 else f"Note {note}"
                print(f"\nTesting Note {note:3d} ({note_name:4s})...")
                print(f"  → Note ON (velocity={velocity})")
                
                port.send(mido.Message('note_on', channel=channel, note=note, velocity=velocity))
                time.sleep(note_duration)
                
                print(f"  → Note OFF")
                port.send(mido.Message('note_off', channel=channel, note=note, velocity=0))
                time.sleep(0.5)
                
                response = input(f"  Did smoke machine respond? (y/n/q to quit): ")
                if response.lower() == 'q':
                    break
                if response.lower() == 'y':
                    print(f"\n✅ Found working note: {note} ({note_name})")
                    return note
            
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == '__main__':
    print("=" * 60)
    print("MIDI Note Test - Find Smoke Machine Trigger")
    print("=" * 60)
    
    # Find DOREMiDi port
    port = find_midi_port("DOREMiDi")
    
    if not port:
        print("❌ No MIDI port found!")
        sys.exit(1)
    
    print(f"\n✅ Found MIDI port: {port}\n")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'range':
            # Test specific range
            start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            end = int(sys.argv[3]) if len(sys.argv) > 3 else 127
            channel = int(sys.argv[4]) if len(sys.argv) > 4 else 1
            test_note_range(port, channel=channel, start_note=start, end_note=end)
        else:
            channel = int(sys.argv[1]) if sys.argv[1].isdigit() else 1
            test_all_notes(port, channel=channel)
    else:
        # Quick test all notes
        channel = input("MIDI channel (0-15, default 1): ").strip()
        channel = int(channel) if channel else 1
        
        print("\nChoose test mode:")
        print("1. Quick test all notes (1s each, auto-advance)")
        print("2. Interactive test all notes (2s each, ask after each)")
        print("3. Test specific note range")
        
        choice = input("\nEnter choice (1-3, default 1): ").strip()
        
        if choice == '2':
            test_note_range(port, channel=channel, start_note=0, end_note=127, note_duration=2.0)
        elif choice == '3':
            start = input("Start note (0-127, default 0): ").strip()
            start = int(start) if start else 0
            end = input("End note (0-127, default 127): ").strip()
            end = int(end) if end else 127
            test_note_range(port, channel=channel, start_note=start, end_note=end)
        else:
            test_all_notes(port, channel=channel)
