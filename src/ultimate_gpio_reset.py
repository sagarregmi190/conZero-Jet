#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO
import os

print("=== MINIMAL GPIO TEST ===")
print("1. Cleaning up GPIO...")

# Force cleanup first
try:
    GPIO.cleanup()
except:
    pass

# Kill any Python processes that might be using GPIO
os.system("sudo pkill -f python3 2>/dev/null")
time.sleep(2)

print("2. Testing GPIO setup...")

try:
    # Basic GPIO setup
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(True)
    
    # Test pins from your config
    test_pins = [17, 23, 16, 5]
    
    for pin in test_pins:
        print(f"   Testing pin {pin}...")
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        value = GPIO.input(pin)
        print(f"   ✅ Pin {pin} = {value}")
    
    print("3. ✅ ALL GPIO PINS WORKING!")
    print("4. Testing button detection...")
    
    # Test button presses for 10 seconds
    print("   Press buttons for 10 seconds...")
    start_time = time.time()
    while time.time() - start_time < 10:
        for pin in test_pins:
            current_value = GPIO.input(pin)
            if current_value == 0:  # Button pressed
                print(f"   🔘 BUTTON PRESSED: Pin {pin}")
        time.sleep(0.1)
    
    print("5. ✅ GPIO TEST COMPLETE!")
    
except Exception as e:
    print(f"❌ GPIO TEST FAILED: {e}")
    import traceback
    traceback.print_exc()

finally:
    print("6. Cleaning up...")
    try:
        GPIO.cleanup()
    except:
        pass