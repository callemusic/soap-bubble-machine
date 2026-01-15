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
    'smokeIntensity': 120,  # MIDI CC value (0-127) - this worked with DOREMiDi!
    'smokeDuration': 3.0,
    'smokeMidiChannel': 0,  # MIDI Channel 0 (0-based) = Channel 1 (1-based) - matches test_midi_smoke.py
    'smokeMidiCC': 1,
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
    'waitAfterDip': 1.0     # Wait after reaching DIP before starting OPEN
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
            midi_port_name = None
            
            for port in ports:
                if 'doremidi' in port.lower() or 'mtd' in port.lower():
                    midi_port_name = port
                    logger.info("Found DOREMiDi port: {}".format(port))
                    break
            
            if not midi_port_name and ports:
                midi_port_name = ports[0]
                logger.warning("DOREMiDi port not found, using: {}".format(midi_port_name))
            
            if midi_port_name:
                midi_port = mido.open_output(midi_port_name)
                midi_initialized = True
                logger.info("MIDI initialized using mido on port: {}".format(midi_port_name))
                return True
            else:
                logger.error("No MIDI output ports found")
                return False
                
        elif MIDI_TYPE == 'pygame':
            # Use pygame.midi (fallback)
            pygame.midi.init()
            
            # Find DOREMiDi port
            port_id = None
            for i in range(pygame.midi.get_count()):
                info = pygame.midi.get_device_info(i)
                if info[3]:  # is_output
                    port_name = info[1].lower()
                    if 'doremidi' in port_name or 'mtd' in port_name:
                        port_id = i
                        logger.info("Found DOREMiDi port: {} (ID: {})".format(info[1], i))
                        break
            
            if port_id is None:
                # Use first available output port
                for i in range(pygame.midi.get_count()):
                    info = pygame.midi.get_device_info(i)
                    if info[3]:  # is_output
                        port_id = i
                        logger.info("Using MIDI port: {} (ID: {})".format(info[1], i))
                        break
            
            if port_id is not None:
                midi_port = port_id  # Store port ID for pygame
                midi_initialized = True
                logger.info("MIDI initialized using pygame.midi on port ID: {}".format(port_id))
                return True
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
    global smoke_running, smoke_stop_timer
    
    if not GLOBAL_CONFIG.get('smokeEnabled', False):
        logger.warning("Smoke control is disabled in config")
        return False
    
    if not init_midi():
        logger.error("Cannot start smoke - MIDI not initialized")
        return False
    
    if smoke_running:
        logger.info("Smoke already running")
        return True
    
    try:
        channel = GLOBAL_CONFIG.get('smokeMidiChannel', 0)
        cc = GLOBAL_CONFIG.get('smokeMidiCC', 1)
        intensity = intensity if intensity is not None else GLOBAL_CONFIG.get('smokeIntensity', 120)
        duration = duration if duration is not None else GLOBAL_CONFIG.get('smokeDuration', 3.0)
        
        # Send MIDI CC message based on MIDI library type
        if MIDI_TYPE == 'mido':
            # mido: use Message class (Python 3, preferred)
            msg = mido.Message('control_change', channel=channel, control=cc, value=intensity)
            midi_port.send(msg)
        elif MIDI_TYPE == 'pygame':
            # pygame.midi: status byte = 0xB0 + channel, then control, value
            midi_out = pygame.midi.Output(midi_port)
            status = 0xB0 + channel
            midi_out.write_short(status, cc, intensity)
            midi_out.close()
        
        smoke_running = True
        
        logger.info("Smoke started: Channel={}, CC={}, Intensity={}, Duration={}s".format(
            channel, cc, intensity, duration))
        
        # Schedule stop
        smoke_stop_timer = threading.Timer(duration, stop_smoke)
        smoke_stop_timer.start()
        
        return True
        
    except Exception as e:
        logger.error("Failed to start smoke: {}".format(e))
        smoke_running = False
        return False

def stop_smoke():
    """Stop smoke machine via MIDI"""
    global smoke_running, smoke_stop_timer
    
    if not smoke_running:
        return True
    
    try:
        channel = GLOBAL_CONFIG.get('smokeMidiChannel', 0)
        cc = GLOBAL_CONFIG.get('smokeMidiCC', 1)
        
        # Send MIDI CC message with value 0
        if MIDI_TYPE == 'mido':
            msg = mido.Message('control_change', channel=channel, control=cc, value=0)
            midi_port.send(msg)
        elif MIDI_TYPE == 'pygame':
            midi_out = pygame.midi.Output(midi_port)
            status = 0xB0 + channel
            midi_out.write_short(status, cc, 0)
            midi_out.close()
        
        smoke_running = False
        
        if smoke_stop_timer:
            smoke_stop_timer.cancel()
            smoke_stop_timer = None
        
        logger.info("Smoke stopped")
        return True
        
    except Exception as e:
        logger.error("Failed to stop smoke: {}".format(e))
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

