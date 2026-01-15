#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple test server to verify HTTP connectivity works
"""

import RPi.GPIO as GPIO
import logging
import json
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from urlparse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global config
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
        self.setup_gpio()
    
    def setup_gpio(self):
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
            logger.info("GPIO pins initialized")
        except Exception as e:
            logger.error("GPIO setup error: {}".format(e))
    
    def set_state(self, state):
        self.current_state = state
        logger.info("State changed to: {}".format(state))
        try:
            if state == 'IDLE':
                GPIO.output(PINS['stepA'], GPIO.LOW)
                GPIO.output(PINS['stepB'], GPIO.LOW)
                if GLOBAL_CONFIG['fanEnabled']:
                    try:
                        self.fan_pwm.ChangeDutyCycle(0)
                        self.fan_running = False
                    except:
                        pass
            elif state == 'BLOW':
                if GLOBAL_CONFIG['fanEnabled']:
                    if self.fan_running:
                        self.fan_pwm.ChangeDutyCycle(0)
                        self.fan_running = False
                        logger.info("Fan stopped")
                    else:
                        fan_speed = GLOBAL_CONFIG['fanSpeed']
                        self.fan_pwm.ChangeDutyCycle(fan_speed)
                        self.fan_running = True
                        logger.info("Fan started at {}%".format(fan_speed))
        except Exception as e:
            logger.error("Error in set_state: {}".format(e))
    
    def cleanup(self):
        try:
            if GLOBAL_CONFIG['fanEnabled']:
                self.fan_pwm.stop()
            GPIO.cleanup()
        except:
            pass

motor_controller = MotorController()

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/health':
            response = json.dumps({'status': 'ok', 'pi': 'bubblebot', 'fan_running': motor_controller.fan_running})
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
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
            if GLOBAL_CONFIG['fanEnabled'] and hasattr(motor_controller, 'fan_pwm') and motor_controller.fan_running:
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

def run(port=5000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHandler)
    logger.info("Starting BubbleBot server on port {}...".format(port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        motor_controller.cleanup()
        httpd.server_close()

if __name__ == '__main__':
    run()





