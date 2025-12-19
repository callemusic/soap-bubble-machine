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
    'dipDuration': 5.0,
    'liftDuration': 4.0,
    'blowDuration': 3.0,
    'closeDuration': 1.5,
    'fanSpeed': 100,
    'fanEnabled': True
}

PINS = {'stepA': 17, 'dirA': 27, 'stepB': 22, 'dirB': 23, 'pwmFan': 18, 'dmxChannel': 1}
MACHINE_STATES = {'IDLE': 'IDLE', 'DIP': 'DIP', 'OPEN': 'OPEN', 'BLOW': 'BLOW', 'CLOSE': 'CLOSE', 'SMOKE_TEST': 'SMOKE_TEST'}

fan_running = False
fan_pwm = None
gpio_initialized = False
current_arm_position = 'IDLE'  # Track current arm position: IDLE, DIP, OPEN, CLOSE

# Motor position tracking (steps from home position)
motor_positions = {
    'motorA': 0,  # Current position relative to home
    'motorB': 0,
    'homeA': 0,   # Saved home position offset (OPEN)
    'homeB': 0,
    'dipA': None,  # Saved DIP position (Motor A, Motor B)
    'dipB': None,
    'closeA': None,  # Saved CLOSE position (Motor A, Motor B)
    'closeB': None
}

CONFIG_FILE = 'motor_positions.json'

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
    except Exception as e:
        logger.error("Failed to load motor positions: {}".format(e))

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

# Fan PWM mapping: slider 0-100% maps to effective PWM range 1-21%
# This accounts for the fan's actual response range
def map_fan_speed(slider_percent):
    """Map slider percentage (0-100) to effective PWM duty cycle (1-21%)"""
    if slider_percent <= 0:
        return 0.0
    # Map 0-100% slider to 1-21% PWM (the effective range)
    pwm_percent = 1.0 + (slider_percent / 100.0) * 20.0  # 1% to 21%
    return min(21.0, pwm_percent)

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
            # Use 100Hz - good for most fans via MOSFET
            # Some fans work better at 50Hz or 200Hz, but 100Hz is a good default
            fan_pwm = GPIO.PWM(PINS['pwmFan'], 100)  # 100Hz
            fan_pwm.start(0)
            logger.info("Fan PWM initialized at 100Hz")
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
    
    init_gpio()
    
    step_pin = PINS['stepA'] if motor == 'A' else PINS['stepB']
    dir_pin = PINS['dirA'] if motor == 'A' else PINS['dirB']
    
    # Set direction: HIGH = one direction, LOW = other
    GPIO.output(dir_pin, GPIO.HIGH if direction == 'forward' else GPIO.LOW)
    
    # Move motor
    for _ in range(abs(steps)):
        GPIO.output(step_pin, GPIO.HIGH)
        time.sleep(0.001)
        GPIO.output(step_pin, GPIO.LOW)
        time.sleep(0.001)
    
    # Update position tracking
    position_key = 'motorA' if motor == 'A' else 'motorB'
    if direction == 'forward':
        motor_positions[position_key] += steps
    else:
        motor_positions[position_key] -= steps
    
    logger.info("Motor {} moved {} steps {}, new position: {}".format(motor, steps, direction, motor_positions[position_key]))
    return True

def move_to_position(target_a, target_b, position_name):
    """Move both motors to a target position"""
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
    
    # Move both motors simultaneously
    for i in range(max_steps):
        if i < steps_a:
            GPIO.output(PINS['stepA'], GPIO.HIGH)
        if i < steps_b:
            GPIO.output(PINS['stepB'], GPIO.HIGH)
        time.sleep(0.001)
        GPIO.output(PINS['stepA'], GPIO.LOW)
        GPIO.output(PINS['stepB'], GPIO.LOW)
        time.sleep(0.001)
    
    # Update positions
    motor_positions['motorA'] = target_a
    motor_positions['motorB'] = target_b
    current_arm_position = position_name
    
    logger.info("Motors moved to {} position. Motor A: {}, Motor B: {}".format(position_name, target_a, target_b))
    return True

def return_to_home():
    """Return both motors to HOME position (OPEN arms position) - uses saved absolute position"""
    # Use saved HOME position if available, otherwise default
    if motor_positions['homeA'] != 0 or motor_positions['homeB'] != 0:
        target_a = motor_positions['homeA']
        target_b = motor_positions['homeB']
    else:
        # Default OPEN: Motor A backward (LOW) 400 steps, Motor B forward (HIGH) 400 steps
        target_a = -400
        target_b = 400
    return move_to_position(target_a, target_b, 'OPEN')

