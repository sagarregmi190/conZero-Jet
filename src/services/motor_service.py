"""
Motor Control Service
Handles all motor UART communication and control
"""

import os
from typing import Optional
from hardware.uart_manager import ASPEPClient

class MotorService:
    """Manages motor control via UART"""
    
    def __init__(self, port: Optional[str] = None, baud: int = 115200):
        """Initialize motor service"""
        self.port = port or os.environ.get("CONZERO_UART_PORT", "/dev/ttyS0")
        self.baud = baud
        self.client: Optional[ASPEPClient] = None
        self.ready = False
        self._last_speed_ref: Optional[int] = None
    
    def initialize(self) -> bool:
        """Initialize motor connection and handshake"""
        try:
            print(f"🔌 Initializing motor on {self.port}...")
            self.client = ASPEPClient(port=self.port, baud=self.baud)
            self.client.open()
            
            if self.client.handshake():
                self.ready = True
                print(" Motor ready")
                return True
            else:
                print(" Motor handshake failed")
                return False
                
        except Exception as e:
            print(f" Motor init error: {e}")
            return False
    
    def start(self, motor_index: int = 1) -> bool:
        """Start motor"""
        if not self.ready or not self.client:
            print(" Motor not ready - cannot start")
            return False
        
        try:
            success = self.client.start_motor(motor_index)
            if success:
                print(" Motor started")
            return success
        except Exception as e:
            print(f" Motor start error: {e}")
            return False
    
    def stop(self, motor_index: int = 1) -> bool:
        """Stop motor"""
        if not self.ready or not self.client:
            return False
        
        try:
            success = self.client.stop_motor(motor_index)
            if success:
                print(" Motor stopped")
            return success
        except Exception as e:
            print(f" Motor stop error: {e}")
            return False
    
    def set_speed(self, speed_percent: int, motor_index: int = 1) -> bool:
        """Set motor speed as percentage"""
        if not self.ready or not self.client:
            print(f" Motor not ready - speed {speed_percent}% not sent")
            return False
        
        # Convert percentage to RPM
        if hasattr(self.client, '_max_speed_rpm'):
            target_rpm = int((speed_percent / 100.0) * self.client._max_speed_rpm)
        else:
            # Fallback to default conversion
            target_rpm = int(speed_percent * 48)  # 100% = 4800 RPM
        
        print(f"  Setting speed: {speed_percent}% → {target_rpm} RPM")
        
        try:
            success = self.client.set_speed_rpm(target_rpm, motor_index)
            if success:
                self._last_speed_ref = target_rpm
                print(f" Speed set: {target_rpm} RPM")
            return success
        except Exception as e:
            print(f" Speed set error: {e}")
            return False
    
    def read_faults(self, motor_index: int = 1) -> Optional[int]:
        """Read motor fault flags"""
        if not self.ready or not self.client:
            return None
        
        try:
            return self.client.read_faults(motor_index)
        except Exception as e:
            print(f" Fault read error: {e}")
            return None
    
    def acknowledge_faults(self, motor_index: int = 1) -> bool:
        """Acknowledge/clear motor faults"""
        if not self.ready or not self.client:
            return False
        
        try:
            success = self.client.fault_acknowledge(motor_index)
            if success:
                print(" Faults acknowledged")
            return success
        except Exception as e:
            print(f" Fault ack error: {e}")
            return False
    
    def read_speed(self, motor_index: int = 1) -> Optional[int]:
        """Read actual motor speed in RPM"""
        if not self.ready or not self.client:
            return None
        
        try:
            self.client.poll_speed(motor_index, repeat=1, delay=0)
            
            if self.client.last_data_payload and len(self.client.last_data_payload) >= 4:
                speed_rpm = int.from_bytes(
                    self.client.last_data_payload[:4], 
                    'little', 
                    signed=True
                )
                return speed_rpm
            return None
        except Exception as e:
            print(f" Speed read error: {e}")
            return None
    
    def get_last_speed_ref(self) -> Optional[int]:
        """Get last commanded speed reference"""
        return self._last_speed_ref
    
    def close(self):
        """Close motor connection"""
        if self.client:
            try:
                self.client.close()
                print(" Motor connection closed")
            except Exception as e:
                print(f" Motor close error: {e}")
    
    def __enter__(self):
        """Context manager support"""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.close()