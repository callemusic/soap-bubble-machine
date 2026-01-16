#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BubbleBot Server using raw sockets (Python 3)
"""

import RPi.GPIO as GPIO
import socket
import logging
import json
import threading
import time
import os
from urllib.parse import urlparse

# Try to import MIDI support - prefer mido (Python 3), fallback to pygame
MIDI_AVAILABLE = False
MIDI_TYPE = None  # 'mido' or 'pygame'
mido = None
pygame = None

try:
    import mido
    MIDI_AVAILABLE = True
    MIDI_TYPE = 'mido'
except ImportError:
    try:
        import pygame.midi
        pygame.midi.init()
        MIDI_AVAILABLE = True
        MIDI_TYPE = 'pygame'
        import pygame  # Import full pygame module for reference
    except ImportError:
        MIDI_AVAILABLE = False
        MIDI_TYPE = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Use absolute path in home directory for config file
CONFIG_FILE = os.path.expanduser('~/bubblebot_config.json')

DEFAULT_CONFIG = {
    'dipDuration': 5.0,
    'liftDuration': 4.0,
    'blowDuration': 3.0,
    'closeDuration': 1.5,
    'fanSpeed': 100,
    'fanEnabled': True,  # Default enabled for 3-wire fan
    'smokeEnabled': False,
    'smokeIntensity': 102,  # MIDI CC value (0-127) - 80% intensity (102/127 ≈ 80%) for DOREMiDi MTD-10
    'smokeDuration': 3.0,
    'smokeMidiChannel': 0,  # MIDI Channel 0 (0-based) = Channel 1 (1-based) - matches test_midi_smoke.py
    'smokeMidiCC': 1,  # CC number 1 - matches test_midi_smoke.py
    # Motor position targets (defaults, will be calibrated)
    'motorADipPosition': 200,
    'motorBDipPosition': -200,
    'motorAOpenPosition': -400,
    'motorBOpenPosition': 400,
    'motorAClosePosition': 200,
    'motorBClosePosition': -200,
    # Wait times between loop states (in seconds)
    'waitAfterOpen': 1.0,   # Wait after reaching OPEN before starting CLOSE
    'waitAfterClose': 1.0,  # Wait after reaching CLOSE before starting DIP
    'waitAfterDip': 1.0,    # Wait after reaching DIP before starting OPEN
    # Multi-track timeline-based loop configuration
    'loopTimeline': [
        {
            'id': 'track-motors',
            'type': 'motors',
            'name': 'Motors',
            'blocks': [
                {'id': 'm1', 'type': 'motor', 'action': 'OPEN', 'startTime': 0, 'duration': 0},
                {'id': 'm2', 'type': 'motor', 'action': 'CLOSE', 'startTime': 2, 'duration': 0},
                {'id': 'm3', 'type': 'motor', 'action': 'DIP', 'startTime': 4, 'duration': 0},
            ],
        },
        {
            'id': 'track-fan',
            'type': 'fan',
            'name': 'Fan',
            'blocks': [
                {'id': 'f1', 'type': 'fan', 'action': 'start', 'startTime': 6, 'duration': 3.0, 'config': {'fanSpeed': 100}},
                {'id': 'f2', 'type': 'fan', 'action': 'stop', 'startTime': 9, 'duration': 0},
            ],
        },
        {
            'id': 'track-smoke',
            'type': 'smoke',
            'name': 'Smoke',
            'blocks': [],
        },
    ],
    'loopDuration': 10.0
}

def load_config():
    """Load configuration from file, or return defaults if file doesn't exist"""
    config_path = CONFIG_FILE
    logger.info("Loading config from: {} (absolute: {})".format(config_path, os.path.abspath(config_path)))
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                saved_config = json.load(f)
                logger.info("Raw config file contents: {}".format(json.dumps(saved_config, indent=2)))
                # Merge with defaults to ensure all keys exist
                config = DEFAULT_CONFIG.copy()
                config.update(saved_config)
                
                # Ensure motor positions exist - if missing from saved config, keep defaults
                # This prevents falling back to 200/-200 if positions were never saved
                if 'motorADipPosition' not in saved_config:
                    logger.warning("⚠ motorADipPosition not in saved config, using default: {}".format(config['motorADipPosition']))
                if 'motorBDipPosition' not in saved_config:
                    logger.warning("⚠ motorBDipPosition not in saved config, using default: {}".format(config['motorBDipPosition']))
                if 'motorAClosePosition' not in saved_config:
                    logger.warning("⚠ motorAClosePosition not in saved config, using default: {}".format(config['motorAClosePosition']))
                if 'motorBClosePosition' not in saved_config:
                    logger.warning("⚠ motorBClosePosition not in saved config, using default: {}".format(config['motorBClosePosition']))
                
                logger.info("Loaded config from {} - Motor positions: DIP(A={}, B={}), CLOSE(A={}, B={})".format(
                    config_path,
                    config.get('motorADipPosition', 200),
                    config.get('motorBDipPosition', -200),
                    config.get('motorAClosePosition', 200),
                    config.get('motorBClosePosition', -200)
                ))
                # Verify motor positions were actually loaded (not just defaults)
                if 'motorAClosePosition' in saved_config:
                    logger.info("✓ CLOSE position loaded from file: A={}, B={}".format(
                        saved_config.get('motorAClosePosition'),
                        saved_config.get('motorBClosePosition')
                    ))
                else:
                    logger.warning("⚠ CLOSE position NOT found in saved config, using defaults")
                return config
        except Exception as e:
            logger.error("Failed to load config file {}: {}".format(config_path, e))
            import traceback
            logger.error(traceback.format_exc())
            logger.info("Using default config values")
            return DEFAULT_CONFIG.copy()
    else:
        logger.warning("No config file found at {} (absolute: {}), using defaults".format(
            config_path, os.path.abspath(config_path)))
        logger.info("Default motor positions: DIP(A={}, B={}), CLOSE(A={}, B={})".format(
            DEFAULT_CONFIG['motorADipPosition'],
            DEFAULT_CONFIG['motorBDipPosition'],
            DEFAULT_CONFIG['motorAClosePosition'],
            DEFAULT_CONFIG['motorBClosePosition']
        ))
        return DEFAULT_CONFIG.copy()

def save_config():
    """Save current configuration to file"""
    config_path = CONFIG_FILE
    try:
        # Ensure directory exists
        config_dir = os.path.dirname(config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, mode=0o755)
        
        with open(config_path, 'w') as f:
            json.dump(GLOBAL_CONFIG, f, indent=2)
        
        # Verify the file was written correctly
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                verify_config = json.load(f)
                logger.info("✓ Config saved to {} (verified) - Motor positions: DIP(A={}, B={}), CLOSE(A={}, B={})".format(
                    config_path,
                    verify_config.get('motorADipPosition', 200),
                    verify_config.get('motorBDipPosition', -200),
                    verify_config.get('motorAClosePosition', 200),
                    verify_config.get('motorBClosePosition', -200)
                ))
                logger.info("Full saved config: {}".format(json.dumps(verify_config, indent=2)))
        else:
            logger.error("Config file was not created at {}".format(config_path))
            return False
        return True
    except Exception as e:
        logger.error("Failed to save config file {}: {}".format(config_path, e))
        import traceback
        logger.error(traceback.format_exc())
        return False

GLOBAL_CONFIG = load_config()

PINS = {'stepA': 17, 'dirA': 27, 'stepB': 22, 'dirB': 23, 'pwmFan': 18, 'dmxChannel': 1}
MACHINE_STATES = {'IDLE': 'IDLE', 'DIP': 'DIP', 'OPEN': 'OPEN', 'BLOW': 'BLOW', 'CLOSE': 'CLOSE', 'SMOKE_TEST': 'SMOKE_TEST'}

fan_running = False
fan_pwm = None
gpio_initialized = False
current_arm_position = 'IDLE'  # Track current arm position: IDLE, DIP, OPEN, CLOSE

# Motor absolute position tracking (in steps)
motor_a_position = 0  # Current absolute position of Motor A (steps from home)
motor_b_position = 0  # Current absolute position of Motor B (steps from home)
motor_position_lock = threading.Lock()  # Lock for thread-safe position updates

# MIDI smoke control
midi_initialized = False
midi_port = None
smoke_running = False
smoke_stop_timer = None

