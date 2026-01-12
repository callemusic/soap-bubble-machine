#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BubbleBot Server using raw sockets (like test_tcp that worked)
"""

import RPi.GPIO as GPIO
import socket
import logging
import json
import threading
from urlparse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

GLOBAL_CONFIG = {
    'dipWait': 3.0,  # Seconds arms stay at DIP position after reaching it
    'openWait': 2.0,  # Seconds arms stay at OPEN position after reaching it
    'blowDuration': 5.0,  # Not used in automatic sequence (kept for backward compatibility)
    'closeWait': 2.0,  # Seconds arms stay at CLOSE position after reaching it
    'fanSpeed': 100,
    'fanEnabled': True,
    'fanStartDelay': 1.6,  # Seconds delay after DIP phase ends before fan starts
    'fanDuration': 4.0,  # Total seconds fan should run (independent of arm movement timing)
    # Movement speed controls (per phase)
    'dipToOpenSpeed': 0.002,  # Base step delay for DIP to OPEN movement (seconds)
    'dipToOpenRampUp': 0,  # Ramp-up steps for DIP to OPEN movement (acceleration at start)
    'dipToOpenSlowIn': 150,  # Slow-in steps for DIP to OPEN movement (deceleration at end)
    'openToCloseSpeed': 0.001,  # Base step delay for OPEN to CLOSE movement (seconds, faster)
    'openToCloseRampUp': 0,  # Ramp-up steps for OPEN to CLOSE movement (acceleration at start)
    'openToCloseSlowIn': 0,  # Slow-in steps for OPEN to CLOSE movement (deceleration at end)
    'closeToDipSpeed': 0.002,  # Base step delay for CLOSE to DIP movement (seconds)
    'closeToDipRampUp': 0,  # Ramp-up steps for CLOSE to DIP movement (acceleration at start)
    'closeToDipSlowIn': 0,  # Slow-in steps for CLOSE to DIP movement (deceleration at end)
    # Legacy/fallback values (kept for backward compatibility)
    'slowInSteps': 150,  # Fallback slow-in steps
    'baseStepDelay': 0.002  # Fallback base step delay
}

PINS = {'stepA': 17, 'dirA': 27, 'stepB': 22, 'dirB': 23, 'pwmFan': 18, 'dmxChannel': 1}
MACHINE_STATES = {'IDLE': 'IDLE', 'DIP': 'DIP', 'OPEN': 'OPEN', 'BLOW': 'BLOW', 'CLOSE': 'CLOSE', 'SMOKE_TEST': 'SMOKE_TEST'}

fan_running = False
fan_pwm = None
gpio_initialized = False
current_arm_position = 'IDLE'  # Track current arm position: IDLE, DIP, OPEN, CLOSE
fan_stop_timer = None  # Timer to stop fan after duration

# Motor position tracking (steps from home position)
motor_positions = {
    'motorA': 0,  # Current position relative to home
    'motorB': 0,
    'homeA': 0,   # Saved home position offset (OPEN)
    'homeB': 0,
    'dipA': None,  # Saved DIP position (Motor A, Motor B)
    'dipB': None,
    'closeA': None,  # Saved CLOSE position (Motor A, Motor B)
    'closeB': None,
    'motorAEnabled': True,  # Motor A enabled/disabled
    'motorBEnabled': True   # Motor B enabled/disabled
}

CONFIG_FILE = 'motor_positions.json'
SETUPS_FILE = 'motor_setups.json'

def load_motor_positions():
    """Load saved motor positions from file"""
    global motor_positions
    try:
        import os
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                motor_positions.update(saved)
                logger.info("Loaded motor positions: {}".format(motor_positions))
        
        # On startup, assume motors are at HOME position (OPEN) if we have saved HOME
        # This ensures absolute positions are correct after restart
        if motor_positions.get('homeA') is not None and motor_positions.get('homeB') is not None:
            # Set current position to HOME on startup (HOME/OPEN is 0,0)
            motor_positions['motorA'] = motor_positions['homeA']
            motor_positions['motorB'] = motor_positions['homeB']
            logger.info("Set current position to HOME on startup: Motor A: {}, Motor B: {} (HOME/OPEN = 0,0)".format(
                motor_positions['motorA'], motor_positions['motorB']))
        else:
            # No HOME saved, assume HOME/OPEN position is 0,0
            motor_positions['motorA'] = 0
            motor_positions['motorB'] = 0
            motor_positions['homeA'] = 0
            motor_positions['homeB'] = 0
            logger.info("No HOME saved, assuming HOME/OPEN position: Motor A: 0, Motor B: 0")
    except Exception as e:
        logger.error("Failed to load motor positions: {}".format(e))
        # On error, assume default HOME position
        motor_positions['motorA'] = -400
        motor_positions['motorB'] = 400

def save_motor_positions():
    """Save motor positions to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(motor_positions, f)
        logger.info("Saved motor positions: {}".format(motor_positions))
        return True
    except Exception as e:
        logger.error("Failed to save motor positions: {}".format(e))
        return False

