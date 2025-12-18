#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BubbleBot Raspberry Pi Server (Python 2.7 Compatible)
Controls stepper motors, fan, and smoke machine via HTTP API
Uses only standard library - no Flask required
"""

import RPi.GPIO as GPIO
import time
import logging
import json
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from urlparse import urlparse, parse_qs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global configuration
GLOBAL_CONFIG = {
    'dipDuration': 5.0,
    'liftDuration': 4.0,
    'blowDuration': 3.0,
    'closeDuration': 1.5,
    'fanSpeed': 100,
    'fanEnabled': True
}

# Pin configuration
PINS = {
    'stepA': 17,
    'dirA': 27,
    'stepB': 22,
    'dirB': 23,
    'pwmFan': 18,
    'dmxChannel': 1
}

# Machine states
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
        self.setup_gpio()
        
    def setup_gpio(self):
        """Initialize GPIO pins"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Motor A pins
            GPIO.setup(PINS['stepA'], GPIO.OUT)
            GPIO.setup(PINS['dirA'], GPIO.OUT)
            
            # Motor B pins
            GPIO.setup(PINS['stepB'], GPIO.OUT)
            GPIO.setup(PINS['dirB'], GPIO.OUT)
            
            # Fan PWM
            if GLOBAL_CONFIG['fanEnabled']:
                GPIO.setup(PINS['pwmFan'], GPIO.OUT)
                self.fan_pwm = GPIO.PWM(PINS['pwmFan'], 1000)
                self.fan_pwm.start(0)
                logger.info("Fan PWM initialized on pin {}".format(PINS['pwmFan']))
            else:
                logger.info("Fan disabled - skipping PWM setup")
                
            logger.info("GPIO pins initialized successfully")
        except Exception as e:
            logger.error("GPIO setup error: {}".format(e))
    
    def set_state(self, state):
        """Set machine state and control hardware accordingly"""
        self.current_state = state
        logger.info("State changed to: {}".format(state))
        
        try:
            if state == 'IDLE':
                self.stop_all()
            elif state == 'DIP':
                self.dip_sequence()
            elif state == 'OPEN':
                self.open_arms()
            elif state == 'BLOW':
                self.blow_sequence()
            elif state == 'CLOSE':
                self.close_arms()
        except Exception as e:
            logger.error("Error in set_state: {}".format(e))
    
    def dip_sequence(self):
        """Lower arms into soap"""
        try:
            GPIO.output(PINS['dirA'], GPIO.HIGH)
            GPIO.output(PINS['dirB'], GPIO.LOW)
            
            steps = 200
            for _ in range(steps):
                GPIO.output(PINS['stepA'], GPIO.HIGH)
                GPIO.output(PINS['stepB'], GPIO.HIGH)
                time.sleep(0.001)
                GPIO.output(PINS['stepA'], GPIO.LOW)
                GPIO.output(PINS['stepB'], GPIO.LOW)
                time.sleep(0.001)
            
            logger.info("Dip sequence completed")
        except Exception as e:
            logger.error("Dip sequence error: {}".format(e))
    
    def open_arms(self):
        """Open arms to blow position"""
        try:
            GPIO.output(PINS['dirA'], GPIO.LOW)
            GPIO.output(PINS['dirB'], GPIO.HIGH)
            
            steps = 400
            for _ in range(steps):
                GPIO.output(PINS['stepA'], GPIO.HIGH)
                GPIO.output(PINS['stepB'], GPIO.HIGH)
                time.sleep(0.001)
                GPIO.output(PINS['stepA'], GPIO.LOW)
                GPIO.output(PINS['stepB'], GPIO.LOW)
                time.sleep(0.001)
            
            logger.info("Arms opened")
        except Exception as e:
            logger.error("Open arms error: {}".format(e))
    
    def blow_sequence(self):
        """Activate fan for blowing bubbles"""
        try:
            if GLOBAL_CONFIG['fanEnabled']:
                fan_speed = GLOBAL_CONFIG['fanSpeed']
                self.fan_pwm.ChangeDutyCycle(fan_speed)
                logger.info("Fan started at {}%".format(fan_speed))
            else:
                logger.info("Fan disabled - skipping")
        except Exception as e:
            logger.error("Blow sequence error: {}".format(e))
    
    def close_arms(self):
        """Close arms back to start position"""
        try:
            GPIO.output(PINS['dirA'], GPIO.HIGH)
            GPIO.output(PINS['dirB'], GPIO.LOW)
            
            steps = 400
            for _ in range(steps):
                GPIO.output(PINS['stepA'], GPIO.HIGH)
                GPIO.output(PINS['stepB'], GPIO.HIGH)
                time.sleep(0.001)
                GPIO.output(PINS['stepA'], GPIO.LOW)
                GPIO.output(PINS['stepB'], GPIO.LOW)
                time.sleep(0.001)
            
            if GLOBAL_CONFIG['fanEnabled']:
                try:
                    self.fan_pwm.ChangeDutyCycle(0)
                    logger.info("Fan stopped")
                except:
                    pass
            
            logger.info("Arms closed")
        except Exception as e:
            logger.error("Close arms error: {}".format(e))
    
    def stop_all(self):
        """Stop all motors and fan"""
        try:
            GPIO.output(PINS['stepA'], GPIO.LOW)
            GPIO.output(PINS['stepB'], GPIO.LOW)
            
            if GLOBAL_CONFIG['fanEnabled']:
                try:
                    self.fan_pwm.ChangeDutyCycle(0)
                except:
                    pass
            
            logger.info("All systems stopped")
        except Exception as e:
            logger.error("Stop all error: {}".format(e))
    
    def cleanup(self):
        """Cleanup GPIO on shutdown"""
        try:
            if GLOBAL_CONFIG['fanEnabled']:
                self.fan_pwm.stop()
            GPIO.cleanup()
            logger.info("GPIO cleaned up")
        except Exception as e:
            logger.error("Cleanup error: {}".format(e))

