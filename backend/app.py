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

app = Flask(__name__, static_folder="../frontend/dist/assets", template_folder="../frontend/dist")

# at some point, add PWM which allows for speed variation
# https://gpiozero.readthedocs.io/en/stable/api_output.html#motor

rearMotor = Motor(forward=18, backward=19)
steeringMotor = Motor(forward=4, backward= 5)


socketio = SocketIO(app, async_mode='gevent')



def process_latency_problem():
	# When there's a latency problem, stop all vehicle movement
	print('latency problem')
	rearMotor.stop()
	steeringMotor.stop()


def process_command(data):
	drive = None
	steer_angle = None
	device = data['device']
	
	if device == 'vehicle':
		if data['drive'] == None:
			rearMotor.stop()
			steeringMotor.stop()
		else:
			# handle throttle
			if drive > 0:
				# forward
				rearMotor.forward()
			else:
				# reverse
				rearMotor.reverse()

		if data['steer'] == None:
			steeringMotor.stop()
		else:
			if steer_angle < 0:
				steeringMotor.forward()
				rearMotor.forward()
			elif steer_angle > 0:
				steeringMotor.backward()
				rearMotor.forward()




@app.route("/")
def index():
	return render_template("index.html")


@socketio.on('connect')
def connect():
	global pwm, p1, p2
	steeringMotor.stop()
	rearMotor.stop()


@socketio.on('command')
def command(data):
	process_command(data)
	emit('command_status', data)

@socketio.on('latency_problem')
def latency_problem():
	process_latency_problem()



@socketio.on('idle')
def idle(data):
	global worker
	if data:
		worker.stop()

	else:
		worker.start()


if __name__ == '__main__':
	socketio.run(app, host='0.0.0.0', port=8000, debug=True)