# Load positions on startup
load_motor_positions()

# Motor setups/scenes management
def load_setups():
    """Load saved motor setups from file"""
    try:
        import os
        if os.path.exists(SETUPS_FILE):
            with open(SETUPS_FILE, 'r') as f:
                setups = json.load(f)
                logger.info("Loaded {} motor setups".format(len(setups)))
                return setups
        return {}
    except Exception as e:
        logger.error("Failed to load motor setups: {}".format(e))
        return {}

def save_setups(setups):
    """Save motor setups to file"""
    try:
        with open(SETUPS_FILE, 'w') as f:
            json.dump(setups, f, indent=2)
        logger.info("Saved {} motor setups".format(len(setups)))
        return True
    except Exception as e:
        logger.error("Failed to save motor setups: {}".format(e))
        return False

def save_current_setup(setup_name):
    """Save current motor positions as a named setup"""
    global motor_positions
    setups = load_setups()
    setups[setup_name] = {
        'homeA': motor_positions.get('homeA', 0),
        'homeB': motor_positions.get('homeB', 0),
        'dipA': motor_positions.get('dipA'),
        'dipB': motor_positions.get('dipB'),
        'closeA': motor_positions.get('closeA'),
        'closeB': motor_positions.get('closeB'),
        'motorA': motor_positions.get('motorA', 0),  # Current position
        'motorB': motor_positions.get('motorB', 0),
        'motorAEnabled': motor_positions.get('motorAEnabled', True),  # Motor enable state
        'motorBEnabled': motor_positions.get('motorBEnabled', True)
    }
    return save_setups(setups)

def load_setup(setup_name):
    """Load a saved setup into current motor positions"""
    global motor_positions
    setups = load_setups()
    if setup_name in setups:
        setup = setups[setup_name]
        motor_positions['homeA'] = setup.get('homeA', 0)
        motor_positions['homeB'] = setup.get('homeB', 0)
        motor_positions['dipA'] = setup.get('dipA')
        motor_positions['dipB'] = setup.get('dipB')
        motor_positions['closeA'] = setup.get('closeA')
        motor_positions['closeB'] = setup.get('closeB')
        motor_positions['motorA'] = setup.get('motorA', 0)
        motor_positions['motorB'] = setup.get('motorB', 0)
        motor_positions['motorAEnabled'] = setup.get('motorAEnabled', True)  # Load enable state
        motor_positions['motorBEnabled'] = setup.get('motorBEnabled', True)
        save_motor_positions()  # Save to motor_positions.json
        logger.info("Loaded setup '{}': Motor A enabled: {}, Motor B enabled: {}".format(
            setup_name, motor_positions['motorAEnabled'], motor_positions['motorBEnabled']))
        return True
    return False

def delete_setup(setup_name):
    """Delete a saved setup"""
    setups = load_setups()
    if setup_name in setups:
        del setups[setup_name]
        return save_setups(setups)
    return False

# Fan PWM mapping for 4-pin PWM fan: direct 0-100% duty cycle
# 4-pin PWM fans use the PWM signal (pin 4) for speed control, not power modulation
# They respond to 0-100% duty cycle directly (no need for 1-21% mapping)
def map_fan_speed(slider_percent):
    """Map slider percentage (0-100) to PWM duty cycle (0-100%) for 4-pin PWM fan"""
    if slider_percent <= 0:
        return 0.0
    # Direct mapping: 0-100% slider to 0-100% PWM duty cycle
    return min(100.0, max(0.0, slider_percent))

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
            # Use 25kHz for 4-pin PWM fans (standard PWM frequency)
            # Note: RPi.GPIO software PWM may not achieve true 25kHz, but will try to get as close as possible
            # GPIO 18 supports hardware PWM, but RPi.GPIO uses software PWM
            # If fan doesn't respond well, consider using pigpio library for true hardware PWM
            # For now, using 1kHz as a compromise (many 4-pin PWM fans will accept this)
            # You can try higher frequencies like 5000 (5kHz) if 1kHz doesn't work well
            fan_pwm = GPIO.PWM(PINS['pwmFan'], 1000)  # 1kHz (try 5000 for 5kHz if needed)
            fan_pwm.start(0)
            logger.info("Fan PWM initialized at 1kHz for 4-pin PWM fan (GPIO pin {})".format(PINS['pwmFan']))
        gpio_initialized = True
        logger.info("GPIO initialized")
    except Exception as e:
        logger.error("GPIO init error: {}".format(e))

