#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BubbleBot Server - Final Working Version
Based on test_server.py that worked
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

PINS = {'stepA': 17, 'dirA': 27, 'stepB': 22, 'dirB': 23, 'pwmFan': 18, 'dmxChannel': 1}
MACHINE_STATES = {'IDLE': 'IDLE', 'DIP': 'DIP', 'OPEN': 'OPEN', 'BLOW': 'BLOW', 'CLOSE': 'CLOSE', 'SMOKE_TEST': 'SMOKE_TEST'}

# Simple global state - no class initialization blocking
fan_running = False
fan_pwm = None
gpio_initialized = False

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
            fan_pwm = GPIO.PWM(PINS['pwmFan'], 100)
            fan_pwm.start(0)
            logger.info("Fan PWM initialized")
        gpio_initialized = True
        logger.info("GPIO initialized")
    except Exception as e:
        logger.error("GPIO init error: {}".format(e))

class Handler(BaseHTTPRequestHandler):
    def handle_one_request(self):
        """Override to ensure response completes and suppress broken pipes"""
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
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/health':
            response = json.dumps({'status': 'ok', 'pi': 'bubblebot', 'fan_running': fan_running})
            # Send response directly without buffering
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            self.wfile.flush()  # Force immediate send
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        global fan_running, fan_pwm
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
                init_gpio()  # Initialize on first use
                if state_str == 'BLOW':
                    if fan_pwm:
                        if fan_running:
                            fan_pwm.ChangeDutyCycle(0)
                            fan_running = False
                        else:
                            fan_pwm.ChangeDutyCycle(GLOBAL_CONFIG['fanSpeed'])
                            fan_running = True
                response = json.dumps({'success': True, 'state': state_str, 'fan_running': fan_running})
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
            if fan_pwm and fan_running and 'fanSpeed' in data:
                try:
                    fan_pwm.ChangeDutyCycle(float(GLOBAL_CONFIG['fanSpeed']))
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
            pass  # Ignore broken pipe errors
        else:
            HTTPServer.handle_error(self, request, client_address)

if __name__ == '__main__':
    # Try port 8080 instead of 5000 - maybe 5000 is blocked
    port = 8080
    server = SafeHTTPServer(('', port), Handler)
    logger.info("Starting BubbleBot server on port {}...".format(port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if fan_pwm:
            fan_pwm.stop()
        GPIO.cleanup()
        server.server_close()