# Initialize motor controller
motor_controller = MotorController()

class BubbleBotHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def send_cors_headers(self):
        """Send CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            response = json.dumps({'status': 'ok', 'pi': 'bubblebot'})
            self.wfile.write(response)
        else:
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        content_length = int(self.headers.getheader('content-length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data) if post_data else {}
        except:
            data = {}
        
        if parsed_path.path == '/set_state':
            try:
                state_str = data.get('state', 'IDLE')
                logger.info("Received state command: {}".format(state_str))
                
                if state_str in MACHINE_STATES:
                    motor_controller.set_state(state_str)
                    response = json.dumps({'success': True, 'state': state_str})
                    self.send_response(200)
                else:
                    response = json.dumps({'error': 'Invalid state'})
                    self.send_response(400)
                
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(response)
            except Exception as e:
                logger.error("set_state error: {}".format(e))
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}))
        
        elif parsed_path.path == '/update_config':
            try:
                logger.info("Received config update: {}".format(data))
                GLOBAL_CONFIG.update(data)
                
                if GLOBAL_CONFIG['fanEnabled'] and not hasattr(motor_controller, 'fan_pwm'):
                    try:
                        GPIO.setup(PINS['pwmFan'], GPIO.OUT)
                        motor_controller.fan_pwm = GPIO.PWM(PINS['pwmFan'], 1000)
                        motor_controller.fan_pwm.start(0)
                        logger.info("Fan PWM initialized after config update")
                    except Exception as e:
                        logger.error("Failed to initialize fan PWM: {}".format(e))
                
                response = json.dumps({'success': True, 'config': GLOBAL_CONFIG})
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(response)
            except Exception as e:
                logger.error("update_config error: {}".format(e))
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}))
        else:
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))

def run(server_class=HTTPServer, handler_class=BubbleBotHandler, port=5000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logger.info("Starting BubbleBot server on port {}...".format(port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        motor_controller.cleanup()
        httpd.server_close()

if __name__ == '__main__':
    run()

