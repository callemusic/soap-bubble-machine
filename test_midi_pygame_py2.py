#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test MIDI using pygame (Python 2 compatible)
"""

try:
    import pygame.midi
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("pygame.midi not available")

def list_midi_outputs():
    """List all available MIDI output ports"""
    if not PYGAME_AVAILABLE:
        print("Pygame MIDI not available")
        return []
    
    pygame.midi.init()
    ports = []
    for i in range(pygame.midi.get_count()):
        info = pygame.midi.get_device_info(i)
        if info[3]:  # is_output
            ports.append((i, info[1]))
            print("Port {}: {}".format(i, info[1]))
    return ports

def send_midi_cc(port_id, channel=0, control=1, value=127):
    """Send MIDI Control Change message"""
    if not PYGAME_AVAILABLE:
        print("Pygame MIDI not available")
        return False
    
    try:
        midi_out = pygame.midi.Output(port_id)
        # MIDI CC message: 0xB0 + channel, control, value
        status = 0xB0 + channel
        midi_out.write_short(status, control, value)
        print("Sent MIDI CC: Channel={}, CC={}, Value={}".format(channel, control, value))
        midi_out.close()
        return True
    except Exception as e:
        print("Error sending MIDI: {}".format(e))
        return False

if __name__ == '__main__':
    print("Testing Pygame MIDI (Python 2 compatible)")
    print("=" * 60)
    
    if not PYGAME_AVAILABLE:
        print("\n❌ pygame.midi not available!")
        print("Install with: pip install pygame")
        exit(1)
    
    ports = list_midi_outputs()
    
    if not ports:
        print("\n❌ No MIDI output ports found!")
        exit(1)
    
    # Test with first port
    port_id, port_name = ports[0]
    print("\nUsing port {}: {}".format(port_id, port_name))
    print("\nTesting CC 1 on Channel 1 with value 120...")
    
    send_midi_cc(port_id, channel=1, control=1, value=120)
    
    import time
    print("Holding for 3 seconds...")
    time.sleep(3)
    
    print("Sending CC 1 = 0 (OFF)...")
    send_midi_cc(port_id, channel=1, control=1, value=0)
    
    print("\n✅ Test completed!")