def return_to_dip():
    """Return both motors to saved DIP position"""
    if motor_positions['dipA'] is None or motor_positions['dipB'] is None:
        logger.warning("DIP position not saved, using default")
        # Default DIP: from OPEN, Motor A forward 200, Motor B backward 200
        target_a = -400 + 200  # -200
        target_b = 400 - 200   # 200
    else:
        target_a = motor_positions['dipA']
        target_b = motor_positions['dipB']
    return move_to_position(target_a, target_b, 'DIP')

def return_to_close():
    """Return both motors to saved CLOSE position"""
    if motor_positions['closeA'] is None or motor_positions['closeB'] is None:
        logger.warning("CLOSE position not saved, using default")
        # Default CLOSE: from OPEN, Motor A forward 400, Motor B backward 400
        target_a = -400 + 400  # 0
        target_b = 400 - 400   # 0
    else:
        target_a = motor_positions['closeA']
        target_b = motor_positions['closeB']
    return move_to_position(target_a, target_b, 'CLOSE')

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
            logger.info("Health check response sent")
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
                logger.info("Received state: {} (current position: {})".format(state_str, current_arm_position))
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
                    if fan_pwm:
                        fan_pwm.ChangeDutyCycle(0)
                        fan_running = False
                    current_arm_position = 'IDLE'
                    logger.info("All systems stopped")
                
                elif state_str == 'DIP':
                    # Always use saved DIP position (absolute), or default if not saved
                    if motor_positions['dipA'] is not None and motor_positions['dipB'] is not None:
                        # Move directly to saved absolute DIP position
                        move_to_position(motor_positions['dipA'], motor_positions['dipB'], 'DIP')
                    else:
                        # Default: calculate from HOME (OPEN) position
                        # Default DIP: from OPEN, Motor A forward 200, Motor B backward 200
                        target_a = -400 + 200  # -200
                        target_b = 400 - 200   # 200
                        move_to_position(target_a, target_b, 'DIP')
                
                elif state_str == 'OPEN':
                    # Always use saved HOME position (absolute), or default if not saved
                    # HOME = OPEN position
                    if motor_positions['homeA'] != 0 or motor_positions['homeB'] != 0:
                        # Use saved HOME position (absolute)
                        move_to_position(motor_positions['homeA'], motor_positions['homeB'], 'OPEN')
                    else:
                        # Default OPEN: Motor A backward 400, Motor B forward 400
                        target_a = -400
                        target_b = 400
                        move_to_position(target_a, target_b, 'OPEN')
                
                elif state_str == 'BLOW' and fan_pwm:
                    if fan_running:
                        fan_pwm.ChangeDutyCycle(0)
                        fan_running = False
                        logger.info("Fan stopped")
                    else:
                        # Map slider speed to effective PWM range
                        slider_speed = float(GLOBAL_CONFIG['fanSpeed'])
                        duty_cycle = map_fan_speed(slider_speed)
                        fan_pwm.ChangeDutyCycle(duty_cycle)
                        fan_running = True
                        logger.info("Fan started at {}% PWM (slider: {}%)".format(duty_cycle, slider_speed))
                
                elif state_str == 'CLOSE':
                    # Always use saved CLOSE position (absolute), or default if not saved
                    if motor_positions['closeA'] is not None and motor_positions['closeB'] is not None:
                        # Move directly to saved absolute CLOSE position
                        move_to_position(motor_positions['closeA'], motor_positions['closeB'], 'CLOSE')
                    else:
                        # Default: calculate from HOME (OPEN) position
                        # Default CLOSE: from OPEN, Motor A forward 400, Motor B backward 400
                        target_a = -400 + 400  # 0
                        target_b = 400 - 400   # 0
                        move_to_position(target_a, target_b, 'CLOSE')
                    # Stop fan when closing
                    if fan_pwm:
                        fan_pwm.ChangeDutyCycle(0)
                        fan_running = False
                
                response_data = json.dumps({'success': True, 'state': state_str, 'fan_running': fan_running, 'current_position': current_arm_position})
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/update_config':
                logger.info("Received config update: {}".format(post_data))
                GLOBAL_CONFIG.update(post_data)
                if fan_pwm and fan_running and 'fanSpeed' in post_data:
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
            logger.info("Connection from: {}".format(addr))
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

