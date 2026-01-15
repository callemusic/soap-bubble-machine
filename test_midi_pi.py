#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test MIDI on Raspberry Pi using pygame (Python 2 compatible)
Run this on the Pi to verify MIDI is working
"""

try:
    import pygame.midi
    print("✅ pygame.midi imported successfully")
except ImportError:
    print("❌ pygame.midi not available")
    print("Install with: pip install pygame")
    exit(1)

print("\nInitializing pygame.midi...")
pygame.midi.init()

print("\nScanning for MIDI devices...")
output_ports = []
for i in range(pygame.midi.get_count()):
    info = pygame.midi.get_device_info(i)
    if info[3]:  # is_output
        output_ports.append((i, info[1]))
        print("  Port {}: {} (interf: {})".format(i, info[1], info[2]))

if not output_ports:
    print("\n❌ No MIDI output ports found!")
    print("Make sure your MIDI-to-DMX converter is connected via USB")
    pygame.midi.quit()
    exit(1)

print("\n✅ Found {} MIDI output port(s)".format(len(output_ports)))

# Test with first port
port_id, port_name = output_ports[0]
print("\nTesting with port {}: {}".format(port_id, port_name))

try:
    midi_out = pygame.midi.Output(port_id)
    
    print("\nSending MIDI CC: Channel=1, CC=1, Value=120")
    # MIDI CC: status = 0xB0 + channel, control, value
    status = 0xB0 + 1  # Channel 1
    midi_out.write_short(status, 1, 120)  # CC 1 = 120
    
    import time
    print("Holding for 3 seconds...")
    time.sleep(3)
    
    print("Sending MIDI CC: Channel=1, CC=1, Value=0 (OFF)")
    midi_out.write_short(status, 1, 0)  # CC 1 = 0
    
    midi_out.close()
    print("\n✅ Test completed successfully!")
    
except Exception as e:
    print("\n❌ Error: {}".format(e))
    import traceback
    traceback.print_exc()

finally:
    pygame.midi.quit()
