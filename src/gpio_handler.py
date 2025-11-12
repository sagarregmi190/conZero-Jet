# GPIOHandler: safe Raspberry Pi GPIO button helper.

import time 
import threading 
try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None  # Running off Pi

class GPIOHandler:
    """
    pin_map: dict logical_name -> BCM pin
    callback(pin, level): called on both edges with level (0=pressed, 1=released)
    """
    def __init__(self, pin_map: dict, callback, long_press_ms: int=600, debounce_ms: int = 50):
        # Define attributes FIRST so they exist even if setup fails
        self.pin_map = pin_map or {}
        self.long_press_ms = long_press_ms
        self.debounce_ms = debounce_ms
        self.button_pins = list(self.pin_map.values())  # required by UI
        self.callback = callback
        self._press_times = {}   # pin -> press start time
        self._lock = threading.Lock()
        if GPIO is None:
            print("RPi.GPIO not available. GPIO disabled.")
            return
        self._setup()

    def _setup(self):
        GPIO.setmode(GPIO.BCM)
        for name, pin in self.pin_map.items():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(pin, GPIO.BOTH, callback=self._wrap(pin), bouncetime=60)

    def _wrap(self, pin: int):
        def handler(channel):
            if GPIO is None:
                return
            level = GPIO.input(channel)
            try:
                # Pass both pin and level (0=pressed, 1=released)
                self.callback(pin, level)
            except Exception:
                pass
        return handler

    def cleanup(self):
        if GPIO:
            for pin in self.button_pins:
                try: GPIO.remove_event_detect(pin)
                except Exception: pass
            try: GPIO.cleanup()
            except Exception: pass