# Continuous motor movement
motor_continuous_running = False
motor_continuous_direction = None
motor_continuous_thread = None
motor_continuous_stop_event = threading.Event()

# Motor movement thread for non-blocking execution
motor_movement_thread = None
motor_movement_lock = threading.Lock()  # Lock to prevent overlapping motor movements

# Fan PWM mapping: slider 0-100% maps to PWM duty cycle
# For 3-wire fan with direct GPIO PWM control (no MOSFET)
# Most 3-wire fans respond well to 0-100% PWM range
def map_fan_speed(slider_percent):
    """Map slider percentage (0-100) to PWM duty cycle (0-100%)"""
    if slider_percent <= 0:
        return 0.0
    # Direct mapping for 3-wire fan - use full 0-100% range
    return min(100.0, max(0.0, float(slider_percent)))

def init_midi():
    """Initialize MIDI output port for smoke control"""
    global midi_initialized, midi_port
    
    if not MIDI_AVAILABLE:
        logger.warning("MIDI not available - cannot initialize smoke control")
        return False
    
    if midi_initialized and midi_port:
        return True
    
    try:
        if MIDI_TYPE == 'mido':
            # Use mido (Python 3, preferred)
            ports = mido.get_output_names()
            logger.info("Available MIDI output ports: {}".format(ports))
            midi_port_name = None
            
            # First, try to find DOREMiDi port
            for port in ports:
                if 'doremidi' in port.lower() or 'mtd' in port.lower():
                    midi_port_name = port
                    logger.info("Found DOREMiDi port: {}".format(port))
                    break
            
            # If DOREMiDi not found, use port at index 1 if available, otherwise first port
            if not midi_port_name and ports:
                if len(ports) > 1:
                    midi_port_name = ports[1]  # Use port index 1 (second port)
                    logger.info("DOREMiDi port not found, using port at index 1: {}".format(midi_port_name))
                else:
                    midi_port_name = ports[0]
                    logger.warning("DOREMiDi port not found, using first available port: {}".format(midi_port_name))
            
            if midi_port_name:
                midi_port = mido.open_output(midi_port_name)
                midi_initialized = True
                logger.info("MIDI initialized using mido on port: {} (Channel: {}, CC: {}, Intensity: {})".format(
                    midi_port_name, 
                    GLOBAL_CONFIG.get('smokeMidiChannel', 0),
                    GLOBAL_CONFIG.get('smokeMidiCC', 1),
                    GLOBAL_CONFIG.get('smokeIntensity', 127)))
                return True
            else:
                logger.error("No MIDI output ports found")
                return False
                
        elif MIDI_TYPE == 'pygame':
            # Use pygame.midi (fallback)
            # Only initialize if not already initialized to avoid invalidating port IDs
            if not pygame.midi.get_init():
                pygame.midi.init()
                logger.info("pygame.midi initialized")
            else:
                logger.info("pygame.midi already initialized, reusing existing session")
            
            logger.info("Scanning for MIDI output ports...")
            # Collect all output ports
            port_id = None
            output_ports = []
            for i in range(pygame.midi.get_count()):
                info = pygame.midi.get_device_info(i)
                if info[3]:  # is_output
                    # info[1] is bytes, decode to string for comparison
                    port_name = info[1].decode('utf-8', errors='ignore').lower()
                    port_display = info[1].decode('utf-8', errors='ignore')
                    output_ports.append((i, port_display))
                    logger.info("Found MIDI output port {}: {}".format(i, port_display))
            
            # Use port at index 1 (second output port) if available, matching test script behavior
            # This corresponds to "port_name 1" in the test script
            if len(output_ports) > 1:
                port_id = output_ports[1][0]  # Use second output port (index 1)
                port_display = output_ports[1][1]
                logger.info("Using port at index 1 (second output port): {} (device ID: {})".format(port_display, port_id))
            elif len(output_ports) > 0:
                port_id = output_ports[0][0]
                port_display = output_ports[0][1]
                logger.info("Only one output port available, using: {} (device ID: {})".format(port_display, port_id))
            
            if port_id is not None:
                # Test that the port is valid by trying to open it
                try:
                    test_out = pygame.midi.Output(port_id)
                    test_out.close()
                    midi_port = port_id  # Store port ID for pygame
                    midi_initialized = True
                    logger.info("MIDI initialized using pygame.midi on port: {} (ID: {}, Channel: {}, CC: {}, Intensity: {})".format(
                        port_display, port_id,
                        GLOBAL_CONFIG.get('smokeMidiChannel', 0),
                        GLOBAL_CONFIG.get('smokeMidiCC', 1),
                        GLOBAL_CONFIG.get('smokeIntensity', 102)))
                    return True
                except Exception as e:
                    logger.error("Failed to open MIDI port {}: {}".format(port_id, e))
                    midi_initialized = False
                    return False
            else:
                logger.error("No MIDI output ports found")
                return False
        else:
            logger.error("MIDI type not set")
            return False
            
    except Exception as e:
        logger.error("Failed to initialize MIDI: {}".format(e))
        return False

def start_smoke(intensity=None, duration=None):
    """Start smoke machine via MIDI"""
    global smoke_running, smoke_stop_timer, midi_initialized, midi_port
    
    if not GLOBAL_CONFIG.get('smokeEnabled', False):
        logger.warning("Smoke control is disabled in config")
        return False
    
    # Ensure pygame.midi is initialized (but don't call init_midi() which does quit/init)
    if MIDI_TYPE == 'pygame':
        if not pygame.midi.get_init():
            logger.info("pygame.midi not initialized, initializing now")
            pygame.midi.init()
        midi_initialized = True  # Mark as initialized (whether we just initialized or it was already initialized)
    elif not midi_initialized:
        # For mido, use init_midi()
        if not init_midi():
            logger.error("Cannot start smoke - MIDI not initialized")
            return False
    
    if smoke_running:
        logger.info("Smoke already running")
        return True
    
    try:
        channel = GLOBAL_CONFIG.get('smokeMidiChannel', 0)
        cc = GLOBAL_CONFIG.get('smokeMidiCC', 1)
        intensity = intensity if intensity is not None else GLOBAL_CONFIG.get('smokeIntensity', 102)
        duration = duration if duration is not None else GLOBAL_CONFIG.get('smokeDuration', 3.0)

        logger.info("Starting smoke: Channel={}, CC={}, Intensity={}, Duration={}s".format(
            channel, cc, intensity, duration))

        # Send MIDI CC message based on MIDI library type
        if MIDI_TYPE == 'mido':
            # mido: use Message class (Python 3, preferred)
            msg = mido.Message('control_change', channel=channel, control=cc, value=intensity)
            midi_port.send(msg)
            logger.info("Sent MIDI CC message: channel={}, control={}, value={}".format(channel, cc, intensity))
        elif MIDI_TYPE == 'pygame':
            # pygame.midi: status byte = 0xB0 + channel, then control, value
            # Always find and open port fresh each time (like test script)
            try:
                # Ensure pygame.midi is initialized
                if not pygame.midi.get_init():
                    logger.info("pygame.midi not initialized, initializing now")
                    pygame.midi.init()
                
                # Find output ports
                output_ports = []
                port_count = pygame.midi.get_count()
                logger.info("Scanning {} MIDI devices for output ports (smoke start)".format(port_count))
                for i in range(port_count):
                    info = pygame.midi.get_device_info(i)
                    if info[3]:  # is_output
                        port_display = info[1].decode('utf-8', errors='ignore')
                        output_ports.append((i, port_display))
                        logger.info("Found output port {}: {} (device ID: {})".format(len(output_ports)-1, port_display, i))
                
                logger.info("Found {} output port(s) for smoke start".format(len(output_ports)))
                
                # Use port at index 1 (second output port) if available, matching test script "port_name 1"
                if len(output_ports) > 1:
                    port_id = output_ports[1][0]  # Use second output port (index 1)
                    port_display = output_ports[1][1]
                    logger.info("Using port at index 1 (second output port) for smoke start: {} (device ID: {})".format(port_display, port_id))
                elif len(output_ports) > 0:
                    port_id = output_ports[0][0]
                    port_display = output_ports[0][1]
                    logger.warning("Only one output port found for smoke start, using: {} (device ID: {})".format(port_display, port_id))
                else:
                    raise Exception("No MIDI output ports available")
                
                logger.info("Opening MIDI port {} (device ID: {}) for smoke start".format(port_display, port_id))
                # Open port, send message, close immediately (like test script)
                try:
                    midi_out = pygame.midi.Output(port_id)
                    status = 0xB0 + channel
                    midi_out.write_short(status, cc, intensity)
                    logger.info("Sent MIDI CC via pygame.midi: channel={}, control={}, value={}".format(channel, cc, intensity))
                    midi_out.close()
                except Exception as e:
                    logger.error("Error opening/sending MIDI via pygame.midi: {}".format(e))
                    # Try to reinitialize and retry
                    logger.info("Attempting to reinitialize MIDI and retry start")
                    try:
                        pygame.midi.quit()
                    except:
                        pass
                    pygame.midi.init()
                    midi_initialized = True
                    
                    # Re-find port after re-init
                    output_ports = []
                    for i in range(pygame.midi.get_count()):
                        info = pygame.midi.get_device_info(i)
                        if info[3]:  # is_output
                            port_display = info[1].decode('utf-8', errors='ignore')
                            output_ports.append((i, port_display))
                    
                    # Use port at index 1 (second output port) if available
                    if len(output_ports) > 1:
                        port_id = output_ports[1][0]  # Use second output port (index 1)
                        port_display = output_ports[1][1]
                    elif len(output_ports) > 0:
                        port_id = output_ports[0][0]
                        port_display = output_ports[0][1]
                    else:
                        raise Exception("No MIDI output ports available after reinit")
                    
                    logger.info("Retry: Opening MIDI port {} (device ID: {}) for smoke start".format(port_display, port_id))
                    midi_out = pygame.midi.Output(port_id)
                    status = 0xB0 + channel
                    midi_out.write_short(status, cc, intensity)
                    logger.info("Successfully sent MIDI CC after reinitialization: channel={}, control={}, value={}".format(channel, cc, intensity))
                    midi_out.close()
            except Exception as e:
                logger.error("Error sending MIDI via pygame.midi: {}".format(e))
                # Mark MIDI as uninitialized to force re-init on next attempt
                midi_initialized = False
                raise
        
        smoke_running = True
        
        logger.info("Smoke started: Channel={}, CC={}, Intensity={}, Duration={}s".format(
            channel, cc, intensity, duration))
        
        # Schedule stop
        logger.info("Scheduling smoke stop timer for {} seconds".format(duration))
        smoke_stop_timer = threading.Timer(duration, lambda: (logger.info("Smoke stop timer fired!"), stop_smoke()))
        smoke_stop_timer.start()
        logger.info("Smoke stop timer started, will fire in {} seconds".format(duration))
        
        return True
        
    except Exception as e:
        logger.error("Failed to start smoke: {}".format(e))
        smoke_running = False
        return False