def move_motor(motor, steps, direction):
    """Move a single motor by specified steps in given direction"""
    global motor_positions
    import time
    
    if motor not in ['A', 'B']:
        return False
    
    # Check if motor is enabled
    motor_enabled_key = 'motorAEnabled' if motor == 'A' else 'motorBEnabled'
    if not motor_positions.get(motor_enabled_key, True):
        logger.warning("Motor {} is disabled, skipping movement".format(motor))
        return False
    
    init_gpio()
    
    step_pin = PINS['stepA'] if motor == 'A' else PINS['stepB']
    dir_pin = PINS['dirA'] if motor == 'A' else PINS['dirB']
    
    # Set direction: HIGH = one direction, LOW = other
    GPIO.output(dir_pin, GPIO.HIGH if direction == 'forward' else GPIO.LOW)
    
    # Move motor with gentler speed
    step_delay = GLOBAL_CONFIG.get('baseStepDelay', 0.002)
    for _ in range(abs(steps)):
        GPIO.output(step_pin, GPIO.HIGH)
        time.sleep(step_delay)
        GPIO.output(step_pin, GPIO.LOW)
        time.sleep(step_delay)
    
    # Update position tracking
    position_key = 'motorA' if motor == 'A' else 'motorB'
    if direction == 'forward':
        motor_positions[position_key] += steps
    else:
        motor_positions[position_key] -= steps
    
    # Save position after trimming to maintain accuracy across restarts
    save_motor_positions()
    
    logger.info("Motor {} moved {} steps {}, new position: {}".format(motor, steps, direction, motor_positions[position_key]))
    return True

def move_to_position(target_a, target_b, position_name, use_slow_in=False, speed_multiplier=1.0, base_step_delay=None, slow_in_steps_value=None, ramp_up_steps_value=None):
    """Move both motors to a target position with optional ramp-up acceleration, slow-in deceleration and speed multiplier"""
    global motor_positions, current_arm_position
    import time
    
    init_gpio()
    
    # Calculate steps needed to reach target position
    steps_a = target_a - motor_positions['motorA']
    steps_b = target_b - motor_positions['motorB']
    
    # Set directions
    dir_a = GPIO.LOW if steps_a < 0 else GPIO.HIGH  # LOW = backward, HIGH = forward
    dir_b = GPIO.HIGH if steps_b > 0 else GPIO.LOW  # HIGH = forward, LOW = backward
    
    GPIO.output(PINS['dirA'], dir_a)
    GPIO.output(PINS['dirB'], dir_b)
    
    steps_a = abs(steps_a)
    steps_b = abs(steps_b)
    max_steps = max(steps_a, steps_b)
    
    # Use provided values or fall back to global config
    if base_step_delay is None:
        base_step_delay = GLOBAL_CONFIG.get('baseStepDelay', 0.002)
    if slow_in_steps_value is None:
        slow_in_steps_value = GLOBAL_CONFIG.get('slowInSteps', 150) if use_slow_in else 0
    else:
        slow_in_steps_value = slow_in_steps_value if use_slow_in else 0
    if ramp_up_steps_value is None:
        ramp_up_steps_value = 0
    
    # Ramp-up configuration - acceleration at start
    ramp_up_end = min(ramp_up_steps_value, max_steps) if ramp_up_steps_value > 0 else 0
    
    # Slow-in configuration - deceleration at end
    # Ensure slow-in doesn't overlap with ramp-up
    if slow_in_steps_value > 0:
        slow_in_start = max(ramp_up_end, max_steps - slow_in_steps_value)
        # If they would overlap, reduce slow-in to fit
        if slow_in_start < ramp_up_end:
            slow_in_steps_value = max(0, max_steps - ramp_up_end)
            slow_in_start = ramp_up_end if slow_in_steps_value > 0 else max_steps
    else:
        slow_in_start = max_steps
    
    # Base step delay (gentler overall movement) - divided by speed multiplier for faster movement
    base_delay = base_step_delay / speed_multiplier
    # Maximum delay at start (for ramp-up) and end (for slow-in) - also affected by speed multiplier
    max_delay_start = 0.015 / speed_multiplier  # Start slow for ramp-up
    max_delay_end = 0.015 / speed_multiplier  # End slow for slow-in
    
    # Move both motors simultaneously with ramp-up and slow-in
    for i in range(max_steps):
        # Calculate delay with ramp-up and slow-in curves
        if ramp_up_steps_value > 0 and i < ramp_up_end:
            # Ramp-up: gradually decrease delay as we accelerate from start
            progress = float(i) / ramp_up_steps_value if ramp_up_steps_value > 0 else 0
            # Cubic easing for smooth acceleration
            eased = progress * progress * progress
            # Also add a linear component for smoother transition
            eased = (eased * 0.7) + (progress * 0.3)
            delay = max_delay_start - (max_delay_start - base_delay) * eased
        elif use_slow_in and slow_in_steps_value > 0 and i >= slow_in_start:
            # Slow-in: gradually increase delay as we approach target
            progress = float(i - slow_in_start) / slow_in_steps_value if slow_in_steps_value > 0 else 0
            # Cubic easing for even smoother, gentler deceleration
            eased = progress * progress * progress
            # Also add a linear component for smoother transition
            eased = (eased * 0.7) + (progress * 0.3)
            delay = base_delay + (max_delay_end - base_delay) * eased
        else:
            delay = base_delay
        
        # Only step motors that are enabled
        if motor_positions.get('motorAEnabled', True) and i < steps_a:
            GPIO.output(PINS['stepA'], GPIO.HIGH)
        if motor_positions.get('motorBEnabled', True) and i < steps_b:
            GPIO.output(PINS['stepB'], GPIO.HIGH)
        time.sleep(delay)
        if motor_positions.get('motorAEnabled', True):
            GPIO.output(PINS['stepA'], GPIO.LOW)
        if motor_positions.get('motorBEnabled', True):
            GPIO.output(PINS['stepB'], GPIO.LOW)
        time.sleep(delay)
    
    # Update positions (only for enabled motors, disabled motors keep their position)
    if motor_positions.get('motorAEnabled', True):
        motor_positions['motorA'] = target_a
    if motor_positions.get('motorBEnabled', True):
        motor_positions['motorB'] = target_b
    current_arm_position = position_name
    
    # Save current position after every move to maintain accuracy across restarts
    save_motor_positions()
    
    ramp_up_info = "ramp-up: {} steps".format(ramp_up_steps_value) if ramp_up_steps_value > 0 else "no ramp-up"
    slow_in_info = "slow-in: {} steps".format(slow_in_steps_value) if use_slow_in and slow_in_steps_value > 0 else "no slow-in"
    logger.info("Motors moved to {} position. Motor A: {}, Motor B: {} ({}, {})".format(
        position_name, target_a, target_b, ramp_up_info, slow_in_info))
    return True

