from gevent import monkey
monkey.patch_all()
from gpiozero import Motor

# for testing on Windows
from gpiozero.pins.mock import MockFactory
from gpiozero import Device
Device.pin_factory = MockFactory()

from flask import Flask, send_file, request
from flask_socketio import SocketIO, emit, ConnectionRefusedError
from flask import render_template, request


app = Flask(__name__, static_folder="../frontend/dist/assets", template_folder="../frontend/dist")
socketio = SocketIO(app, async_mode='gevent')

# at some point, add PWM which allows for speed variation
# https://gpiozero.readthedocs.io/en/stable/api_output.html#motor

rearMotor = Motor(forward=18, backward=19, pwm=False)
steeringMotor = Motor(forward=4, backward= 5, pwm=False)


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
	socketio.run(app, host='0.0.0.0', port=8000)
