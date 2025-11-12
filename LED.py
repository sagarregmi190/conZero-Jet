from gpiozero import LED

class StatusLED:
    def __init__(self, pin=27):
        self.led = LED(pin)
        self.led.off()  # Start OFF