def return_to_home():
    """Return both motors to HOME position (OPEN arms position) - uses saved absolute position with slow-in"""
    # HOME/OPEN is always 0,0 - use saved HOME position
    target_a = motor_positions.get('homeA', 0)
    target_b = motor_positions.get('homeB', 0)
    # Use DIP to OPEN settings for returning to home
    base_delay = GLOBAL_CONFIG.get('dipToOpenSpeed', 0.002)
    ramp_up = GLOBAL_CONFIG.get('dipToOpenRampUp', 0)
    slow_in = GLOBAL_CONFIG.get('dipToOpenSlowIn', 150)
    use_slow = slow_in > 0
    return move_to_position(target_a, target_b, 'OPEN', use_slow_in=use_slow, base_step_delay=base_delay, slow_in_steps_value=slow_in, ramp_up_steps_value=ramp_up)

def return_to_dip():
    """Return both motors to saved DIP position"""
    # Use CLOSE to DIP settings (since we're coming from OPEN/CLOSE to DIP)
    base_delay = GLOBAL_CONFIG.get('closeToDipSpeed', 0.002)
    ramp_up = GLOBAL_CONFIG.get('closeToDipRampUp', 0)
    slow_in = GLOBAL_CONFIG.get('closeToDipSlowIn', 0)
    use_slow = slow_in > 0
    
    if motor_positions['dipA'] is None or motor_positions['dipB'] is None:
        logger.warning("DIP position not saved, using default")
        # Default DIP: calculate from HOME (OPEN) position which is 0,0
        home_a = motor_positions.get('homeA', 0)
        home_b = motor_positions.get('homeB', 0)
        target_a = home_a + 200  # Forward from HOME
        target_b = home_b - 200  # Backward from HOME
    else:
        target_a = motor_positions['dipA']
        target_b = motor_positions['dipB']
    return move_to_position(target_a, target_b, 'DIP', use_slow_in=use_slow, base_step_delay=base_delay, slow_in_steps_value=slow_in, ramp_up_steps_value=ramp_up)

def return_to_close():
    """Return both motors to saved CLOSE position"""
    # Use OPEN to CLOSE settings
    base_delay = GLOBAL_CONFIG.get('openToCloseSpeed', 0.001)
    ramp_up = GLOBAL_CONFIG.get('openToCloseRampUp', 0)
    slow_in = GLOBAL_CONFIG.get('openToCloseSlowIn', 0)
    use_slow = slow_in > 0
    
    if motor_positions['closeA'] is None or motor_positions['closeB'] is None:
        logger.warning("CLOSE position not saved, using default")
        # Default CLOSE: from OPEN, Motor A forward 400, Motor B backward 400
        target_a = -400 + 400  # 0
        target_b = 400 - 400   # 0
    else:
        target_a = motor_positions['closeA']
        target_b = motor_positions['closeB']
    return move_to_position(target_a, target_b, 'CLOSE', use_slow_in=use_slow, base_step_delay=base_delay, slow_in_steps_value=slow_in, ramp_up_steps_value=ramp_up)

