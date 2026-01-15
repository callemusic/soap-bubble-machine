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
import time
from urlparse import urlparse

# Try to import MIDI support - try pygame first (Python 2 compatible), then mido (Python 3)
MIDI_AVAILABLE = False
MIDI_TYPE = None  # 'pygame' or 'mido'
pygame = None
mido = None

try:
    import pygame.midi
    pygame.midi.init()
    MIDI_AVAILABLE = True
    MIDI_TYPE = 'pygame'
    import pygame  # Import full pygame module for reference
except ImportError:
    try:
        import mido
        MIDI_AVAILABLE = True
        MIDI_TYPE = 'mido'
    except ImportError:
        MIDI_AVAILABLE = False
        MIDI_TYPE = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

GLOBAL_CONFIG = {
    'dipDuration': 5.0,
    'liftDuration': 4.0,
    'blowDuration': 3.0,
    'closeDuration': 1.5,
    'fanSpeed': 100,
    'fanEnabled': True,
    'smokeEnabled': False,
    'smokeIntensity': 120,  # MIDI CC value (0-127) - this worked with DOREMiDi!
    'smokeDuration': 3.0,
    'smokeMidiChannel': 0,  # MIDI Channel 0 (0-based) = Channel 1 (1-based) - matches test_midi_smoke.py
    'smokeMidiCC': 1
}

PINS = {'stepA': 17, 'dirA': 27, 'stepB': 22, 'dirB': 23, 'pwmFan': 18, 'dmxChannel': 1}
MACHINE_STATES = {'IDLE': 'IDLE', 'DIP': 'DIP', 'OPEN': 'OPEN', 'BLOW': 'BLOW', 'CLOSE': 'CLOSE', 'SMOKE_TEST': 'SMOKE_TEST'}

fan_running = False
fan_pwm = None
gpio_initialized = False
current_arm_position = 'IDLE'  # Track current arm position: IDLE, DIP, OPEN, CLOSE

# MIDI smoke control
midi_initialized = False
midi_port = None
smoke_running = False
smoke_stop_timer = None

# Fan PWM mapping: slider 0-100% maps to effective PWM range 1-21%
# This accounts for the fan's actual response range
def map_fan_speed(slider_percent):
    """Map slider percentage (0-100) to effective PWM duty cycle (1-21%)"""
    if slider_percent <= 0:
        return 0.0
    # Map 0-100% slider to 1-21% PWM (the effective range)
    pwm_percent = 1.0 + (slider_percent / 100.0) * 20.0  # 1% to 21%
    return min(21.0, pwm_percent)

