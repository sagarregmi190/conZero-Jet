import serial
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(message)s")

def ts():
    return datetime.now().strftime("%H:%M:%S.%f")

def hex_str(data: bytes) -> str:    #converts bytes object to space-separated lower-case hex.
    return ' '.join(f"{b:02x}" for b in data)

class AdaptiveMotorPilot:
    """
    Adaptive implementation that follows STM32's responses
    """
    
    # Initial beacon - same as MotorPilot
    BEACON_TX = bytes.fromhex("15 c7 01 94")
    
    # Commands from Motor Pilot
    REQ_NAME = bytes.fromhex("49 00 00 70 11 00 e1 00")
    START    = bytes.fromhex("29 00 00 e0 19 00")
    STOP     = bytes.fromhex("29 00 00 e0 21 00")

    def __init__(self, port="/dev/ttyS0", baud=115200):
        self.port = port
        self.baud = baud
        self.ser: serial.Serial | None = None
        self.connected = False

    def open(self):
        """Open with adaptive settings"""
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.1,
            rtscts=True,
            dsrdtr=False
        )
        print(f"Port opened: {self.port} @ {self.baud} baud")

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            
    #_send_and_capture: core send routine (write bytes, optional wait for CTS, delay, then read what is present once).
    def _send_and_capture(self, tx: bytes, wait=0.1) -> bytes:
        """Send and capture whatever response we get"""
        if not self.ser:
            return b''
            
        self.ser.reset_input_buffer()
        print(f"{ts()} --> Tx: {hex_str(tx)}")
        
        # Wait for clear to send CTS
        if self.ser.rtscts:
            start_time = time.time()
            while not self.ser.cts:
                if time.time() - start_time > 2.0:
                    print("CTS timeout, sending anyway...")
                    break
                time.sleep(0.01)
        
        # Send data
        self.ser.write(tx)
        self.ser.flush()
        
        # Wait and read response
        time.sleep(wait)
        
        rx_data = b''
        if self.ser.in_waiting > 0:
            rx_data = self.ser.read(self.ser.in_waiting)
            print(f"{ts()} <-- Rx: {hex_str(rx_data)}")
        else:
            print("   No response")
        
        return rx_data

    #adaptive_handshake: tries to establish link by (a) sending BEACON_TX, (b) echoing whatever came back, 
    # (c) sending several “ping” patterns hoping one yields a reply
    # Marks connected=True regardless once any ping yields data.
    
    def adaptive_handshake(self):
        """Adaptive handshake that follows STM32's responses"""
        print("\n🔗 === ADAPTIVE HANDSHAKE ===")
        
        # Step 1: Send beacon and see what we get back
        print("1. Sending beacon...")
        beacon_response = self._send_and_capture(self.BEACON_TX, wait=0.2)
        
        if len(beacon_response) < 4:  #at least 4 bytes 
            print(" No beacon response")
            return False
        
        print(f"   STM32 responded with: {hex_str(beacon_response)}")
        
        # Step 2: Echo back whatever the STM32 sent us
        print("2. Echoing STM32's response...")
        echo_response = self._send_and_capture(beacon_response, wait=0.2)
        
        if echo_response != beacon_response:
            print(f"    Echo mismatch: expected {hex_str(beacon_response)}, got {hex_str(echo_response)}")
            # Continue anyway - some protocols don't require exact echo
        
        # Step 3: Try different ping patterns
        print("3. Testing connection...")
        
        ping_patterns = [
            bytes.fromhex("06 00 00 60"),  # Original ping
            bytes.fromhex("16 00 00 70"),  # Variant 1
            bytes.fromhex("26 00 00 80"),  # Variant 2
            bytes.fromhex("36 00 00 90"),  # Variant 3
        ]
        
        for i, ping in enumerate(ping_patterns):
            print(f"   Ping test {i+1}: {hex_str(ping)}")
            response = self._send_and_capture(ping, wait=0.1)
            if response:
                print(f"    Got response: {hex_str(response)}")
                break
            else:
                print("    No response")
        
        print(" Adaptive handshake completed!")
        self.connected = True
        return True

    def try_motor_commands(self):
        """Try various motor command patterns"""
        print("\n === TESTING MOTOR COMMANDS ===")
        
        # Test different command patterns
        command_patterns = [
            # Original commands from capture
            bytes.fromhex("29 00 00 e0 19 00"),  # START
            bytes.fromhex("29 00 00 e0 21 00"),  # STOP
            
            # Variations that might work
            bytes.fromhex("29 00 00 e0 01 00"),  # CMD 0x01
            bytes.fromhex("29 00 00 e0 02 00"),  # CMD 0x02
            bytes.fromhex("39 00 00 e0 19 00"),  # Different header
            bytes.fromhex("49 00 00 e0 19 00"),  # Different header
        ]
        
        for i, cmd in enumerate(command_patterns):
            print(f"\nCommand test {i+1}: {hex_str(cmd)}")
            response = self._send_and_capture(cmd, wait=0.3)
            
            if response:
                if response[0] == 0x0F:
                    print("    CRC Error")
                else:
                    print(f"    Success! Response: {hex_str(response)}")
            else:
                print("    No response")

    def discover_protocol(self):
        """Discover the actual protocol by testing different patterns"""
        print("\n🔍 === PROTOCOL DISCOVERY ===")
        
        # Test different beacon patterns
        beacon_patterns = [
            bytes.fromhex("15 c7 01 94"),  # Original
            bytes.fromhex("15 c3 00 d4"),  # Based on STM32 response
            bytes.fromhex("05 c7 01 14"),  # Echo pattern
            bytes.fromhex("05 c3 00 d4"),  # Echo of STM32 response
        ]
        
        for i, beacon in enumerate(beacon_patterns):
            print(f"\nBeacon test {i+1}: {hex_str(beacon)}")
            response = self._send_and_capture(beacon, wait=0.2)
            if response:
                print(f"   Response: {hex_str(response)}")
                
#main: procedural execution: open port → run handshake → test commands → interactive loop sending start / stop / discovery frames

def main():
    print(" ADAPTIVE MOTORPILOT IMPLEMENTATION")
    print("Following STM32's actual responses")
    
    controller = AdaptiveMotorPilot(port="/dev/ttyS0", baud=115200)
    
    try:
        # Open connection
        controller.open()
        
        # Try adaptive handshake
        if controller.adaptive_handshake():
            print("\n Connected! Testing motor commands...")
            
            # Try to discover working commands
            controller.try_motor_commands()
            
            # Interactive testing
            print("\n Interactive testing available")
            while True:
                cmd = input("\n[s]tart, [t]op, [d]iscover, [q]uit: ").strip().lower()
                
                if cmd == 's':
                    controller._send_and_capture(controller.START, wait=0.3)
                elif cmd == 't':
                    controller._send_and_capture(controller.STOP, wait=0.3)
                elif cmd == 'd':
                    controller.discover_protocol()
                elif cmd == 'q':
                    break
        else:
            print(" Connection failed")
            
    except Exception as e:
        print(f" Error: {e}")
    finally:
        controller.close()

if __name__ == "__main__":
    main()