def handle_request(conn, addr):
    global fan_running, fan_pwm
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
            conn.sendall(response)
            conn.close()
            return
        
        # Handle GET /health
        if method == 'GET' and parsed_path.path == '/health':
            response_data = json.dumps({
                'status': 'ok', 
                'pi': 'bubblebot', 
                'fan_running': fan_running, 
                'current_position': current_arm_position,
                'motor_positions': motor_positions
            })
            response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
            conn.sendall(response)
            # Health check - no log needed (too frequent)
            conn.close()
            return
        
        # Handle GET /get_motor_positions
        if method == 'GET' and parsed_path.path == '/get_motor_positions':
            response_data = json.dumps({
                'success': True,
                'positions': motor_positions
            })
            response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
            conn.sendall(response)
            conn.close()
            return
        
        # Handle GET /list_setups
        if method == 'GET' and parsed_path.path == '/list_setups':
            setups = load_setups()
            response_data = json.dumps({
                'success': True,
                'setups': setups
            })
            response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
            conn.sendall(response)
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
                global current_arm_position
                state_str = post_data.get('state', 'IDLE')
                is_sequence = post_data.get('isSequence', False)  # True if part of automatic sequence, False if manual
                logger.info("Received state: {} (current position: {}, isSequence: {})".format(state_str, current_arm_position, is_sequence))
                init_gpio()
                
                # Skip if already in this position (except BLOW which toggles)
                if state_str != 'BLOW' and state_str == current_arm_position:
                    logger.info("Already in {} position - skipping".format(state_str))
                    response_data = json.dumps({'success': True, 'state': state_str, 'fan_running': fan_running, 'skipped': True})
                    response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response)
                    conn.close()
                    return
                
                import time
                
                if state_str == 'IDLE':
                    GPIO.output(PINS['stepA'], GPIO.LOW)
                    GPIO.output(PINS['stepB'], GPIO.LOW)
                    # Stop fan and cancel any pending fan stop timer
                    global fan_stop_timer
                    if fan_stop_timer:
                        fan_stop_timer.cancel()
                        fan_stop_timer = None
                    if fan_pwm:
                        fan_pwm.ChangeDutyCycle(0)
                        fan_running = False
                    current_arm_position = 'IDLE'
                    logger.info("All systems stopped")
                
                elif state_str == 'DIP':
                    # Always use saved DIP position (absolute), or calculate default from HOME if not saved
                    # This is CLOSE to DIP movement - use closeToDipSpeed, closeToDipRampUp and closeToDipSlowIn
                    base_delay = GLOBAL_CONFIG.get('closeToDipSpeed', 0.002)
                    ramp_up = GLOBAL_CONFIG.get('closeToDipRampUp', 0)
                    slow_in = GLOBAL_CONFIG.get('closeToDipSlowIn', 0)
                    use_slow = slow_in > 0
                    
                    # Check if DIP position is saved (checking for None explicitly, 0 is a valid saved value)
                    if motor_positions.get('dipA') is not None and motor_positions.get('dipB') is not None:
                        # Move directly to saved absolute DIP position
                        target_a = motor_positions['dipA']
                        target_b = motor_positions['dipB']
                        logger.info("Moving to saved DIP position: Motor A: {}, Motor B: {}".format(target_a, target_b))
                    else:
                        # DIP position not saved - calculate default from HOME (OPEN) position
                        logger.warning("DIP position not saved, using default calculated from HOME")
                        home_a = motor_positions.get('homeA', 0)
                        home_b = motor_positions.get('homeB', 0)
                        target_a = home_a + 200  # Forward from HOME
                        target_b = home_b - 200  # Backward from HOME
                        logger.info("Using default DIP position: Motor A: {}, Motor B: {} (calculated from HOME: {},{})".format(target_a, target_b, home_a, home_b))
                    
                    move_to_position(target_a, target_b, 'DIP', 
                                   use_slow_in=use_slow, base_step_delay=base_delay, slow_in_steps_value=slow_in, ramp_up_steps_value=ramp_up)
                    
                    # DIP phase - no fan start here anymore, fan starts when DIP ends (in OPEN phase)
                
                elif state_str == 'OPEN':
                    # HOME = OPEN = 0,0 position
                    # This is DIP to OPEN movement - use dipToOpenSpeed, dipToOpenRampUp and dipToOpenSlowIn
                    base_delay = GLOBAL_CONFIG.get('dipToOpenSpeed', 0.002)
                    ramp_up = GLOBAL_CONFIG.get('dipToOpenRampUp', 0)
                    slow_in = GLOBAL_CONFIG.get('dipToOpenSlowIn', 150)
                    use_slow = slow_in > 0
                    
                    target_a = motor_positions.get('homeA', 0)
                    target_b = motor_positions.get('homeB', 0)
                    
                    # Start fan timer IMMEDIATELY when OPEN is received (DIP wait just ended)
                    # Only if this is part of the automatic sequence (not manual trigger)
                    if is_sequence:
                        fan_start_delay = GLOBAL_CONFIG.get('fanStartDelay', 0.0)  # Delay after DIP ends before fan starts
                        fan_duration = GLOBAL_CONFIG.get('fanDuration', 12.0)  # Total seconds fan should run
                        
                        def start_fan_after_delay():
                            global fan_running, fan_pwm, fan_stop_timer
                            if fan_pwm and not fan_running:
                                slider_speed = float(GLOBAL_CONFIG.get('fanSpeed', 100))
                                duty_cycle = map_fan_speed(slider_speed)
                                fan_pwm.ChangeDutyCycle(duty_cycle)
                                fan_running = True
                                logger.info("Fan started ({}s delay after DIP wait ended) at {}% PWM (slider: {}%)".format(fan_start_delay, duty_cycle, slider_speed))
                                
                                # Schedule fan to stop after fanDuration seconds (independent of arm movement)
                                def stop_fan_after_duration():
                                    global fan_running, fan_pwm
                                    if fan_pwm and fan_running:
                                        fan_pwm.ChangeDutyCycle(0)
                                        fan_running = False
                                        logger.info("Fan stopped after {} seconds (independent timer)".format(fan_duration))
                                
                                import threading
                                fan_stop_timer = threading.Timer(fan_duration, stop_fan_after_duration)
                                fan_stop_timer.start()
                                logger.info("Fan will run for {} seconds total (independent of arm movement)".format(fan_duration))
                        
                        # Start fan timer IMMEDIATELY (before movement starts) - counts from when DIP wait ended
                        import threading
                        timer = threading.Timer(fan_start_delay, start_fan_after_delay)
                        timer.start()
                        logger.info("Fan timer started - will start fan in {} seconds (counted from when DIP wait ended, not movement completion)".format(fan_start_delay))
                    
                    # Now start the movement (blocking - movement completes before response is sent)
                    move_to_position(target_a, target_b, 'OPEN', 
                                   use_slow_in=use_slow, base_step_delay=base_delay, slow_in_steps_value=slow_in, ramp_up_steps_value=ramp_up)
                    
                    # Movement is now complete - response will be sent, frontend can start OPEN wait timer
                
                elif state_str == 'BLOW' and fan_pwm:
                    if is_sequence:
                        # During sequence: ensure fan is running (it should already be running from DIP phase)
                        if not fan_running:
                            # Fan didn't start during DIP, start it now
                            slider_speed = float(GLOBAL_CONFIG.get('fanSpeed', 100))
                            duty_cycle = map_fan_speed(slider_speed)
                            fan_pwm.ChangeDutyCycle(duty_cycle)
                            fan_running = True
                            logger.info("Fan started during BLOW phase (sequence) at {}% PWM".format(duty_cycle))
                        else:
                            # Fan already running, ensure correct speed
                            slider_speed = float(GLOBAL_CONFIG.get('fanSpeed', 100))
                            duty_cycle = map_fan_speed(slider_speed)
                            fan_pwm.ChangeDutyCycle(duty_cycle)
                            logger.info("Fan running during BLOW phase (sequence) at {}% PWM".format(duty_cycle))
                    else:
                        # Manual trigger: toggle fan
                        if fan_running:
                            # Stop fan (manual toggle)
                            fan_pwm.ChangeDutyCycle(0)
                            fan_running = False
                            logger.info("Fan stopped (manual toggle)")
                        else:
                            # Start fan
                            slider_speed = float(GLOBAL_CONFIG.get('fanSpeed', 100))
                            duty_cycle = map_fan_speed(slider_speed)
                            fan_pwm.ChangeDutyCycle(duty_cycle)
                            fan_running = True
                            logger.info("Fan started (manual toggle) at {}% PWM (slider: {}%)".format(duty_cycle, slider_speed))
                
                elif state_str == 'CLOSE':
                    # Always use saved CLOSE position (absolute), or default if not saved
                    # This is OPEN to CLOSE movement - use openToCloseSpeed, openToCloseRampUp and openToCloseSlowIn
                    base_delay = GLOBAL_CONFIG.get('openToCloseSpeed', 0.001)
                    ramp_up = GLOBAL_CONFIG.get('openToCloseRampUp', 0)
                    slow_in = GLOBAL_CONFIG.get('openToCloseSlowIn', 0)
                    use_slow = slow_in > 0
                    
                    # Fan continues running (stopped by independent timer, not by arm movement)
                    if motor_positions['closeA'] is not None and motor_positions['closeB'] is not None:
                        # Move directly to saved absolute CLOSE position
                        move_to_position(motor_positions['closeA'], motor_positions['closeB'], 'CLOSE', 
                                       use_slow_in=use_slow, base_step_delay=base_delay, slow_in_steps_value=slow_in, ramp_up_steps_value=ramp_up)
                    else:
                        # Default: calculate from HOME (OPEN) position
                        # Default CLOSE: from OPEN, Motor A forward 400, Motor B backward 400
                        target_a = -400 + 400  # 0
                        target_b = 400 - 400   # 0
                        move_to_position(target_a, target_b, 'CLOSE', 
                                       use_slow_in=use_slow, base_step_delay=base_delay, slow_in_steps_value=slow_in, ramp_up_steps_value=ramp_up)
                    # Fan continues running - it will stop based on independent fanDuration timer
                    logger.info("Arms closing - fan continues running (stopped by independent timer)")
                
                # Response sent AFTER movement completes - frontend can start wait timer
                response_data = json.dumps({'success': True, 'state': state_str, 'fan_running': fan_running, 'current_position': current_arm_position, 'movement_complete': True})
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/update_config':
                logger.info("Received config update: {}".format(post_data))
                # Map old property names to new names for backward compatibility
                config_update = dict(post_data)
                if 'dipDuration' in config_update:
                    config_update['dipWait'] = config_update.pop('dipDuration')
                if 'liftDuration' in config_update:
                    config_update['openWait'] = config_update.pop('liftDuration')
                if 'closeDuration' in config_update:
                    config_update['closeWait'] = config_update.pop('closeDuration')
                if 'fanEarlyStart' in config_update:
                    config_update['fanStartDelay'] = config_update.pop('fanEarlyStart')
                GLOBAL_CONFIG.update(config_update)
                if fan_pwm and fan_running and 'fanSpeed' in config_update:
                    try:
                        slider_speed = float(GLOBAL_CONFIG['fanSpeed'])
                        duty_cycle = map_fan_speed(slider_speed)
                        fan_pwm.ChangeDutyCycle(duty_cycle)
                        logger.info("Fan speed updated to {}% PWM (slider: {}%)".format(duty_cycle, slider_speed))
                    except Exception as e:
                        logger.error("Failed to update fan speed: {}".format(e))
                
                response_data = json.dumps({'success': True, 'config': GLOBAL_CONFIG})
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/trim_motor':
                # Move individual motor for trimming
                motor = post_data.get('motor', '').upper()  # 'A' or 'B'
                steps = int(post_data.get('steps', 10))
                direction = post_data.get('direction', 'forward')  # 'forward' or 'backward'
                
                if motor not in ['A', 'B']:
                    response_data = json.dumps({'success': False, 'error': 'Invalid motor. Use "A" or "B"'})
                    response = "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response)
                    conn.close()
                    return
                
                success = move_motor(motor, steps, direction)
                response_data = json.dumps({
                    'success': success,
                    'motor': motor,
                    'positions': motor_positions
                })
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/save_home':
                # Save current position as HOME (OPEN position) - absolute values, independent of other positions
                motor_positions['homeA'] = motor_positions['motorA']  # Save absolute position
                motor_positions['homeB'] = motor_positions['motorB']  # Save absolute position
                # Note: This does NOT affect dipA/dipB/closeA/closeB - each position is independent
                
                saved = save_motor_positions()
                response_data = json.dumps({
                    'success': saved,
                    'message': 'HOME position saved (OPEN arms position)' if saved else 'Failed to save',
                    'positions': motor_positions
                })
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/save_dip':
                # Save current position as DIP position - absolute values, independent of other positions
                motor_positions['dipA'] = motor_positions['motorA']  # Save absolute position
                motor_positions['dipB'] = motor_positions['motorB']  # Save absolute position
                # Note: This does NOT affect homeA/homeB/closeA/closeB - each position is independent
                
                saved = save_motor_positions()
                response_data = json.dumps({
                    'success': saved,
                    'message': 'DIP position saved (absolute)' if saved else 'Failed to save',
                    'positions': motor_positions
                })
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/save_close':
                # Save current position as CLOSE position - absolute values, independent of other positions
                motor_positions['closeA'] = motor_positions['motorA']  # Save absolute position
                motor_positions['closeB'] = motor_positions['motorB']  # Save absolute position
                # Note: This does NOT affect homeA/homeB/dipA/dipB - each position is independent
                
                saved = save_motor_positions()
                response_data = json.dumps({
                    'success': saved,
                    'message': 'CLOSE position saved (absolute)' if saved else 'Failed to save',
                    'positions': motor_positions
                })
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/return_home':
                # Return motors to saved home position
                success = return_to_home()
                response_data = json.dumps({
                    'success': success,
                    'positions': motor_positions
                })
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/return_dip':
                # Return motors to saved DIP position
                success = return_to_dip()
                response_data = json.dumps({
                    'success': success,
                    'positions': motor_positions
                })
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/return_close':
                # Return motors to saved CLOSE position
                success = return_to_close()
                response_data = json.dumps({
                    'success': success,
                    'positions': motor_positions
                })
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/reset_motor_positions':
                # Reset current motor positions to 0,0 (for physical alignment)
                # This sets the software position to match physical position after manual alignment
                # 0,0 = HOME = OPEN position
                motor_positions['motorA'] = 0
                motor_positions['motorB'] = 0
                motor_positions['homeA'] = 0  # HOME/OPEN is 0,0
                motor_positions['homeB'] = 0   # HOME/OPEN is 0,0
                current_arm_position = 'IDLE'
                saved = save_motor_positions()
                logger.info("Motor positions reset to 0,0 (HOME/OPEN position) - ready for physical alignment")
                response_data = json.dumps({
                    'success': saved,
                    'message': 'Motor positions reset to 0,0 - align motors physically to this position' if saved else 'Failed to save',
                    'positions': motor_positions
                })
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/get_motor_positions':
                # Get current motor positions
                response_data = json.dumps({
                    'success': True,
                    'positions': motor_positions
                })
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/save_setup':
                # Save current motor positions as a named setup
                setup_name = post_data.get('name', '').strip()
                if not setup_name:
                    response_data = json.dumps({'success': False, 'error': 'Setup name required'})
                    response = "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response)
                    conn.close()
                    return
                
                success = save_current_setup(setup_name)
                response_data = json.dumps({
                    'success': success,
                    'message': 'Setup "{}" saved'.format(setup_name) if success else 'Failed to save setup',
                    'setups': load_setups()
                })
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/load_setup':
                # Load a saved setup
                setup_name = post_data.get('name', '').strip()
                if not setup_name:
                    response_data = json.dumps({'success': False, 'error': 'Setup name required'})
                    response = "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response)
                    conn.close()
                    return
                
                success = load_setup(setup_name)
                response_data = json.dumps({
                    'success': success,
                    'message': 'Setup "{}" loaded'.format(setup_name) if success else 'Setup "{}" not found'.format(setup_name),
                    'positions': motor_positions
                })
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/delete_setup':
                # Delete a saved setup
                setup_name = post_data.get('name', '').strip()
                if not setup_name:
                    response_data = json.dumps({'success': False, 'error': 'Setup name required'})
                    response = "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response)
                    conn.close()
                    return
                
                success = delete_setup(setup_name)
                response_data = json.dumps({
                    'success': success,
                    'message': 'Setup "{}" deleted'.format(setup_name) if success else 'Setup "{}" not found'.format(setup_name),
                    'setups': load_setups()
                })
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/set_motor_enabled':
                # Enable/disable a motor
                motor = post_data.get('motor', '').upper()  # 'A' or 'B'
                enabled = post_data.get('enabled', True)
                
                if motor not in ['A', 'B']:
                    response_data = json.dumps({'success': False, 'error': 'Invalid motor. Use "A" or "B"'})
                    response = "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response)
                    conn.close()
                    return
                
                motor_enabled_key = 'motorAEnabled' if motor == 'A' else 'motorBEnabled'
                motor_positions[motor_enabled_key] = bool(enabled)
                save_motor_positions()
                
                logger.info("Motor {} {}abled".format(motor, "en" if enabled else "dis"))
                response_data = json.dumps({
                    'success': True,
                    'motor': motor,
                    'enabled': enabled,
                    'positions': motor_positions
                })
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/upload_server':
                # Receive server code and save it
                server_code = post_data.get('code', '')
                if server_code:
                    try:
                        import os
                        # Determine the current script's directory
                        script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
                        # Try common locations
                        possible_paths = [
                            os.path.join(os.path.expanduser('~'), 'server.py'),  # Home directory
                            '/home/pi/server.py',  # Pi home
                            'server.py',  # Current directory
                            os.path.join(script_dir, 'server.py')  # Script directory
                        ]
                        
                        saved = False
                        for save_path in possible_paths:
                            try:
                                # Save to a temporary file first, then replace (atomic operation)
                                temp_file = save_path + '.tmp'
                                with open(temp_file, 'w') as f:
                                    f.write(server_code)
                                # Try to move (atomic)
                                import shutil
                                shutil.move(temp_file, save_path)
                                logger.info("Server code updated successfully at: {}".format(save_path))
                                saved = True
                                break
                            except (IOError, OSError):
                                continue
                        
                        if not saved:
                            # Fallback: save to current directory
                            with open('server.py', 'w') as f:
                                f.write(server_code)
                            logger.info("Server code saved to current directory")
                        
                        response_data = json.dumps({'success': True, 'message': 'Server code updated. Restart required.'})
                        response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                        conn.sendall(response)
                        conn.close()
                        return
                    except Exception as e:
                        logger.error("Failed to save server code: {}".format(e))
                        response_data = json.dumps({'success': False, 'error': str(e)})
                        response = "HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                        conn.sendall(response)
                        conn.close()
                        return
                else:
                    response_data = json.dumps({'success': False, 'error': 'No code provided'})
                    response = "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                    conn.sendall(response)
                    conn.close()
                    return
        
        # 404
        response = "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n"
        conn.sendall(response)
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
            # Connection log removed to reduce clutter
            # Handle each request in the same thread (simple, works for low traffic)
            handle_request(conn, addr)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if fan_pwm:
            fan_pwm.stop()
        GPIO.cleanup()
        s.close()

if __name__ == '__main__':
    run_server()