def init_midi():
    """Initialize MIDI output port for smoke control"""
    global midi_initialized, midi_port
    
    if not MIDI_AVAILABLE:
        logger.warning("MIDI not available - cannot initialize smoke control")
        return False
    
    if midi_initialized and midi_port:
        return True
    
    try:
        if MIDI_TYPE == 'pygame':
            # Use pygame.midi (Python 2 compatible)
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
                
        elif MIDI_TYPE == 'mido':
            # Use mido (Python 3)
            ports = mido.get_output_names()
            midi_port_name = None
            
            for port in ports:
                if 'doremidi' in port.lower() or 'mtd' in port.lower():
                    midi_port_name = port
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
        channel = GLOBAL_CONFIG.get('smokeMidiChannel', 1)
        cc = GLOBAL_CONFIG.get('smokeMidiCC', 1)
        intensity = intensity if intensity is not None else GLOBAL_CONFIG.get('smokeIntensity', 120)
        duration = duration if duration is not None else GLOBAL_CONFIG.get('smokeDuration', 3.0)
        
        # Send MIDI CC message based on MIDI library type
        if MIDI_TYPE == 'pygame':
            # pygame.midi: status byte = 0xB0 + channel, then control, value
            midi_out = pygame.midi.Output(midi_port)
            status = 0xB0 + channel
            midi_out.write_short(status, cc, intensity)
            midi_out.close()
        elif MIDI_TYPE == 'mido':
            # mido: use Message class
            msg = mido.Message('control_change', channel=channel, control=cc, value=intensity)
            midi_port.send(msg)
        
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
        channel = GLOBAL_CONFIG.get('smokeMidiChannel', 1)
        cc = GLOBAL_CONFIG.get('smokeMidiCC', 1)
        
        # Send MIDI CC message with value 0
        if MIDI_TYPE == 'pygame':
            midi_out = pygame.midi.Output(midi_port)
            status = 0xB0 + channel
            midi_out.write_short(status, cc, 0)
            midi_out.close()
        elif MIDI_TYPE == 'mido':
            msg = mido.Message('control_change', channel=channel, control=cc, value=0)
            midi_port.send(msg)
        
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
            # Use 100Hz - good for most fans via MOSFET
            # Some fans work better at 50Hz or 200Hz, but 100Hz is a good default
            fan_pwm = GPIO.PWM(PINS['pwmFan'], 100)  # 100Hz
            fan_pwm.start(0)
            logger.info("Fan PWM initialized at 100Hz")
        gpio_initialized = True
        logger.info("GPIO initialized")
    except Exception as e:
        logger.error("GPIO init error: {}".format(e))

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
            health_data = {
                'status': 'ok',
                'pi': 'bubblebot',
                'fan_running': fan_running,
                'current_position': current_arm_position,
                'smoke_running': smoke_running,
                'midi_available': MIDI_AVAILABLE,
                'midi_initialized': midi_initialized
            }
            response_data = json.dumps(health_data)
            response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
            conn.sendall(response)
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
                    GPIO.output(PINS['dirA'], GPIO.HIGH)
                    GPIO.output(PINS['dirB'], GPIO.LOW)
                    for _ in range(200):
                        GPIO.output(PINS['stepA'], GPIO.HIGH)
                        GPIO.output(PINS['stepB'], GPIO.HIGH)
                        time.sleep(0.001)
                        GPIO.output(PINS['stepA'], GPIO.LOW)
                        GPIO.output(PINS['stepB'], GPIO.LOW)
                        time.sleep(0.001)
                    logger.info("Dip sequence completed")
                
                elif state_str == 'OPEN':
                    current_arm_position = 'OPEN'  # Set immediately to prevent double-clicks
                    GPIO.output(PINS['dirA'], GPIO.LOW)
                    GPIO.output(PINS['dirB'], GPIO.HIGH)
                    for _ in range(400):
                        GPIO.output(PINS['stepA'], GPIO.HIGH)
                        GPIO.output(PINS['stepB'], GPIO.HIGH)
                        time.sleep(0.001)
                        GPIO.output(PINS['stepA'], GPIO.LOW)
                        GPIO.output(PINS['stepB'], GPIO.LOW)
                        time.sleep(0.001)
                    logger.info("Arms opened")
                
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
                    current_arm_position = 'CLOSE'  # Set immediately to prevent double-clicks
                    GPIO.output(PINS['dirA'], GPIO.HIGH)
                    GPIO.output(PINS['dirB'], GPIO.LOW)
                    for _ in range(400):
                        GPIO.output(PINS['stepA'], GPIO.HIGH)
                        GPIO.output(PINS['stepB'], GPIO.HIGH)
                        time.sleep(0.001)
                        GPIO.output(PINS['stepA'], GPIO.LOW)
                        GPIO.output(PINS['stepB'], GPIO.LOW)
                        time.sleep(0.001)
                    if fan_pwm:
                        fan_pwm.ChangeDutyCycle(0)
                        fan_running = False
                    logger.info("Arms closed")
                
                response_data = json.dumps({'success': True, 'state': state_str, 'fan_running': fan_running, 'current_position': current_arm_position})
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/update_config' or parsed_path.path == '/set_config':
                logger.info("Received config update: {}".format(post_data))
                GLOBAL_CONFIG.update(post_data)
                
                # Update fan speed if running
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
        stop_smoke()
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