def stop_smoke():
    """Stop smoke machine via MIDI"""
    global smoke_running, smoke_stop_timer, midi_initialized, midi_port
    
    logger.info("stop_smoke() called, smoke_running={}".format(smoke_running))
    
    if not smoke_running:
        logger.info("Smoke already stopped")
        return True
    
    try:
        # Only initialize MIDI if not already initialized
        # This avoids unnecessary quit/init cycles that can invalidate port IDs
        if not midi_initialized:
            if not init_midi():
                logger.error("Cannot stop smoke - MIDI not initialized")
                return False
        elif MIDI_TYPE == 'pygame':
            # Ensure pygame.midi is still initialized
            if not pygame.midi.get_init():
                logger.warning("pygame.midi was uninitialized, re-initializing")
                midi_initialized = False
                if not init_midi():
                    logger.error("Cannot stop smoke - MIDI re-initialization failed")
                    return False
        
        channel = GLOBAL_CONFIG.get('smokeMidiChannel', 0)
        cc = GLOBAL_CONFIG.get('smokeMidiCC', 1)
        
        logger.info("Stopping smoke: Channel={}, CC={}, sending value=0".format(channel, cc))
        
        # Send MIDI CC message with value 0
        if MIDI_TYPE == 'mido':
            msg = mido.Message('control_change', channel=channel, control=cc, value=0)
            midi_port.send(msg)
            logger.info("Sent MIDI CC stop message via mido: channel={}, control={}, value=0".format(channel, cc))
        elif MIDI_TYPE == 'pygame':
            # Always find and open port fresh each time (like test script)
            try:
                # Ensure pygame.midi is initialized
                if not pygame.midi.get_init():
                    logger.info("pygame.midi not initialized, initializing now")
                    pygame.midi.init()
                
                # Find output ports
                output_ports = []
                port_count = pygame.midi.get_count()
                logger.info("Scanning {} MIDI devices for output ports (smoke stop)".format(port_count))
                for i in range(port_count):
                    info = pygame.midi.get_device_info(i)
                    if info[3]:  # is_output
                        port_display = info[1].decode('utf-8', errors='ignore')
                        output_ports.append((i, port_display))
                        logger.info("Found output port {}: {} (device ID: {})".format(len(output_ports)-1, port_display, i))
                
                logger.info("Found {} output port(s) for smoke stop".format(len(output_ports)))
                
                # Use port at index 1 (second output port) if available, matching test script "port_name 1"
                if len(output_ports) > 1:
                    port_id = output_ports[1][0]  # Use second output port (index 1)
                    port_display = output_ports[1][1]
                    logger.info("Using port at index 1 (second output port) for smoke stop: {} (device ID: {})".format(port_display, port_id))
                elif len(output_ports) > 0:
                    port_id = output_ports[0][0]
                    port_display = output_ports[0][1]
                    logger.warning("Only one output port found for smoke stop, using: {} (device ID: {})".format(port_display, port_id))
                else:
                    raise Exception("No MIDI output ports available")
                
                logger.info("Opening MIDI port {} (device ID: {}) for smoke stop".format(port_display, port_id))
                # Open port, send message, close immediately (like test script)
                midi_out = pygame.midi.Output(port_id)
                status = 0xB0 + channel
                midi_out.write_short(status, cc, 0)
                logger.info("Sent MIDI CC stop message via pygame.midi: channel={}, control={}, value=0".format(channel, cc))
                midi_out.close()
            except Exception as e:
                logger.error("Error sending MIDI stop via pygame.midi: {}".format(e))
                import traceback
                logger.error(traceback.format_exc())
                # Try to reinitialize and send again
                logger.info("Attempting to reinitialize MIDI and retry stop")
                # Force reinitialize pygame.midi
                try:
                    pygame.midi.quit()
                except:
                    pass
                pygame.midi.init()
                midi_initialized = True
                
                try:
                    # Re-find port after re-init - use port index 1 (second output port)
                    output_ports = []
                    for i in range(pygame.midi.get_count()):
                        info = pygame.midi.get_device_info(i)
                        if info[3]:  # is_output
                            port_display = info[1].decode('utf-8', errors='ignore')
                            output_ports.append((i, port_display))
                    
                    # Use port at index 1 (second output port) if available
                    if len(output_ports) > 1:
                        port_id = output_ports[1][0]  # Use second output port (index 1)
                        port_display = output_ports[1][1]
                    elif len(output_ports) > 0:
                        port_id = output_ports[0][0]
                        port_display = output_ports[0][1]
                    else:
                        raise Exception("No MIDI output ports available after reinit")
                    
                    logger.info("Retry: Opening MIDI port {} (device ID: {}) for smoke stop".format(port_display, port_id))
                    midi_out = pygame.midi.Output(port_id)
                    status = 0xB0 + channel
                    midi_out.write_short(status, cc, 0)
                    logger.info("Successfully sent stop message after reinitialization")
                    midi_out.close()
                except Exception as e2:
                    logger.error("Still failed to send stop after reinitialization: {}".format(e2))
                    raise
        
        smoke_running = False
        
        if smoke_stop_timer:
            smoke_stop_timer.cancel()
            smoke_stop_timer = None
        
        logger.info("Smoke stopped successfully")
        return True
        
    except Exception as e:
        logger.error("Failed to stop smoke: {}".format(e))
        import traceback
        logger.error(traceback.format_exc())
        # Still set smoke_running to False even if MIDI fails
        smoke_running = False
        return False

