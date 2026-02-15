import React, {useEffect, useRef, useState, useMemo } from 'react';
import nipplejs from 'nipplejs';
import {
  ChakraProvider,
  defaultSystem,
  SegmentGroup,
  HStack,
  IconButton,
  Flex,
  Grid,
  GridItem,
  CloseButton,
  Presence,
} from "@chakra-ui/react"
import {
  LuCarFront,
  LuTrash2,
  LuLightbulb,
  LuLightbulbOff,
} from "react-icons/lu"
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";

import GestureDriveImg from './assets/gesture-left.png';

import './App.css';

// The number of milliseconds between joystick position emissions to the backend.
// A lower number causes more frequent syncing and a theoretically more responsive experience,
// but it comes at a trade-off of possibly overloading the system with too many requests.
const CONTROLS_VEHICLE_SYNC_INTERVAL_MS = 25;

// If controls aren't activated for this amount of time, the feed will go into an idle state
// where new frames aren't sent. This saves on bandwidth.
// Set to 0 to disable.
const IDLE_TIME_MS = 10000;

const getWindowDimensions = () => {
  const { innerWidth: width, innerHeight: height } = window;
  return {
    width,
    height
  };
}

const useWindowDimensions = () => {
  const [windowDimensions, setWindowDimensions] = useState(getWindowDimensions());

  useEffect(() => {
    function handleResize() {
      setWindowDimensions(getWindowDimensions());
    }

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return windowDimensions;
}

const convertNippleData = (data) => {
  let modifier = 1;
  if (data.direction.x === 'left' || data.direction.y === 'down') {
    modifier = -1;
  }
  return Math.round(data.force * modifier * 100);
};

function App() {
  const drive = useRef(null);
  const steer = useRef(null);
  const managerDrive = useRef(null);
  const managerSteer = useRef(null);
  const driveValue = useRef(null);
  const steerValue = useRef(null);
  const driveValuePrev = useRef(null);
  const steerValuePrev = useRef(null);
  const commandTimer = useRef(null);
  const feed = useRef(null);
  const socket = useRef(null);
  const currentLatency = useRef(null);
  const idleTimer = useRef(null);
  const [driveActive, setDriveActive] = useState(false);
  const [steerActive, setSteerActive] = useState(false);
  const [device, setDevice] = useState('vehicle');
  const [light, setLight] = useState(false);
  const [showLatencyWarning, setShowLatencyWarning] = useState(false);
  const [idle, setIdle] = useState(false);
  const windowDimensions = useWindowDimensions();
  
  useEffect(() => {
    
    socket.current.on('command_status', function(data) {
      driveValuePrev.current = data.drive === null ? null : parseInt(data.drive);
      steerValuePrev.current = data.steer === null ? null : parseInt(data.steer);
    });
    
  },);

  const handleResetIdle = () => {
    if (IDLE_TIME_MS) {
      setIdle(false);
      if (idleTimer.current) {
        clearTimeout(idleTimer.current);
      }
      idleTimer.current = setTimeout(() => {
        setIdle(true);
      }, [IDLE_TIME_MS]);
    }
  };

  useEffect(() => {
    if (commandTimer.current) {
      return;
    }

    if (IDLE_TIME_MS) {
      idleTimer.current = setTimeout(() => {
        setIdle(true);
      }, [IDLE_TIME_MS]);
    }

    const optionsDrive = {
      zone: drive.current,
      lockY: true,
      shape: 'square',
      mode: 'dynamic',
    };
    managerDrive.current = nipplejs.create(optionsDrive);
    const optionsSteer = {
      zone: steer.current,
      lockX: true,
      shape: 'square',
      restJoystick: false,
      mode: 'static',
      position: { top: 'calc(50% + 20px)', right: '120px' },
    };
    managerSteer.current = nipplejs.create(optionsSteer);

    managerDrive.current.on('start', () => {
      driveValue.current = 0;
      setDriveActive(true);
    }).on('end', () => {
      setDriveActive(false);
    }).on('move', (evt, data) => {
      if (data.force && data.direction) {
	      driveValue.current = convertNippleData(data);
        handleResetIdle();
      }
    });

    managerSteer.current.on('start', () => {
      setSteerActive(true);
    }).on('end', () => {
      setSteerActive(false);
    }).on('move', (evt, data) => {
      if (data.force && data.direction) {
	      steerValue.current = convertNippleData(data);
        handleResetIdle();
      }
    });
  }, []);

  useEffect(() => {
    if (commandTimer.current) {
      clearInterval(commandTimer.current);
    }
    const sync_interval = device == 'vehicle' ? CONTROLS_VEHICLE_SYNC_INTERVAL_MS : CONTROLS_CAMERA_SYNC_INTERVAL_MS;
    commandTimer.current = setInterval(() => {
      const driveValueCurated = driveActive ? driveValue.current : null;
      const steerValueCurated = steerActive ? steerValue.current : null;
      if (!showLatencyWarning) {
        // The vehicle moves by setting values and the camera moves by incrementing or decrementing values
        // so for the vehicle, only emit data when there's a change, and for the camera, always emit data.
        if (driveValueCurated !== driveValuePrev.current || steerValueCurated !== steerValuePrev.current) {
          currentLatency.current = Date.now();
          socket.current.emit('command', {
            drive: driveValueCurated,
            steer: steerValueCurated,
          });
        }
      }
    }, sync_interval);
  }, [driveActive, steerActive, device, showLatencyWarning]);

  const appClass = useMemo(() => {
    let className = `App--${mode}`;
    if (window.requireAuth && !authenticated) {
      className += ' App--unauthenticated';
    } else if (driveActive || steerActive) {
      className += ' App--active';
    } else {
      className += ' App--inactive';
    }
    return className;
  }, [driveActive, steerActive, authenticated, mode]);


  useEffect(() => {
    if (socket.current) {
      socket.current.emit('idle', idle);
    }
  }, [idle]);

  useEffect(() => {
    if (socket.current) {
      socket.current.emit('light', light);
    }
  }, [light]);

  const gestureAlignmentClass = useMemo(() => {
    const aspectRatio = CAMERA_ASPECT_RATIO;
    const videoWidth = window.innerHeight * aspectRatio;
    if (videoWidth >= window.innerWidth) {
      return 'gesture-alignBottom';
    }
    return 'gesture-alignCenter';
  }, [windowDimensions]);


  return (
    <ChakraProvider value={defaultSystem}>
      <div className={`App dark ${appClass}`}>
        <div className={`feed${idle ? ' feed--idle' : ''}`}>
          <canvas ref={feed}></canvas>
          <Presence
            present={photoTaken}
            _open={{ animationName: "fade-in", animationDuration: "30ms" }}
            _closed={{ animationName: "fade-out", animationDuration: "1500ms" }}
          >
          </Presence>
          <Presence
            present={showLatencyWarning}
            _open={{ animationName: "fade-in", animationDuration: "30ms" }}
            _closed={{ animationName: "fade-out", animationDuration: "1500ms" }}
          >
            <div className="feedNotification">
              <p>High latency detected. Controls are disabled. Please wait.</p>
            </div>
          </Presence>
          <Presence
            present={idle}
            _open={{ animationName: "fade-in", animationDuration: "3000ms" }}
            _closed={{ animationName: "fade-out", animationDuration: "300ms" }}
          >
            <div className="feedNotification">
              <p>You are currently idle. Touch the controls to begin.</p>
            </div>
          </Presence>
        </div>
        <div id="controls">
          <div className="zone" id="drive" ref={drive}>
            <div className={`gesture ${gestureAlignmentClass} gesture-drive${(!driveActive && !photoOpen && !albumOpen) ? ' gesture--visible' : ''}`}>
              <img src={GestureDriveImg} />
            </div>
          </div>
          <div className="zone" id="steer" ref={steer}></div>
        </div>
        <div className="settings settings-left">

        </div>
        <div className="settings settings-right">
          <Flex gap="2">
            <IconButton disabled={buttonsDisabled} aria-label="Toggle Light" size="lg" colorPalette={light ? 'blue' : 'white'} variant="solid" onClick={() => setLight(!light)}>
              {light ? (
                <LuLightbulb color="white" />
              ) : (
                <LuLightbulbOff color="white" />
              )}
            </IconButton>
            <SegmentGroup.Root
              disabled={buttonsDisabled}
              size="lg"
              onValueChange={({ value }) => setDevice(value)}
              value={device}
              css={{
                "--segment-indicator-bg": "colors.blue.600",
                "--chakra-colors-bg-muted": "#333",
              }}
            >
              <SegmentGroup.Indicator />
              <SegmentGroup.Items items={[
                {
                  value: "vehicle",
                  label: (
                    <HStack>
                      <LuCarFront />
                    </HStack>
                  ),
                },
              ]}/>
            </SegmentGroup.Root>
          </Flex>
        </div>
      </div>
    </ChakraProvider>
  );
}

export default App
