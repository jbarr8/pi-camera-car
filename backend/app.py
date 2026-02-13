from gevent import monkey
monkey.patch_all(thread=False, threading=False)
from gpiozero import Motor

import signal
import sys
import atexit
import gpiozero as GPIO
from flask import Flask, send_file, request
from flask_socketio import SocketIO, emit, ConnectionRefusedError
from flask import render_template, request
import random
import string
from threading import Event

DEBUG = True

# Values below this do not provide enough power to move the car
# so anytime the throttle is activated, do not allow it to drop below this.
MIN_THROTTLE_VALUE = 40

# Anytime the throttle is activated, do not allow it to go above this.
MAX_THROTTLE_VALUE = 90

# A higher value results in more force being required to drive
DRIVE_SENSITIVITY = 200

# A higher value results in more force being required to steer
STEER_SENSITIVITY = 360

# Minimum allowed steer angle - any joystick value below this will be floored to this value
MIN_STEER_ANGLE = 61  # 0 to 180

# Maximum allowed steer angle - any joystick value above this will be ceilinged to this value
MAX_STEER_ANGLE = 110  # 0 to 180


app = Flask(__name__, static_folder="../frontend/dist/assets", template_folder="../frontend/dist")

led_pin = 10

NSLEEP1 = 12
AN11 = 17
AN12 = 27
BN11 = 22
BN12 = 23
NSLEEP2 = 13
AN21 = 24
AN22 = 25
BN21 = 26
BN22 = 16

servo_pin = 21

socketio = SocketIO(app, async_mode='gevent')

pwm = None
p1 = None
p2 = None
worker = None

thread_event = Event()

def cleanup():
  thread_event.clear()
  if DEBUG:
    print(f'cleanup')

atexit.register(cleanup)

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)

def cap_value(value, max_value):
	if value > max_value:
		value = max_value
	elif value < -max_value:
		value = -max_value
	return value

def generate_random_string(length):
	characters = string.ascii_letters + string.digits
	random_string = ''.join(random.choices(characters, k=length))
	return random_string


def process_latency_problem():
	# When there's a latency problem, stop all vehicle movement
	print('latency problem')
	GPIO.output(AN11,GPIO.LOW)
	GPIO.output(AN12,GPIO.LOW)
	GPIO.output(BN21,GPIO.LOW)
	GPIO.output(BN22,GPIO.LOW)
	pwm.ChangeDutyCycle(0)

def process_command(data):
	drive = None
	steer_angle = None
	device = data['device']
	
	if device == 'vehicle':
		if data['drive'] == None:
			GPIO.output(AN11,GPIO.LOW)
			GPIO.output(AN12,GPIO.LOW)
			GPIO.output(BN21,GPIO.LOW)
			GPIO.output(BN22,GPIO.LOW)
		else:
			# handle throttle
			drive = cap_value(data['drive'], DRIVE_SENSITIVITY)
			if drive > 0:
				# forward
				GPIO.output(AN11,GPIO.LOW)
				GPIO.output(AN12,GPIO.HIGH)
				GPIO.output(BN21,GPIO.LOW)
				GPIO.output(BN22,GPIO.HIGH)
			else:
				# reverse
				GPIO.output(AN11,GPIO.HIGH)
				GPIO.output(AN12,GPIO.LOW)
				GPIO.output(BN21,GPIO.HIGH)
				GPIO.output(BN22,GPIO.LOW)

			drive = round((abs(drive) / DRIVE_SENSITIVITY) * 90)
			if drive < MIN_THROTTLE_VALUE:
				# values below this cause the car to not move
				drive = MIN_THROTTLE_VALUE
			elif drive > MAX_THROTTLE_VALUE:
				drive = MAX_THROTTLE_VALUE
			p1.ChangeDutyCycle(drive)
			p2.ChangeDutyCycle(drive)

		if data['steer'] == None:
			pwm.ChangeDutyCycle(0)
		else:
			steer = -cap_value(data['steer'], STEER_SENSITIVITY)
			steer += STEER_SENSITIVITY
			steer_angle = round(steer / (STEER_SENSITIVITY * 2) * 180)
			if steer_angle < MIN_STEER_ANGLE:
				steer_angle = MIN_STEER_ANGLE
			elif steer_angle > MAX_STEER_ANGLE:
				steer_angle = MAX_STEER_ANGLE
			duty_cycle = steer_angle / 18 + 2
			pwm.ChangeDutyCycle(duty_cycle)

		if DEBUG:
			print(f'drive: {drive}, steer_angle: {steer_angle}')


@app.route("/")
def index():
	return render_template("index.html", require_auth=False)


@socketio.on('connect')
def connect():
	global pwm, p1, p2

	GPIO.setmode(GPIO.BCM)
	GPIO.setup(NSLEEP1,GPIO.OUT)
	GPIO.setup(NSLEEP2,GPIO.OUT)
	GPIO.setup(AN11,GPIO.OUT)
	GPIO.setup(AN12,GPIO.OUT)
	GPIO.setup(BN21,GPIO.OUT)
	GPIO.setup(BN22,GPIO.OUT)
	GPIO.setup(servo_pin, GPIO.OUT)
	GPIO.output(AN11,GPIO.LOW)
	GPIO.output(AN12,GPIO.LOW)
	GPIO.output(BN21,GPIO.LOW)
	GPIO.output(BN22,GPIO.LOW)

	p1=GPIO.PWM(NSLEEP1,1000)
	p2=GPIO.PWM(NSLEEP2,1000)
	p1.start(30)
	p2.start(30)

	pwm = GPIO.PWM(servo_pin, 50)
	pwm.start(0)

	GPIO.setup(led_pin, GPIO.OUT)
		

@socketio.on('disconnect')
def on_disconnect():
	thread_event.clear()

@socketio.on('command')
def command(data):
	process_command(data)
	emit('command_status', data)

@socketio.on('latency_problem')
def latency_problem():
	process_latency_problem()


@socketio.on('light')
def light(data):
	if data:
		GPIO.output(led_pin, GPIO.HIGH)
		if DEBUG:
			print(f'light turned on')
	else:
		GPIO.output(led_pin, GPIO.LOW)
		if DEBUG:
			print(f'light turned off')

@socketio.on('idle')
def idle(data):
	global worker
	if data:
		worker.stop()
		if DEBUG:
			print(f'user set to idle')
	else:
		worker.start()
		if DEBUG:
			print(f'user set to active')

if __name__ == '__main__':
	socketio.run(app, host='0.0.0.0', port=8000, debug=True)