def init_gpio():
    global fan_pwm, gpio_initialized
    if gpio_initialized:
        return
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(PINS['stepA'], GPIO.OUT)
        GPIO.setup(PINS['dirA'], GPIO.OUT)
        GPIO.setup(PINS['stepB'], GPIO.OUT)
        GPIO.setup(PINS['dirB'], GPIO.OUT)
        if GLOBAL_CONFIG['fanEnabled']:
            GPIO.setup(PINS['pwmFan'], GPIO.OUT)
            # Use 1kHz PWM frequency - higher frequency reduces audible noise and stuttering
            # GPIO 18 supports hardware PWM, but RPi.GPIO uses software PWM (max ~1kHz)
            # For true 25kHz PWM, would need pigpio library, but 1kHz is much better than 100Hz
            fan_pwm = GPIO.PWM(PINS['pwmFan'], 1000)  # 1kHz - much better for 3-wire fans
            fan_pwm.start(0)
            logger.info("Fan PWM initialized at 1kHz (3-wire fan, direct GPIO control)")
        gpio_initialized = True
        logger.info("GPIO initialized")
    except Exception as e:
        logger.error("GPIO init error: {}".format(e))

def move_motors_to_position_sync(target_a, target_b, use_slow_in=False, slow_in_start_distance=100, use_slow_out=False, slow_out_start_distance=100):
    """Synchronous motor movement (blocking) - used internally by async wrapper.
    
    Args:
        target_a: Target position for motor A
        target_b: Target position for motor B
        use_slow_in: If True, apply slow-in easing as approaching target (deceleration)
        slow_in_start_distance: Distance (in steps) from target where slow-in begins
        use_slow_out: If True, apply slow-out easing at start (acceleration from slow)
        slow_out_start_distance: Distance (in steps) from start where slow-out ends
    
    Returns:
        duration in seconds
    """
    global motor_a_position, motor_b_position
    init_gpio()
    
    with motor_position_lock:
        current_a = motor_a_position
        current_b = motor_b_position
    
    steps_a = target_a - current_a
    steps_b = target_b - current_b
    
    logger.info("move_motors_to_position_sync: Current (A: {}, B: {}), Target (A: {}, B: {}), Steps needed (A: {}, B: {})".format(
        current_a, current_b, target_a, target_b, steps_a, steps_b))
    
    # Base step delay (fastest speed)
    base_step_delay = 0.001  # seconds per half-step
    max_delay = 0.005  # Maximum delay for slow-in/slow-out (5x slower)
    
    max_steps = max(abs(steps_a), abs(steps_b))
    
    # Determine directions based on motor behavior:
    # Motor A: LOW = forward (decreases position), HIGH = backward (increases position)
    # Motor B: HIGH = forward (increases position), LOW = backward (decreases position)
    dir_a = GPIO.HIGH if steps_a > 0 else GPIO.LOW  # HIGH = backward (increase), LOW = forward (decrease)
    dir_b = GPIO.HIGH if steps_b > 0 else GPIO.LOW  # HIGH = forward (increase), LOW = backward (decrease)
    
    logger.info("Movement: max_steps={}, dir_a={}, dir_b={}, Motor A will step {} times, Motor B will step {} times".format(
        max_steps, "HIGH(backward)" if dir_a == GPIO.HIGH else "LOW(forward)", 
        "HIGH(forward)" if dir_b == GPIO.HIGH else "LOW(backward)",
        abs(steps_a), abs(steps_b)))
    
    GPIO.output(PINS['dirA'], dir_a)
    GPIO.output(PINS['dirB'], dir_b)
    
    total_duration = 0.0
    
    # Move both motors simultaneously
    for i in range(max_steps):
        # Calculate distance remaining (for slow-in) and distance traveled (for slow-out)
        remaining_steps = max_steps - i
        traveled_steps = i
        
        # Calculate step delay with easing
        step_delay = base_step_delay
        
        # Slow-out (acceleration from start): start slow, speed up
        if use_slow_out and traveled_steps < slow_out_start_distance:
            # Quadratic ease-out: delay decreases as we move away from start
            # Normalize distance (0 = at start, 1 = at slow_out_start_distance)
            if slow_out_start_distance > 0:
                normalized_distance = traveled_steps / slow_out_start_distance
                # Quadratic easing: delay = max - (max - base) * normalized_distance^2
                # This gives smooth acceleration from slow to fast
                ease_factor = normalized_distance ** 2
                step_delay = max_delay - (max_delay - base_step_delay) * ease_factor
            else:
                step_delay = max_delay
        
        # Slow-in (deceleration to target): slow down as approaching target
        elif use_slow_in and remaining_steps <= slow_in_start_distance:
            # Quadratic ease-in: delay increases as we approach target
            # Normalize distance (0 = at target, 1 = at slow_in_start_distance)
            if slow_in_start_distance > 0:
                normalized_distance = remaining_steps / slow_in_start_distance
                # Quadratic easing: delay = base + (max - base) * (1 - normalized_distance)^2
                # This gives smooth deceleration
                ease_factor = (1.0 - normalized_distance) ** 2
                step_delay = base_step_delay + (max_delay - base_step_delay) * ease_factor
            else:
                step_delay = max_delay
        
        # Execute step
        if i < abs(steps_a):
            GPIO.output(PINS['stepA'], GPIO.HIGH)
        if i < abs(steps_b):
            GPIO.output(PINS['stepB'], GPIO.HIGH)
        time.sleep(step_delay)
        total_duration += step_delay
        
        if i < abs(steps_a):
            GPIO.output(PINS['stepA'], GPIO.LOW)
        if i < abs(steps_b):
            GPIO.output(PINS['stepB'], GPIO.LOW)
        time.sleep(step_delay)
        total_duration += step_delay
    
    # Update positions - calculate actual final position based on steps taken
    # This ensures we don't overshoot if one motor stops before the other
    with motor_position_lock:
        # Calculate actual final position based on direction and steps taken
        if steps_a > 0:
            # Motor A moved backward (HIGH) - position increases
            actual_a = current_a + abs(steps_a)
        else:
            # Motor A moved forward (LOW) - position decreases
            actual_a = current_a - abs(steps_a)
        
        if steps_b > 0:
            # Motor B moved forward (HIGH) - position increases
            actual_b = current_b + abs(steps_b)
        else:
            # Motor B moved backward (LOW) - position decreases
            actual_b = current_b - abs(steps_b)
        
        # Set to target (should match actual, but use target to ensure accuracy)
        motor_a_position = target_a
        motor_b_position = target_b
        
        logger.info("Position updated after movement: Set to target (A: {}, B: {}), Calculated actual (A: {}, B: {})".format(
            target_a, target_b, actual_a, actual_b))
    
    easing_desc = []
    if use_slow_out:
        easing_desc.append("slow-out")
    if use_slow_in:
        easing_desc.append("slow-in")
    easing_str = " (with {})".format(" and ".join(easing_desc)) if easing_desc else ""
    
    logger.info("Motors moved to target positions (A: {}, B: {}) in {:.2f}s{}".format(
        target_a, target_b, total_duration, easing_str))
    return total_duration

def move_motors_to_position(target_a, target_b, use_slow_in=False, slow_in_start_distance=100, use_slow_out=False, slow_out_start_distance=100, force=False):
    """Non-blocking motor movement - runs in background thread and returns immediately with estimated duration
    
    Args:
        force: If True, interrupt any ongoing movement and start new one (for cleanup/stop scenarios)
    """
    global motor_movement_thread, motor_movement_lock
    
    # Check if a motor movement is already in progress
    waited_for_previous = False
    if motor_movement_thread and motor_movement_thread.is_alive():
        if force:
            # Force interrupt: wait for current movement to finish, then start new one
            logger.warning("Motor movement in progress, forcing new movement (cleanup/stop) - waiting for completion")
            try:
                # Wait longer to ensure movement completes and position is updated
                motor_movement_thread.join(timeout=3.0)  # Wait up to 3 seconds for current movement
                waited_for_previous = True
                logger.info("Previous movement thread finished, re-reading position")
            except Exception as e:
                logger.error("Error waiting for motor movement thread: {}".format(e))
                # Continue anyway - start new movement
        else:
            logger.warning("Motor movement already in progress, ignoring new command")
            return 0.0  # Return 0 duration if movement already in progress
    
    # Calculate estimated duration before starting (for immediate response)
    # ALWAYS re-read position after checking for previous movement (it may have updated)
    with motor_position_lock:
        current_a = motor_a_position
        current_b = motor_b_position
    
    if waited_for_previous:
        logger.info("After waiting for previous movement, current position: A={}, B={}, new target: A={}, B={}".format(
            current_a, current_b, target_a, target_b))
    
    steps_a = abs(target_a - current_a)
    steps_b = abs(target_b - current_b)
    max_steps = max(steps_a, steps_b)
    base_step_delay = 0.001
    estimated_duration = max_steps * base_step_delay * 2  # Rough estimate (will be refined by actual movement)
    
    def move_in_thread():
        """Execute motor movement in background thread"""
        try:
            move_motors_to_position_sync(target_a, target_b, use_slow_in, slow_in_start_distance, use_slow_out, slow_out_start_distance)
        except Exception as e:
            logger.error("Error in motor movement thread: {}".format(e))
        finally:
            # Thread completes, can be reused
            pass
    
    # Start motor movement in background thread
    motor_movement_thread = threading.Thread(target=move_in_thread, daemon=True)
    motor_movement_thread.start()
    
    logger.info("Motor movement started in background thread (target A: {}, B: {}), estimated duration: {:.2f}s".format(
        target_a, target_b, estimated_duration))
    
    return estimated_duration  # Return immediately with estimated duration