def move_motors_to_position(target_a, target_b, use_slow_in=False, slow_in_start_distance=100, use_slow_out=False, slow_out_start_distance=100):
    """Move motors to target positions with optional slow-in and slow-out easing.
    
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
    
    # Base step delay (fastest speed)
    base_step_delay = 0.001  # seconds per half-step
    max_delay = 0.005  # Maximum delay for slow-in/slow-out (5x slower)
    
    max_steps = max(abs(steps_a), abs(steps_b))
    
    # Determine directions based on motor behavior:
    # Motor A: LOW = forward (decreases position), HIGH = backward (increases position)
    # Motor B: HIGH = forward (increases position), LOW = backward (decreases position)
    dir_a = GPIO.HIGH if steps_a > 0 else GPIO.LOW  # HIGH = backward (increase), LOW = forward (decrease)
    dir_b = GPIO.HIGH if steps_b > 0 else GPIO.LOW  # HIGH = forward (increase), LOW = backward (decrease)
    
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
    
    # Update positions
    with motor_position_lock:
        motor_a_position = target_a
        motor_b_position = target_b
    
    easing_desc = []
    if use_slow_out:
        easing_desc.append("slow-out")
    if use_slow_in:
        easing_desc.append("slow-in")
    easing_str = " (with {})".format(" and ".join(easing_desc)) if easing_desc else ""
    
    logger.info("Motors moved to target positions (A: {}, B: {}) in {:.2f}s{}".format(
        target_a, target_b, total_duration, easing_str))
    return total_duration

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
                
                # Skip if already in this position (except BLOW which toggles)
                if state_str != 'BLOW' and state_str == current_arm_position:
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
                    logger.info("Dip sequence completed (A: {}, B: {})".format(motor_a_position, motor_b_position))
                
                elif state_str == 'OPEN':
                    current_arm_position = 'OPEN'  # Set immediately to prevent double-clicks
                    # OPEN and HOME are the same - move to home position (0, 0) with slow-in
                    # Start slow-in at 250 steps (about 2 seconds longer with gradual deceleration)
                    movement_duration = move_motors_to_position(0, 0, use_slow_in=True, slow_in_start_distance=250)
                    logger.info("Arms opened to home (A: 0, B: 0) with slow-in")
                
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
                    movement_duration = move_motors_to_position(target_a, target_b, use_slow_out=True, slow_out_start_distance=250)
                    if fan_pwm:
                        fan_pwm.ChangeDutyCycle(0)
                        fan_running = False
                    logger.info("Arms closed (A: {}, B: {}) with slow-out".format(motor_a_position, motor_b_position))
                
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
                GLOBAL_CONFIG.update(post_data)
                
                # Save config to file for persistence
                save_config()
                
                # Initialize GPIO if not already done
                init_gpio()
                
                # Handle fan enabled/disabled toggle
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
                        # Don't auto-start fan, just initialize PWM
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
                        logger.info("Fan PWM initialized at 1kHz (enabled via config update)")
                    except Exception as e:
                        logger.error("Failed to initialize fan PWM: {}".format(e))
                
                # Update fan speed if running (or if just fanSpeed was updated)
                if fan_pwm and 'fanSpeed' in post_data:
                    if fan_running:
                        # Fan is running, update speed immediately
                        try:
                            slider_speed = float(GLOBAL_CONFIG['fanSpeed'])
                            duty_cycle = map_fan_speed(slider_speed)
                            fan_pwm.ChangeDutyCycle(duty_cycle)
                            logger.info("Fan speed updated to {}% PWM".format(duty_cycle))
                        except Exception as e:
                            logger.error("Failed to update fan speed: {}".format(e))
                    # If fan not running, speed is saved in config for next time it starts
                
                response_data = json.dumps({'success': True, 'config': GLOBAL_CONFIG, 'fan_running': fan_running})
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response.encode('utf-8'))
                conn.close()
                return
            
            elif parsed_path.path == '/control_smoke':
                action = post_data.get('action', '')
                intensity = post_data.get('intensity', None)
                duration = post_data.get('duration', None)
                
                if action == 'start':
                    success = start_smoke(intensity=intensity, duration=duration)
                    response_data = json.dumps({'success': success, 'smoke_running': smoke_running})
                elif action == 'stop':
                    success = stop_smoke()
                    response_data = json.dumps({'success': success, 'smoke_running': smoke_running})
                elif action == 'test':
                    # Test smoke for 2 seconds
                    success = start_smoke(intensity=120, duration=2.0)
                    response_data = json.dumps({'success': success, 'smoke_running': smoke_running, 'test': True})
                else:
                    response_data = json.dumps({'success': False, 'error': 'Invalid action. Use "start", "stop", or "test"'})
                
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
