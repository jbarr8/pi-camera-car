BIN=.venv/bin/

install:
	sudo apt install jq -y
	sudo apt install -y python3-picamera2
	python -m venv .venv --system-site-packages
	$(BIN)pip install Flask==3.1.1 Flask-SocketIO==5.6.0 opencv-python==4.13.0.90 gevent==25.9.1 gevent-websocket==0.10.1 setproctitle==1.3.7
	gcc -fPIC -shared ./backend/camera_mount/mount_functions.c ./backend/camera_mount/PCA9685.c ./backend/camera_mount/PCA9685.h -o ./backend/camera_mount/mount_functions.o
	mkdir album
	chmod 0777 album
	echo "dtparam=i2c_arm=on" >> /boot/firmware/config.txt
	reboot

start:
	$(BIN)python ./backend/app.py

start-public:
	$(BIN)python ./backend/app.py &
	ngrok http 8000 &

stop:
	@if ! pgrep pi-camera-car > /dev/null; then \
		echo "Pi Camera Car is not currently running."; \
	else \
		pkill -9 pi-camera-car; \
		echo "Pi Camera Car stopped successfully."; \
	fi
	@if ! pgrep ngrok > /dev/null; then \
		echo "ngrok is not currently running."; \
	else \
		pkill -9 ngrok; \
		echo "ngrok stopped successfully."; \
	fi

get-url:
	@if ! pgrep ngrok > /dev/null; then \
		echo "ngrok is not running."; \
	else \
		curl -s localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'; \
	fi

compile-camera-mount:
	gcc -fPIC -shared ./backend/camera_mount/mount_functions.c ./backend/camera_mount/PCA9685.c ./backend/camera_mount/PCA9685.h -o ./backend/camera_mount/mount_functions.o