def continuous_motor_loop():
    """Background thread for smooth continuous motor stepping"""
    global motor_continuous_running, motor_continuous_direction, motor_a_position, motor_b_position
    init_gpio()
    
    step_delay = 0.0005  # 500 microseconds = 2000 steps/second (very smooth)
    step_counter = 0  # Track steps for position updates
    position_update_interval = 10  # Update position every 10 steps (to avoid lock contention)
    
    while motor_continuous_running and not motor_continuous_stop_event.is_set():
        try:
            if motor_continuous_direction == 'up' or motor_continuous_direction == 'both_forward':
                # Motor A forward (dirA LOW), Motor B forward (dirB HIGH) = arms open/lift
                GPIO.output(PINS['dirA'], GPIO.LOW)
                GPIO.output(PINS['dirB'], GPIO.HIGH)
                GPIO.output(PINS['stepA'], GPIO.HIGH)
                GPIO.output(PINS['stepB'], GPIO.HIGH)
                time.sleep(step_delay)
                GPIO.output(PINS['stepA'], GPIO.LOW)
                GPIO.output(PINS['stepB'], GPIO.LOW)
                time.sleep(step_delay)
                step_counter += 1
                # Update position periodically
                if step_counter >= position_update_interval:
                    with motor_position_lock:
                        motor_a_position -= position_update_interval  # Motor A forward
                        motor_b_position += position_update_interval  # Motor B forward
                    step_counter = 0
                
            elif motor_continuous_direction == 'down' or motor_continuous_direction == 'both_backward':
                # Motor A backward (dirA HIGH), Motor B backward (dirB LOW) = arms close/dip
                GPIO.output(PINS['dirA'], GPIO.HIGH)
                GPIO.output(PINS['dirB'], GPIO.LOW)
                GPIO.output(PINS['stepA'], GPIO.HIGH)
                GPIO.output(PINS['stepB'], GPIO.HIGH)
                time.sleep(step_delay)
                GPIO.output(PINS['stepA'], GPIO.LOW)
                GPIO.output(PINS['stepB'], GPIO.LOW)
                time.sleep(step_delay)
                step_counter += 1
                # Update position periodically
                if step_counter >= position_update_interval:
                    with motor_position_lock:
                        motor_a_position += position_update_interval  # Motor A backward
                        motor_b_position -= position_update_interval  # Motor B backward
                    step_counter = 0
        except Exception as e:
            logger.error("Continuous motor error: {}".format(e))
            break
    
    # Update final position if there are remaining steps
    if step_counter > 0:
        with motor_position_lock:
            if motor_continuous_direction == 'up' or motor_continuous_direction == 'both_forward':
                motor_a_position -= step_counter
                motor_b_position += step_counter
            elif motor_continuous_direction == 'down' or motor_continuous_direction == 'both_backward':
                motor_a_position += step_counter
                motor_b_position -= step_counter
    
    logger.info("Continuous motor movement stopped (A: {}, B: {})".format(motor_a_position, motor_b_position))
    motor_continuous_running = False

def start_continuous_motor(direction):
    """Start continuous motor movement in specified direction"""
    global motor_continuous_running, motor_continuous_direction, motor_continuous_thread, motor_continuous_stop_event
    
    if motor_continuous_running:
        stop_continuous_motor()
    
    if direction not in ['up', 'down', 'both_forward', 'both_backward']:
        return False
    
    motor_continuous_stop_event.clear()
    motor_continuous_direction = direction
    motor_continuous_running = True
    
    motor_continuous_thread = threading.Thread(target=continuous_motor_loop, daemon=True)
    motor_continuous_thread.start()
    logger.info("Continuous motor movement started: {}".format(direction))
    return True

def stop_continuous_motor():
    """Stop continuous motor movement"""
    global motor_continuous_running, motor_continuous_thread
    
    if motor_continuous_running:
        motor_continuous_stop_event.set()
        motor_continuous_running = False
        if motor_continuous_thread:
            motor_continuous_thread.join(timeout=0.5)
        logger.info("Continuous motor movement stopped")
        return True
    return False

