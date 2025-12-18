#!/usr/bin/env python3
"""
BubbleBot Raspberry Pi Server
Controls stepper motors, fan, and smoke machine via Flask API
"""

import RPi.GPIO as GPIO
import time
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from enum import Enum

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
    'fanEnabled': True  # Set to True since fan is now connected
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

class MachineState(Enum):
    IDLE = 'IDLE'
    DIP = 'DIP'
    OPEN = 'OPEN'
    BLOW = 'BLOW'
    CLOSE = 'CLOSE'
    SMOKE_TEST = 'SMOKE_TEST'

class MotorController:
    def __init__(self):
        self.current_state = MachineState.IDLE
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
                self.fan_pwm = GPIO.PWM(PINS['pwmFan'], 1000)  # 1kHz frequency
                self.fan_pwm.start(0)
                logger.info("Fan PWM initialized on pin {}".format(PINS['pwmFan']))
            else:
                logger.info("Fan disabled - skipping PWM setup")
                
            logger.info("GPIO pins initialized successfully")
        except Exception as e:
            logger.error("GPIO setup error: {}".format(e))
    
    def set_state(self, state: MachineState):
        """Set machine state and control hardware accordingly"""
        self.current_state = state
        logger.info("State changed to: {}".format(state.value))
        
        try:
            if state == MachineState.IDLE:
                self.stop_all()
            elif state == MachineState.DIP:
                self.dip_sequence()
            elif state == MachineState.OPEN:
                self.open_arms()
            elif state == MachineState.BLOW:
                self.blow_sequence()
            elif state == MachineState.CLOSE:
                self.close_arms()
        except Exception as e:
            logger.error("Error in set_state: {}".format(e))
    
    def dip_sequence(self):
        """Lower arms into soap"""
        try:
            # Set direction for dipping
            GPIO.output(PINS['dirA'], GPIO.HIGH)
            GPIO.output(PINS['dirB'], GPIO.LOW)
            
            # Step motors
            steps = 200  # Adjust based on your motor/gearing
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
            
            steps = 400  # Adjust based on your setup
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
            
            # Stop fan when closing
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
            # Stop motors (they stop when step pins are low)
            GPIO.output(PINS['stepA'], GPIO.LOW)
            GPIO.output(PINS['stepB'], GPIO.LOW)
            
            # Stop fan
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

# Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for web dashboard

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'pi': 'bubblebot'
    })

@app.route('/set_state', methods=['POST'])
def set_state():
    """Set machine state"""
    try:
        data = request.get_json()
        state_str = data.get('state', 'IDLE')
        
        logger.info("Received state command: {}".format(state_str))
        
        state = MachineState[state_str]
        motor_controller.set_state(state)
        
        return jsonify({
            'success': True,
            'state': state.value
        })
    except KeyError:
        return jsonify({'error': 'Invalid state'}), 400
    except Exception as e:
        logger.error("set_state error: {}".format(e))
        return jsonify({'error': str(e)}), 500

@app.route('/update_config', methods=['POST'])
def update_config():
    """Update global configuration"""
    try:
        data = request.get_json()
        logger.info("Received config update: {}".format(data))
        
        # Update config
        GLOBAL_CONFIG.update(data)
        
        # If fan was just enabled, initialize PWM
        if GLOBAL_CONFIG['fanEnabled'] and not hasattr(motor_controller, 'fan_pwm'):
            try:
                GPIO.setup(PINS['pwmFan'], GPIO.OUT)
                motor_controller.fan_pwm = GPIO.PWM(PINS['pwmFan'], 1000)
                motor_controller.fan_pwm.start(0)
                logger.info("Fan PWM initialized after config update")
            except Exception as e:
                logger.error("Failed to initialize fan PWM: {}".format(e))
        
        return jsonify({
            'success': True,
            'config': GLOBAL_CONFIG
        })
    except Exception as e:
        logger.error("update_config error: {}".format(e))
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    try:
        logger.info("Starting BubbleBot server on port 5000...")
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        motor_controller.cleanup()

