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
            response_data = json.dumps({'status': 'ok', 'pi': 'bubblebot', 'fan_running': fan_running})
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
                state_str = post_data.get('state', 'IDLE')
                logger.info("Received state: {}".format(state_str))
                init_gpio()
                if state_str == 'BLOW' and fan_pwm:
                    if fan_running:
                        fan_pwm.ChangeDutyCycle(0)
                        fan_running = False
                    else:
                        fan_pwm.ChangeDutyCycle(GLOBAL_CONFIG['fanSpeed'])
                        fan_running = True
                
                response_data = json.dumps({'success': True, 'state': state_str, 'fan_running': fan_running})
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
                conn.sendall(response)
                conn.close()
                return
            
            elif parsed_path.path == '/update_config':
                logger.info("Received config update: {}".format(post_data))
                GLOBAL_CONFIG.update(post_data)
                if fan_pwm and fan_running and 'fanSpeed' in post_data:
                    try:
                        fan_pwm.ChangeDutyCycle(float(GLOBAL_CONFIG['fanSpeed']))
                    except:
                        pass
                
                response_data = json.dumps({'success': True, 'config': GLOBAL_CONFIG})
                response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}".format(len(response_data), response_data)
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





