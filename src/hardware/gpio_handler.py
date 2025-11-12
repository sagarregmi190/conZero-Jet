from gpiozero import Button
from typing import Callable, Dict

class GPIOHandler:
    """
    pin_map: dict logical_name -> BCM pin
    callback(pin, level): called on both edges with level (0=pressed, 1=released)
    """
    def __init__(self, pin_map: Dict[str, int], callback: Callable[[int, int], None]):
        self.pin_map = pin_map or {}
        self.button_pins = list(self.pin_map.values())
        self.callback = callback
        self._buttons = {}
        self._backend = None
        
        print(f"[GPIOHandler] Initializing with pins: {self.pin_map}")
        
        # Try gpiozero first
        try:
            self._init_gpiozero()
            self._backend = "gpiozero"
            return
        except Exception as e:
            print(f"[GPIOHandler] gpiozero failed: {e}")
        
        print("[GPIOHandler] No GPIO backend available. Running in no-op mode.")
        self._backend = None

    def _init_gpiozero(self):
        """Initialize using gpiozero"""
        bounce_time = 0.08  # 80ms debounce
        
        for name, pin in self.pin_map.items():
            if pin is None:
                raise ValueError(f"Pin for '{name}' is None")
                
            btn = Button(
                pin, 
                pull_up=True,
                bounce_time=bounce_time
            )
            
            # Use lambda to capture the current pin value
            btn.when_pressed = lambda p=pin: self._handle_button(p, 0)
            btn.when_released = lambda p=pin: self._handle_button(p, 1)
            
            self._buttons[pin] = btn
            print(f"[GPIOHandler] Configured '{name}' on pin {pin}")

    def _handle_button(self, pin: int, level: int):
        """Handle button events - simple passthrough"""
        try:
            self.callback(pin, level)
        except Exception as e:
            print(f"[GPIOHandler] Callback error: {e}")

    def cleanup(self):
        """Clean up GPIO resources"""
        if self._backend == "gpiozero":
            for pin, btn in self._buttons.items():
                try:
                    btn.close()
                except Exception as e:
                    print(f"[GPIOHandler] Error closing button on pin {pin}: {e}")
            self._buttons.clear()
            print("[GPIOHandler] Cleanup completed")