def handle_request(conn, addr):
    global fan_running, fan_pwm, current_arm_position, smoke_running, motor_a_position, motor_b_position
    try:
        data = conn.recv(4096)
        if not data:
            return
        
        request = data.decode('utf-8', errors='ignore')
        lines = request.split('\r\n')
        if not lines:
            return
        
        method_line = lines[0]
        parts = method_line.split()
        if len(parts) < 2:
            return
        
        method = parts[0]
        path = parts[1]
        parsed_path = urlparse(path)
        
        # Handle OPTIONS (CORS preflight)
        if method == 'OPTIONS':
            response = "HTTP/1.1 200 OK\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, POST, OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\nContent-Length: 0\r\n\r\n"
            conn.sendall(response.encode('utf-8'))
            conn.close()
            return
        
        # Handle GET /health
        if method == 'GET' and parsed_path.path == '/health':
            with motor_position_lock:
                motor_a_pos = motor_a_position
                motor_b_pos = motor_b_position
            health_data = {
                'status': 'ok',
                'pi': 'bubblebot',
                'fan_running': fan_running,
                'current_position': current_arm_position,
                'smoke_running': smoke_running,
                'midi_available': MIDI_AVAILABLE,
                'midi_initialized': midi_initialized,
                'motor_a_position': motor_a_pos,
                'motor_b_position': motor_b_pos
            }
            response_data = json.dumps(health_data)
            response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
            conn.sendall(response.encode('utf-8'))
            logger.info("Health check response sent")
            conn.close()
            return
        
        # Handle GET /get_config
        if method == 'GET' and parsed_path.path == '/get_config':
            response_data = json.dumps({'success': True, 'config': GLOBAL_CONFIG})
            response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
            conn.sendall(response.encode('utf-8'))
            logger.info("Config requested, sent full config")
            conn.close()
            return
        
        # Handle POST
        if method == 'POST':
            body_start = request.find('\r\n\r\n') + 4
            body = request[body_start:] if body_start > 3 else ''
            
            try:
                post_data = json.loads(body) if body else {}
            except:
                post_data = {}
            
            if parsed_path.path == '/set_state':
                state_str = post_data.get('state', 'IDLE')
                logger.info("Received state: {} (current position: {})".format(state_str, current_arm_position))
                init_gpio()
                
                # Skip if already in this position (except BLOW which toggles, and OPEN which needs to check actual motor position)
                if state_str != 'BLOW' and state_str != 'OPEN' and state_str == current_arm_position:
                    logger.info("Already in {} position - skipping".format(state_str))
                    response_data = json.dumps({'success': True, 'state': state_str, 'fan_running': fan_running, 'skipped': True, 'movement_duration': 0.0})
                    response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response.encode('utf-8'))
                    conn.close()
                    return
                
                movement_duration = 0.0  # Initialize movement duration for states that don't move motors
                
                if state_str == 'IDLE':
                    GPIO.output(PINS['stepA'], GPIO.LOW)
                    GPIO.output(PINS['stepB'], GPIO.LOW)
                    if fan_pwm:
                        fan_pwm.ChangeDutyCycle(0)
                        fan_running = False
                    current_arm_position = 'IDLE'
                    logger.info("All systems stopped")
                
                elif state_str == 'DIP':
                    current_arm_position = 'DIP'  # Set immediately to prevent double-clicks
                    target_a = GLOBAL_CONFIG['motorADipPosition']
                    target_b = GLOBAL_CONFIG['motorBDipPosition']
                    movement_duration = move_motors_to_position(target_a, target_b)
                    logger.info("Dip sequence started - moving to target (A: {}, B: {}), duration: {:.2f}s".format(target_a, target_b, movement_duration))
                
                elif state_str == 'OPEN':
                    current_arm_position = 'OPEN'  # Set immediately to prevent double-clicks
                    # OPEN/HOME always goes to (0, 0) - home position
                    target_a = 0
                    target_b = 0
                    
                    # Check if already at home position
                    with motor_position_lock:
                        current_a = motor_a_position
                        current_b = motor_b_position
                    
                    tolerance = 10  # Allow small tolerance
                    logger.info("OPEN command: Current position A={}, B={}, target=(0, 0)".format(current_a, current_b))
                    if abs(current_a) < tolerance and abs(current_b) < tolerance:
                        logger.info("Already at OPEN position (A: {}, B: {}), skipping movement".format(current_a, current_b))
                        movement_duration = 0.0
                    else:
                        # Move to home position (0, 0) with slow-in
                        # Use force=True to interrupt any ongoing movement (for cleanup scenarios)
                        # IMPORTANT: After waiting for previous movement, re-read position to ensure accuracy
                        # Start slow-in at 250 steps (about 2 seconds longer with gradual deceleration)
                        logger.info("Calling move_motors_to_position with force=True, current tracked position: A={}, B={}".format(current_a, current_b))
                        movement_duration = move_motors_to_position(0, 0, use_slow_in=True, slow_in_start_distance=250, force=True)
                        logger.info("Arms opened to home (A: 0, B: 0) with slow-in, movement duration: {:.2f}s".format(movement_duration))
                
                elif state_str == 'BLOW':
                    # Ensure fan is enabled and initialized
                    if not GLOBAL_CONFIG['fanEnabled']:
                        logger.warning("Fan control requested but fan is disabled in config")
                        response_data = json.dumps({'success': False, 'error': 'Fan is disabled. Enable it in config first.', 'state': state_str})
                        response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                        conn.sendall(response.encode('utf-8'))
                        conn.close()
                        return
                    
                    # Initialize fan PWM if not already done
                    if fan_pwm is None:
                        try:
                            GPIO.setup(PINS['pwmFan'], GPIO.OUT)
                            fan_pwm = GPIO.PWM(PINS['pwmFan'], 1000)  # 1kHz
                            fan_pwm.start(0)
                            logger.info("Fan PWM initialized at 1kHz (lazy init on BLOW)")
                        except Exception as e:
                            logger.error("Failed to initialize fan PWM: {}".format(e))
                            response_data = json.dumps({'success': False, 'error': 'Failed to initialize fan PWM', 'state': state_str})
                            response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                            conn.sendall(response.encode('utf-8'))
                            conn.close()
                            return
                    
                    # Toggle fan on/off
                    if fan_running:
                        fan_pwm.ChangeDutyCycle(0)
                        fan_running = False
                        logger.info("Fan stopped")
                    else:
                        # Map slider speed to PWM duty cycle (0-100%)
                        slider_speed = float(GLOBAL_CONFIG['fanSpeed'])
                        duty_cycle = map_fan_speed(slider_speed)
                        # Start fan directly at target speed - no delay for faster response
                        # For 3-wire PWM fans, starting directly at target speed is usually fastest
                        fan_pwm.ChangeDutyCycle(duty_cycle)
                        fan_running = True
                        logger.info("Fan started at {}% PWM".format(duty_cycle))
                
                elif state_str == 'CLOSE':
                    current_arm_position = 'CLOSE'  # Set immediately to prevent double-clicks
                    target_a = GLOBAL_CONFIG['motorAClosePosition']
                    target_b = GLOBAL_CONFIG['motorBClosePosition']
                    logger.info("CLOSE state: Using target positions from GLOBAL_CONFIG: A={}, B={}".format(target_a, target_b))
                    # Apply slow-out (slow start) for CLOSE movement - start slow, then speed up
                    # Reduced slow-out distance for faster CLOSE movement
                    movement_duration = move_motors_to_position(target_a, target_b, use_slow_out=True, slow_out_start_distance=100)
                    # NOTE: Fan control should be handled by timeline blocks, not by motor states
                    # Removing automatic fan stop on CLOSE - let timeline control fan
                    if fan_pwm and fan_running:
                        logger.warning("CLOSE state: Fan is running (fan_running={}), but NOT stopping it - fan should be controlled by timeline blocks".format(fan_running))
                    logger.info("Arms closed - moving to target (A: {}, B: {}) with slow-out, duration: {:.2f}s".format(target_a, target_b, movement_duration))
                
                elif state_str == 'HOME':
                    current_arm_position = 'HOME'  # Set immediately to prevent double-clicks
                    movement_duration = move_motors_to_position(0, 0)
                    logger.info("Motors moved to home position (A: 0, B: 0)")
                
                # Get updated motor positions for response
                with motor_position_lock:
                    motor_a_pos = motor_a_position
                    motor_b_pos = motor_b_position
                
                response_data = json.dumps({'success': True, 'state': state_str, 'fan_running': fan_running, 'current_position': current_arm_position, 'motor_a_position': motor_a_pos, 'motor_b_position': motor_b_pos, 'movement_duration': movement_duration})
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response.encode('utf-8'))
                conn.close()
                return
            
            elif parsed_path.path == '/update_config' or parsed_path.path == '/set_config':
                logger.info("Received config update: {}".format(post_data))
                # Update only the keys that are provided, preserving existing values
                # This ensures motor positions aren't lost if not included in the update
                for key, value in post_data.items():
                    GLOBAL_CONFIG[key] = value
                
                # Ensure motor positions exist (fallback to defaults if missing)
                if 'motorADipPosition' not in GLOBAL_CONFIG:
                    GLOBAL_CONFIG['motorADipPosition'] = DEFAULT_CONFIG['motorADipPosition']
                if 'motorBDipPosition' not in GLOBAL_CONFIG:
                    GLOBAL_CONFIG['motorBDipPosition'] = DEFAULT_CONFIG['motorBDipPosition']
                if 'motorAClosePosition' not in GLOBAL_CONFIG:
                    GLOBAL_CONFIG['motorAClosePosition'] = DEFAULT_CONFIG['motorAClosePosition']
                if 'motorBClosePosition' not in GLOBAL_CONFIG:
                    GLOBAL_CONFIG['motorBClosePosition'] = DEFAULT_CONFIG['motorBClosePosition']
                if 'motorAOpenPosition' not in GLOBAL_CONFIG:
                    GLOBAL_CONFIG['motorAOpenPosition'] = DEFAULT_CONFIG['motorAOpenPosition']
                if 'motorBOpenPosition' not in GLOBAL_CONFIG:
                    GLOBAL_CONFIG['motorBOpenPosition'] = DEFAULT_CONFIG['motorBOpenPosition']
                
                logger.info("Config updated - Motor positions: DIP(A={}, B={}), CLOSE(A={}, B={})".format(
                    GLOBAL_CONFIG.get('motorADipPosition', 200),
                    GLOBAL_CONFIG.get('motorBDipPosition', -200),
                    GLOBAL_CONFIG.get('motorAClosePosition', 200),
                    GLOBAL_CONFIG.get('motorBClosePosition', -200)
                ))
                
                # Save config to file for persistence
                save_config()
                
                # Initialize GPIO if not already done
                init_gpio()
                
                # Handle fan enabled/disabled toggle
                fan_should_start = False
                if 'fanEnabled' in post_data:
                    if GLOBAL_CONFIG['fanEnabled']:
                        # Fan enabled: initialize PWM if not already done
                        if fan_pwm is None:
                            try:
                                GPIO.setup(PINS['pwmFan'], GPIO.OUT)
                                fan_pwm = GPIO.PWM(PINS['pwmFan'], 1000)  # 1kHz
                                fan_pwm.start(0)
                                logger.info("Fan PWM initialized at 1kHz (enabled via config update)")
                            except Exception as e:
                                logger.error("Failed to initialize fan PWM: {}".format(e))
                        # If fanSpeed is also being set in this update, start the fan
                        if 'fanSpeed' in post_data:
                            fan_should_start = True
                    else:
                        # Fan disabled: stop fan if running
                        if fan_pwm and fan_running:
                            fan_pwm.ChangeDutyCycle(0)
                            fan_running = False
                            logger.info("Fan stopped (disabled via config)")
                elif GLOBAL_CONFIG['fanEnabled'] and fan_pwm is None:
                    # Fan is enabled but PWM not initialized, initialize it now
                    try:
                        GPIO.setup(PINS['pwmFan'], GPIO.OUT)
                        fan_pwm = GPIO.PWM(PINS['pwmFan'], 1000)  # 1kHz
                        fan_pwm.start(0)
                        logger.info("Fan PWM initialized at 1kHz (lazy init)")
                    except Exception as e:
                        logger.error("Failed to initialize fan PWM: {}".format(e))
                
                # Update fan speed and start/stop fan
                if fan_pwm and 'fanSpeed' in post_data:
                    try:
                        slider_speed = float(GLOBAL_CONFIG['fanSpeed'])
                        duty_cycle = map_fan_speed(slider_speed)
                        if fan_should_start:
                            # Start fan at specified speed (from timeline fan start block)
                            # Give a brief kick to 100% to help it start faster, then set target speed
                            if duty_cycle > 0:
                                fan_pwm.ChangeDutyCycle(100)  # Brief kick to full speed for faster startup
                                time.sleep(0.1)  # 100ms kick to ensure fan starts spinning
                            fan_pwm.ChangeDutyCycle(duty_cycle)
                            fan_running = True
                            logger.info("Fan started at {}% PWM (from timeline, with quick start kick)".format(duty_cycle))
                        elif fan_running:
                            # Fan is running, update speed immediately
                            fan_pwm.ChangeDutyCycle(duty_cycle)
                            logger.info("Fan speed updated to {}% PWM".format(duty_cycle))
                        # If fan not running and not starting, speed is saved in config for next time
                    except Exception as e:
                        logger.error("Failed to update fan speed: {}".format(e))
                
                # Handle explicit fan stop (fanEnabled: false with fanSpeed: 0 or just fanEnabled: false)
                if 'fanEnabled' in post_data and not GLOBAL_CONFIG['fanEnabled']:
                    if fan_pwm and fan_running:
                        fan_pwm.ChangeDutyCycle(0)
                        fan_running = False
                        logger.info("Fan stopped (fanEnabled set to false)")
                
                response_data = json.dumps({'success': True, 'config': GLOBAL_CONFIG, 'fan_running': fan_running})
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response.encode('utf-8'))
                conn.close()
                return
            
            elif parsed_path.path == '/control_smoke':
                logger.info("Received smoke control request: {}".format(post_data))
                action = post_data.get('action', '')
                intensity = post_data.get('intensity', None)
                duration = post_data.get('duration', None)
                
                logger.info("Smoke control: action={}, intensity={}, duration={}, smokeEnabled={}".format(
                    action, intensity, duration, GLOBAL_CONFIG.get('smokeEnabled', False)))
                
                try:
                    if action == 'start':
                        success = start_smoke(intensity=intensity, duration=duration)
                        logger.info("Smoke start result: success={}, smoke_running={}".format(success, smoke_running))
                        response_data = json.dumps({'success': success, 'smoke_running': smoke_running})
                    elif action == 'stop':
                        success = stop_smoke()
                        logger.info("Smoke stop result: success={}, smoke_running={}".format(success, smoke_running))
                        response_data = json.dumps({'success': success, 'smoke_running': smoke_running})
                    elif action == 'test':
                        # Test smoke for 2 seconds
                        logger.info("Smoke test requested")
                        success = start_smoke(intensity=127, duration=2.0)
                        logger.info("Smoke test result: success={}, smoke_running={}".format(success, smoke_running))
                        response_data = json.dumps({'success': success, 'smoke_running': smoke_running, 'test': True})
                    else:
                        logger.warning("Invalid smoke action: {}".format(action))
                        response_data = json.dumps({'success': False, 'error': 'Invalid action. Use "start", "stop", or "test"'})
                    
                    response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response.encode('utf-8'))
                    conn.close()
                    return
                except Exception as e:
                    logger.error("Error in smoke control: {}".format(e))
                    import traceback
                    logger.error(traceback.format_exc())
                    response_data = json.dumps({'success': False, 'smoke_running': smoke_running, 'error': str(e)})
                    response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response.encode('utf-8'))
                    conn.close()
                    return
            
            elif parsed_path.path == '/motor_step':
                # Fine motor control: step motors individually
                direction = post_data.get('direction', '')  # 'up', 'down', 'left', 'right', 'both_forward', 'both_backward'
                steps = int(post_data.get('steps', 10))  # Number of steps (default 10)
                
                init_gpio()
                
                try:
                    if direction == 'up' or direction == 'both_forward':
                        # Motor A forward (dirA LOW), Motor B forward (dirB HIGH) = arms open/lift
                        GPIO.output(PINS['dirA'], GPIO.LOW)
                        GPIO.output(PINS['dirB'], GPIO.HIGH)
                        for _ in range(steps):
                            GPIO.output(PINS['stepA'], GPIO.HIGH)
                            GPIO.output(PINS['stepB'], GPIO.HIGH)
                            time.sleep(0.001)
                            GPIO.output(PINS['stepA'], GPIO.LOW)
                            GPIO.output(PINS['stepB'], GPIO.LOW)
                            time.sleep(0.001)
                        with motor_position_lock:
                            motor_a_position -= steps  # Motor A forward
                            motor_b_position += steps  # Motor B forward
                        logger.info("Motors stepped {} steps: UP/BOTH_FORWARD (A: {}, B: {})".format(steps, motor_a_position, motor_b_position))
                    
                    elif direction == 'down' or direction == 'both_backward':
                        # Motor A backward (dirA HIGH), Motor B backward (dirB LOW) = arms close/dip
                        GPIO.output(PINS['dirA'], GPIO.HIGH)
                        GPIO.output(PINS['dirB'], GPIO.LOW)
                        for _ in range(steps):
                            GPIO.output(PINS['stepA'], GPIO.HIGH)
                            GPIO.output(PINS['stepB'], GPIO.HIGH)
                            time.sleep(0.001)
                            GPIO.output(PINS['stepA'], GPIO.LOW)
                            GPIO.output(PINS['stepB'], GPIO.LOW)
                            time.sleep(0.001)
                        with motor_position_lock:
                            motor_a_position += steps  # Motor A backward
                            motor_b_position -= steps  # Motor B backward
                        logger.info("Motors stepped {} steps: DOWN/BOTH_BACKWARD (A: {}, B: {})".format(steps, motor_a_position, motor_b_position))
                    
                    elif direction == 'left':
                        # Motor A only forward = rotate left
                        GPIO.output(PINS['dirA'], GPIO.LOW)
                        GPIO.output(PINS['dirB'], GPIO.LOW)  # B not moving
                        for _ in range(steps):
                            GPIO.output(PINS['stepA'], GPIO.HIGH)
                            time.sleep(0.001)
                            GPIO.output(PINS['stepA'], GPIO.LOW)
                            time.sleep(0.001)
                        with motor_position_lock:
                            motor_a_position -= steps  # Motor A forward
                        logger.info("Motor A stepped {} steps: LEFT (A: {}, B: {})".format(steps, motor_a_position, motor_b_position))
                    
                    elif direction == 'right':
                        # Motor B only forward = rotate right
                        GPIO.output(PINS['dirA'], GPIO.LOW)  # A not moving
                        GPIO.output(PINS['dirB'], GPIO.HIGH)
                        for _ in range(steps):
                            GPIO.output(PINS['stepB'], GPIO.HIGH)
                            time.sleep(0.001)
                            GPIO.output(PINS['stepB'], GPIO.LOW)
                            time.sleep(0.001)
                        with motor_position_lock:
                            motor_b_position += steps  # Motor B forward
                        logger.info("Motor B stepped {} steps: RIGHT (A: {}, B: {})".format(steps, motor_a_position, motor_b_position))
                    
                    elif direction == 'motor_a_forward':
                        # Motor A forward (dirA LOW)
                        GPIO.output(PINS['dirA'], GPIO.LOW)
                        GPIO.output(PINS['dirB'], GPIO.LOW)  # B not moving
                        for _ in range(steps):
                            GPIO.output(PINS['stepA'], GPIO.HIGH)
                            time.sleep(0.001)
                            GPIO.output(PINS['stepA'], GPIO.LOW)
                            time.sleep(0.001)
                        with motor_position_lock:
                            motor_a_position -= steps  # Motor A forward
                        logger.info("Motor A forward: {} steps (A: {}, B: {})".format(steps, motor_a_position, motor_b_position))
                    
                    elif direction == 'motor_a_backward':
                        # Motor A backward (dirA HIGH)
                        GPIO.output(PINS['dirA'], GPIO.HIGH)
                        GPIO.output(PINS['dirB'], GPIO.LOW)  # B not moving
                        for _ in range(steps):
                            GPIO.output(PINS['stepA'], GPIO.HIGH)
                            time.sleep(0.001)
                            GPIO.output(PINS['stepA'], GPIO.LOW)
                            time.sleep(0.001)
                        with motor_position_lock:
                            motor_a_position += steps  # Motor A backward
                        logger.info("Motor A backward: {} steps (A: {}, B: {})".format(steps, motor_a_position, motor_b_position))
                    
                    elif direction == 'motor_b_forward':
                        # Motor B forward (dirB HIGH)
                        GPIO.output(PINS['dirA'], GPIO.LOW)  # A not moving
                        GPIO.output(PINS['dirB'], GPIO.HIGH)
                        for _ in range(steps):
                            GPIO.output(PINS['stepB'], GPIO.HIGH)
                            time.sleep(0.001)
                            GPIO.output(PINS['stepB'], GPIO.LOW)
                            time.sleep(0.001)
                        with motor_position_lock:
                            motor_b_position += steps  # Motor B forward
                        logger.info("Motor B forward: {} steps (A: {}, B: {})".format(steps, motor_a_position, motor_b_position))
                    
                    elif direction == 'motor_b_backward':
                        # Motor B backward (dirB LOW)
                        GPIO.output(PINS['dirA'], GPIO.LOW)  # A not moving
                        GPIO.output(PINS['dirB'], GPIO.LOW)
                        for _ in range(steps):
                            GPIO.output(PINS['stepB'], GPIO.HIGH)
                            time.sleep(0.001)
                            GPIO.output(PINS['stepB'], GPIO.LOW)
                            time.sleep(0.001)
                        with motor_position_lock:
                            motor_b_position -= steps  # Motor B backward
                        logger.info("Motor B backward: {} steps (A: {}, B: {})".format(steps, motor_a_position, motor_b_position))
                    
                    else:
                        response_data = json.dumps({'success': False, 'error': 'Invalid direction. Use "up", "down", "left", "right", "both_forward", or "both_backward"'})
                        response = "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                        conn.sendall(response.encode('utf-8'))
                        conn.close()
                        return
                    
                    # Return updated positions
                    with motor_position_lock:
                        motor_a_pos = motor_a_position
                        motor_b_pos = motor_b_position
                    response_data = json.dumps({'success': True, 'direction': direction, 'steps': steps, 'motor_a_position': motor_a_pos, 'motor_b_position': motor_b_pos})
                    response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response.encode('utf-8'))
                    conn.close()
                    return
                    
                except Exception as e:
                    logger.error("Motor step error: {}".format(e))
                    response_data = json.dumps({'success': False, 'error': str(e)})
                    response = "HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response.encode('utf-8'))
                    conn.close()
                    return
            
            elif parsed_path.path == '/motor_continuous':
                # Continuous smooth motor movement
                action = post_data.get('action', '')  # 'start' or 'stop'
                direction = post_data.get('direction', '')  # 'up' or 'down'
                
                init_gpio()
                
                try:
                    if action == 'start':
                        if direction not in ['up', 'down']:
                            response_data = json.dumps({'success': False, 'error': 'Invalid direction. Use "up" or "down"'})
                            response = "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                            conn.sendall(response.encode('utf-8'))
                            conn.close()
                            return
                        
                        success = start_continuous_motor(direction)
                        # Return current positions when starting continuous movement
                        with motor_position_lock:
                            motor_a_pos = motor_a_position
                            motor_b_pos = motor_b_position
                        response_data = json.dumps({'success': success, 'direction': direction, 'running': motor_continuous_running, 'motor_a_position': motor_a_pos, 'motor_b_position': motor_b_pos})
                    
                    elif action == 'stop':
                        success = stop_continuous_motor()
                        # Return updated positions after stopping continuous movement
                        with motor_position_lock:
                            motor_a_pos = motor_a_position
                            motor_b_pos = motor_b_position
                        response_data = json.dumps({'success': success, 'running': motor_continuous_running, 'motor_a_position': motor_a_pos, 'motor_b_position': motor_b_pos})
                    
                    else:
                        response_data = json.dumps({'success': False, 'error': 'Invalid action. Use "start" or "stop"'})
                        response = "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                        conn.sendall(response.encode('utf-8'))
                        conn.close()
                        return
                    
                    response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response.encode('utf-8'))
                    conn.close()
                    return
                    
                except Exception as e:
                    logger.error("Continuous motor error: {}".format(e))
                    response_data = json.dumps({'success': False, 'error': str(e)})
                    response = "HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response.encode('utf-8'))
                    conn.close()
                    return
            
            elif parsed_path.path == '/motor_home' or parsed_path.path == '/calibrate':
                # Reset motor positions to home (0, 0)
                # This sets the current physical position as the reference/home position
                with motor_position_lock:
                    motor_a_position = 0
                    motor_b_position = 0
                logger.info("Motor positions reset to home (0, 0)")
                response_data = json.dumps({'success': True, 'motor_a_position': 0, 'motor_b_position': 0, 'message': 'Motors calibrated to home position'})
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response.encode('utf-8'))
                conn.close()
                return
            
            elif parsed_path.path == '/save_motor_position':
                # Save current motor positions as target for a specific state
                state = post_data.get('state', '')  # 'DIP', 'OPEN', or 'CLOSE'
                with motor_position_lock:
                    current_a = motor_a_position
                    current_b = motor_b_position
                
                if state == 'DIP':
                    GLOBAL_CONFIG['motorADipPosition'] = current_a
                    GLOBAL_CONFIG['motorBDipPosition'] = current_b
                    logger.info("Saved DIP position: A={}, B={}".format(current_a, current_b))
                elif state == 'OPEN':
                    GLOBAL_CONFIG['motorAOpenPosition'] = current_a
                    GLOBAL_CONFIG['motorBOpenPosition'] = current_b
                    logger.info("Saved OPEN position: A={}, B={}".format(current_a, current_b))
                elif state == 'CLOSE':
                    GLOBAL_CONFIG['motorAClosePosition'] = current_a
                    GLOBAL_CONFIG['motorBClosePosition'] = current_b
                    logger.info("Saved CLOSE position: A={}, B={}".format(current_a, current_b))
                else:
                    response_data = json.dumps({'success': False, 'error': 'Invalid state. Use "DIP", "OPEN", or "CLOSE"'})
                    response = "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response.encode('utf-8'))
                    conn.close()
                    return
                
                # Persist config to file
                save_config()
                
                response_data = json.dumps({'success': True, 'state': state, 'motor_a_position': current_a, 'motor_b_position': current_b, 'config': GLOBAL_CONFIG})
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response.encode('utf-8'))
                conn.close()
                return
        
        # 404
        response = "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n"
        conn.sendall(response.encode('utf-8'))
        conn.close()
        
    except Exception as e:
        logger.error("Request error: {}".format(e))
        try:
            conn.close()
        except:
            pass

def run_server(port=8080):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', port))
    s.listen(5)
    logger.info("Starting BubbleBot server on port {}...".format(port))
    
    try:
        while True:
            conn, addr = s.accept()
            logger.info("Connection from: {}".format(addr))
            # Handle each request in the same thread (simple, works for low traffic)
            handle_request(conn, addr)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        stop_smoke()
        stop_continuous_motor()
        if fan_pwm:
            fan_pwm.stop()
        if MIDI_TYPE == 'mido' and midi_port:
            midi_port.close()
        elif MIDI_TYPE == 'pygame':
            pygame.midi.quit()
        GPIO.cleanup()
        s.close()

if __name__ == '__main__':
    run_server()
