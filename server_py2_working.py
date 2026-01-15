#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BubbleBot Raspberry Pi Server - Working Version
Based on test_server.py that works
"""

import RPi.GPIO as GPIO
import logging
import json
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
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

PINS = {
    'stepA': 17,
    'dirA': 27,
    'stepB': 22,
    'dirB': 23,
    'pwmFan': 18,
    'dmxChannel': 1
}

MACHINE_STATES = {
    'IDLE': 'IDLE',
    'DIP': 'DIP',
    'OPEN': 'OPEN',
    'BLOW': 'BLOW',
    'CLOSE': 'CLOSE',
    'SMOKE_TEST': 'SMOKE_TEST'
}

class MotorController:
    def __init__(self):
        self.current_state = 'IDLE'
        self.fan_running = False
        self.fan_pwm = None
        self.gpio_initialized = False
        # Don't initialize GPIO here - do it lazily on first use
        logger.info("MotorController created (GPIO will initialize on first use)")
    
    def setup_gpio(self):
        if self.gpio_initialized:
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
                self.fan_pwm = GPIO.PWM(PINS['pwmFan'], 100)
                self.fan_pwm.start(0)
                logger.info("Fan PWM initialized on pin {} at 100Hz".format(PINS['pwmFan']))
            self.gpio_initialized = True
            logger.info("GPIO pins initialized")
        except Exception as e:
            logger.error("GPIO setup error: {}".format(e))
            self.gpio_initialized = False
    
    def set_state(self, state):
        self.current_state = state
        logger.info("State changed to: {}".format(state))
        # Initialize GPIO on first use
        if not self.gpio_initialized:
            self.setup_gpio()
        try:
            if state == 'IDLE':
                if self.gpio_initialized:
                    GPIO.output(PINS['stepA'], GPIO.LOW)
                    GPIO.output(PINS['stepB'], GPIO.LOW)
                if self.fan_pwm:
                    self.fan_pwm.ChangeDutyCycle(0)
                    self.fan_running = False
            elif state == 'BLOW':
                if self.fan_pwm:
                    if self.fan_running:
                        self.fan_pwm.ChangeDutyCycle(0)
                        self.fan_running = False
                        logger.info("Fan stopped")
                    else:
                        self.fan_pwm.ChangeDutyCycle(GLOBAL_CONFIG['fanSpeed'])
                        self.fan_running = True
                        logger.info("Fan started at {}%".format(GLOBAL_CONFIG['fanSpeed']))
        except Exception as e:
            logger.error("Error in set_state: {}".format(e))
    
    def cleanup(self):
        try:
            if self.fan_pwm:
                self.fan_pwm.stop()
            GPIO.cleanup()
        except:
            pass

motor_controller = MotorController()

class BubbleBotHandler(BaseHTTPRequestHandler):
    def handle_one_request(self):
        """Override to catch broken pipe errors"""
        try:
            BaseHTTPRequestHandler.handle_one_request(self)
        except (IOError, OSError) as e:
            if e.errno == 32:  # Broken pipe
                pass  # Ignore - client closed connection
            else:
                raise
    
    def finish(self):
        """Override to suppress broken pipe errors"""
        try:
            BaseHTTPRequestHandler.finish(self)
        except (IOError, OSError) as e:
            if e.errno == 32:  # Broken pipe
                pass  # Ignore
            else:
                raise
    
    def do_GET(self):
        try:
            parsed_path = urlparse(self.path)
            if parsed_path.path == '/health':
                # Get fan_running safely without triggering GPIO init
                fan_running = getattr(motor_controller, 'fan_running', False)
                response = json.dumps({'status': 'ok', 'pi': 'bubblebot', 'fan_running': fan_running})
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Length', str(len(response)))
                self.end_headers()
                self.wfile.write(response)
                self.wfile.flush()  # Force flush
            else:
                self.send_response(404)
                self.end_headers()
        except (IOError, OSError) as e:
            if e.errno != 32:  # Only ignore broken pipe
                raise
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        content_length = int(self.headers.getheader('content-length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else ''
        
        try:
            data = json.loads(post_data) if post_data else {}
        except:
            data = {}
        
        if parsed_path.path == '/set_state':
            state_str = data.get('state', 'IDLE')
            logger.info("Received state: {}".format(state_str))
            if state_str in MACHINE_STATES:
                motor_controller.set_state(state_str)
                response = json.dumps({'success': True, 'state': state_str, 'fan_running': motor_controller.fan_running})
                self.send_response(200)
            else:
                response = json.dumps({'error': 'Invalid state'})
                self.send_response(400)
            
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response)
        
        elif parsed_path.path == '/update_config':
            logger.info("Received config update: {}".format(data))
            GLOBAL_CONFIG.update(data)
            if GLOBAL_CONFIG['fanEnabled'] and motor_controller.fan_pwm and motor_controller.fan_running:
                if 'fanSpeed' in data:
                    try:
                        motor_controller.fan_pwm.ChangeDutyCycle(float(GLOBAL_CONFIG['fanSpeed']))
                        logger.info("Fan speed updated to {}%".format(GLOBAL_CONFIG['fanSpeed']))
                    except:
                        pass
            
            response = json.dumps({'success': True, 'config': GLOBAL_CONFIG})
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response)
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        logger.info("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))

class SafeHTTPServer(HTTPServer):
    def handle_error(self, request, client_address):
        """Suppress broken pipe errors"""
        import sys
        exc_type, exc_value = sys.exc_info()[:2]
        if exc_type == IOError and exc_value.errno == 32:  # Broken pipe
            pass  # Ignore
        else:
            HTTPServer.handle_error(self, request, client_address)

def run(port=5000):
    server_address = ('', port)
    httpd = SafeHTTPServer(server_address, BubbleBotHandler)
    logger.info("Starting BubbleBot server on port {}...".format(port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        motor_controller.cleanup()
        httpd.server_close()

if __name__ == '__main__':
    run()

