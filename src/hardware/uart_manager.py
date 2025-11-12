#!/usr/bin/env python3
"""
ASPEP/MCP Motor Control Client - Complete with Physically Accurate Speed Ramp
Based on STM32 Motor Control SDK firmware analysis

Author: sagarregmi
Date: 2025-01-23
Version: 6.0 - Physically Accurate Ramp

Features:
- PHYSICALLY ACCURATE speed ramp handling (ramp_duration_ms = speed_change / acc_rpm_s * 1000)
- Speed Reading/Writing with RPM and Percentage support
- Fault Reading and Acknowledge
- Motor Start/Stop
- Full diagnostics
"""

import serial
import time
import logging
import struct
from dataclasses import dataclass
from typing import Optional

# =========== ========== ========== =================== LOGGING ===== ========== ========== ========================= ========== ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("ASPEP_MCP")

# ========= ========== ========== ===================== ASPEP PROTOCOL CONSTANTS =========== ========== ================== ===========
TYPE_SILENT = 0x1
TYPE_BEACON = 0x5
TYPE_PING   = 0x6
TYPE_ERROR  = 0x7
TYPE_DATA   = 0x9
TYPE_ACK    = 0xA
TYPE_NACK   = 0xF

# ============ ========== ========== ================== MCP COMMAND IDs (from mcp.h) ============== ========== ================ ==========
GET_MCP_VERSION     = 0x00
SET_DATA_ELEMENT    = 0x08
GET_DATA_ELEMENT    = 0x10
START_MOTOR         = 0x18
STOP_MOTOR          = 0x20
STOP_RAMP           = 0x28
START_STOP          = 0x30
FAULT_ACK           = 0x38
CPULOAD_CLEAR       = 0x40
IQDREF_CLEAR        = 0x48
PFC_ENABLE          = 0x50
PFC_DISABLE         = 0x58
PFC_FAULT_ACK       = 0x60
PROFILER_CMD        = 0x68
SW_RESET            = 0x78

# Legacy command names (kept for compatibility)
CMD_NAME            = 0x0011
CMD_START           = 0x0019
CMD_STOP            = 0x0021
CMD_READ_REGS       = 0x10
MCP_CMD_WRITE_REG   = 0x08
CMD_WRITE_REGS      = 0x11
CMD_SPEED_RAMP      = 0x13
CMD_STOP_RAMP       = 0x16
CMD_RAMP_STATUS     = 0x17

# =========== ========== ========== =================== REGISTER ENCODING =================== ========== ========== ========== ===========
ELT_IDENTIFIER_POS  = 6
TYPE_POS            = 3
TYPE_MASK           = 0x38
MOTOR_MASK          = 0x07
REG_MASK            = 0xFFF8

# Register type definitions
TYPE_DATA_8BIT      = (1 << TYPE_POS)  # 0x08
TYPE_DATA_16BIT     = (2 << TYPE_POS)  # 0x10
TYPE_DATA_32BIT     = (3 << TYPE_POS)  # 0x18
TYPE_DATA_STRING    = (4 << TYPE_POS)  # 0x20
TYPE_DATA_RAW       = (5 << TYPE_POS)  # 0x28

# =========== ========== ========== =================== REGISTER ADDRESSES ============= ========== ========== ========== =================
# Base addresses (without motor ID encoded)
MC_REG_SPEED_MEAS_BASE  = ((1 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)  # 0x0058
MC_REG_SPEED_REF_BASE   = ((2 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)  # 0x0098
MC_REG_STATUS_BASE      = ((1 << ELT_IDENTIFIER_POS) | TYPE_DATA_8BIT)   # 0x0048
MC_REG_FAULTS_BASE      = ((0 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)  # 0x0018
MC_REG_BUS_VOLTAGE_BASE = ((22 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT) # 0x0590
MC_REG_HEATS_TEMP_BASE  = ((23 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT) # 0x05D0

# SPEED RAMP REGISTER - CRITICAL FOR PREVENTING OVER-VOLTAGE FAULTS
MC_REG_SPEED_RAMP_BASE  = ((6 << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)    # 0x0604

# For Motor 1 (with motor_id = 0x01 encoded)
MC_REG_SPEED_MEAS   = 0x0059  # MC_REG_SPEED_MEAS_BASE | 0x01
MC_REG_SPEED_REF    = 0x0099  # MC_REG_SPEED_REF_BASE | 0x01
MC_REG_FAULTS       = 0x0019  # MC_REG_FAULTS_BASE | 0x01

# ========= ========== ========== ===================== FAULT BIT DEFINITIONS (from mc_type.h) ========== ========== ========== ====================
FAULT_NO_ERROR          = 0x0000
FAULT_FOC_DURATION      = 0x0001
FAULT_OVER_VOLT         = 0x0002
FAULT_UNDER_VOLT        = 0x0004
FAULT_OVER_TEMP         = 0x0008
FAULT_START_UP          = 0x0010
FAULT_SPEED_FDBK        = 0x0020
FAULT_OVER_CURR         = 0x0040
FAULT_SW_ERROR          = 0x0080
FAULT_DP_FAULT          = 0x0400

FAULT_NAMES = {
    0x0001: "FOC DURATION",
    0x0002: "OVER VOLTAGE",
    0x0004: "UNDER VOLTAGE",
    0x0008: "OVER TEMPERATURE",
    0x0010: "START UP FAILURE",
    0x0020: "SPEED FEEDBACK",
    0x0040: "OVER CURRENT",
    0x0080: "SOFTWARE ERROR",
    0x0400: "DRIVER PROTECTION",
}

# ======== ========== ========== ====================== CRC4 LOOKUP TABLES ============ ========== ========== ==================
CRC4_Lookup8 = [
  0x00,0x02,0x04,0x06,0x08,0x0a,0x0c,0x0e,0x07,0x05,0x03,0x01,0x0f,0x0d,0x0b,0x09,
  0x07,0x05,0x03,0x01,0x0f,0x0d,0x0b,0x09,0x00,0x02,0x04,0x06,0x08,0x0a,0x0c,0x0e,
  0x0e,0x0c,0x0a,0x08,0x06,0x04,0x02,0x00,0x09,0x0b,0x0d,0x0f,0x01,0x03,0x05,0x07,
  0x09,0x0b,0x0d,0x0f,0x01,0x03,0x05,0x07,0x0e,0x0c,0x0a,0x08,0x06,0x04,0x02,0x00,
  0x0b,0x09,0x0f,0x0d,0x03,0x01,0x07,0x05,0x0c,0x0e,0x08,0x0a,0x04,0x06,0x00,0x02,
  0x0c,0x0e,0x08,0x0a,0x04,0x06,0x00,0x02,0x0b,0x09,0x0f,0x0d,0x03,0x01,0x07,0x05,
  0x05,0x07,0x01,0x03,0x0d,0x0f,0x09,0x0b,0x02,0x00,0x06,0x04,0x0a,0x08,0x0e,0x0c,
  0x02,0x00,0x06,0x04,0x0a,0x08,0x0e,0x0c,0x05,0x07,0x01,0x03,0x0d,0x0f,0x09,0x0b,
  0x01,0x03,0x05,0x07,0x09,0x0b,0x0d,0x0f,0x06,0x04,0x02,0x00,0x0e,0x0c,0x0a,0x08,
  0x06,0x04,0x02,0x00,0x0e,0x0c,0x0a,0x08,0x01,0x03,0x05,0x07,0x09,0x0b,0x0d,0x0f,
  0x0f,0x0d,0x0b,0x09,0x07,0x05,0x03,0x01,0x08,0x0a,0x0c,0x0e,0x00,0x02,0x04,0x06,
  0x08,0x0a,0x0c,0x0e,0x00,0x02,0x04,0x06,0x0f,0x0d,0x0b,0x09,0x07,0x05,0x03,0x01,
  0x0a,0x08,0x0e,0x0c,0x02,0x00,0x06,0x04,0x0d,0x0f,0x09,0x0b,0x05,0x07,0x01,0x03,
  0x0d,0x0f,0x09,0x0b,0x05,0x07,0x01,0x03,0x0a,0x08,0x0e,0x0c,0x02,0x00,0x06,0x04,
  0x04,0x06,0x00,0x02,0x0c,0x0e,0x08,0x0a,0x03,0x01,0x07,0x05,0x0b,0x09,0x0f,0x0d,
  0x03,0x01,0x07,0x05,0x0b,0x09,0x0f,0x0d,0x04,0x06,0x00,0x02,0x0c,0x0e,0x08,0x0a
]

CRC4_Lookup4 = [
  0x00,0x07,0x0e,0x09,0x0b,0x0c,0x05,0x02,
  0x01,0x06,0x0f,0x08,0x0a,0x0d,0x04,0x03
]

# =========== ========== ========== ========== =================== HELPER FUNCTIONS ================ ========== ========== ==============
def compute_header_crc(lower28: int) -> int:
    """Compute CRC4 for 28-bit header"""
    h = lower28 & 0x0FFFFFFF
    crc = 0
    crc = CRC4_Lookup8[crc ^ (h & 0xFF)]
    crc = CRC4_Lookup8[crc ^ ((h >> 8) & 0xFF)]
    crc = CRC4_Lookup8[crc ^ ((h >> 16) & 0xFF)]
    crc = CRC4_Lookup4[crc ^ ((h >> 24) & 0x0F)]
    return crc & 0xF

def check_header_crc(word32: int) -> bool:
    """Validate 32-bit header CRC"""
    crc = 0
    crc = CRC4_Lookup8[crc ^ (word32 & 0xFF)]
    crc = CRC4_Lookup8[crc ^ ((word32 >> 8) & 0xFF)]
    crc = CRC4_Lookup8[crc ^ ((word32 >> 16) & 0xFF)]
    crc = CRC4_Lookup8[crc ^ ((word32 >> 24) & 0xFF)]
    return crc == 0

def hx(b: bytes) -> str:
    """Format bytes as hex string"""
    return ' '.join(f"{x:02X}" for x in b) if b else ""

def reg_value_size(reg_id: int) -> int:
    """Get register value size from type bits"""
    t = reg_id & TYPE_MASK
    if t == TYPE_DATA_8BIT:  return 1
    if t == TYPE_DATA_16BIT: return 2
    if t == TYPE_DATA_32BIT: return 4
    return 2

# ======== ========== ========== ========== ====================== CAPABILITIES ========= ========== ========== =====================
@dataclass
class Capabilities:
    """ASPEP capabilities"""
    version: int = 0
    data_crc: int = 0
    rx_max: int = 0x1C
    txs_max: int = 0x07
    txa_max: int = 0x01
    
    def build_lower28(self) -> int:
        return (TYPE_BEACON
                | (self.version & 0x7) << 4
                | (self.data_crc & 0x1) << 7
                | (self.rx_max   & 0x3F) << 8
                | (self.txs_max  & 0x7F) << 14
                | (self.txa_max  & 0x7F) << 21)
    
    @staticmethod
    def from_lower28(l28: int):
        return Capabilities(
            version = (l28 >> 4) & 0x7,
            data_crc= (l28 >> 7) & 0x1,
            rx_max  = (l28 >> 8) & 0x3F,
            txs_max = (l28 >>14) & 0x7F,
            txa_max = (l28 >>21) & 0x7F
        )

# ============ ========== ========== ================== MAIN CLIENT CLASS ======== ========== ========== ======================
class ASPEPClient:
    """Complete ASPEP/MCP Motor Control Client with Physically Accurate Speed Ramp"""
    
    def __init__(self, port: str = "/dev/ttyS0", baud: int = 115200, timeout: float = 0.04) -> None:
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser: Optional[serial.Serial] = None
        self.connected = False
        self.ctrl_caps = Capabilities()
        self.perf_caps: Optional[Capabilities] = None
        self.packet_number = 0
        self.ip_id = 0
        self.last_data_payload: bytes = b''
        self._last_speed_ref: Optional[int] = None
        self._max_speed_rpm: int = 4800  # Default max speed - adjust based on your motor
        self._speed_unit: str = "RPM"    # "RPM" or "PERCENT"
        self._acceleration_rpm_s: float = 8000.0 # Default acceleration: 1000 RPM/s

    # ===== ========== ========== ========== =============== SERIAL I/O ========== ========== ========== ========== ========== ==========
    def open(self) -> None:
        """Open serial port"""
        self.ser = serial.Serial(
            self.port, self.baud, timeout=self.timeout,
            bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE, rtscts=False
        )
        log.info(f"Opened {self.port} @ {self.baud} baud")
        self._drain()

    def close(self) -> None:
        """Close serial port"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            log.info("Port closed")

    def _drain(self):
        """Drain RX buffer"""
        if not self.ser: return
        time.sleep(0.02)
        while self.ser.in_waiting:
            self.ser.read(self.ser.in_waiting)
            time.sleep(0.001)

    def _tx(self, data: bytes, desc=""):
        """Transmit data"""
        self.ser.write(data)
        self.ser.flush()
        log.debug(f"TX {desc}: {hx(data)}")

    def _read_exact(self, n: int, timeout=0.4):
        """Read exactly n bytes"""
        end = time.time() + timeout
        buf = b''
        while len(buf) < n and time.time() < end:
            part = self.ser.read(n - len(buf))
            if part: buf += part
            else: time.sleep(0.0008)
        return buf

    def _read_header_sync(self, timeout=0.6):
        """Read and sync to valid header"""
        start = time.time()
        window = bytearray(self._read_exact(4, timeout))
        if len(window) < 4: return b''
        
        while time.time() - start < timeout:
            w = int.from_bytes(window, 'little')
            if check_header_crc(w):
                return bytes(window)
            nxt = self.ser.read(1)
            if not nxt:
                time.sleep(0.0005)
                continue
            window.pop(0)
            window.append(nxt[0])
        return b''

    # ===== ========== ========== ========== ========== =============== PACKET BUILDING ==== ========== ========== ========== ========== ================
    def build_data_header(self, length: int) -> bytes:
        """Build DATA packet header"""
        if length > 0x1FFF: raise ValueError("Payload too long")
        l28 = (length << 4) | TYPE_DATA
        word = (compute_header_crc(l28) << 28) | l28
        return word.to_bytes(4, 'little')

    def build_beacon(self, caps: Capabilities) -> bytes:
        """Build BEACON packet"""
        l28 = caps.build_lower28()
        word = (compute_header_crc(l28) << 28) | l28
        return word.to_bytes(4, 'little')
    
    def build_ping(self):
        """Build PING packet"""
        l28 = (TYPE_PING | (self.ip_id & 0xF) << 8 | (self.packet_number & 0xFFFF) << 12)
        word = (compute_header_crc(l28) << 28) | l28
        return word.to_bytes(4, 'little')

    # === ========== ========== ========== ========== ================= HANDSHAKE ========== ========== ========== ========== ==========
    def handshake(self) -> bool:
        """Perform ASPEP handshake"""
        if self.connected:
            log.info("Already connected")
            return True
        
        self._drain()
        log.info("Handshaking...")
        
        self._tx(self.build_beacon(self.ctrl_caps), "BEACON")
        perf = self._read_exact(4, 0.4)
        if not perf:
            log.error("ERROR: No performer beacon")
            return False
        
        w = int.from_bytes(perf, 'little')
        if check_header_crc(w) and (w & 0xF) == TYPE_BEACON:
            self.perf_caps = Capabilities.from_lower28(w & 0x0FFFFFFF)
        else:
            self.perf_caps = self.ctrl_caps
        
        self.ctrl_caps.rx_max  = min(self.ctrl_caps.rx_max,  self.perf_caps.rx_max)
        self.ctrl_caps.txs_max = min(self.ctrl_caps.txs_max, self.perf_caps.txs_max)
        self.ctrl_caps.txa_max = min(self.ctrl_caps.txa_max, self.perf_caps.txa_max)
        
        self._tx(self.build_beacon(self.perf_caps), "ECHO")
        _ = self._read_exact(4, 0.1)
        
        self._tx(self.build_ping(), "PING")
        pong = self._read_exact(4, 0.5)
        if not pong or (pong[0] & 0x0F) != TYPE_PING:
            log.error("ERROR: Ping failed")
            return False
        
        self.connected = True
        log.info("Handshake OK")
        return True

    # ==== ========== ========== ========== ================ PACKET READING ==== ========== ========== ========== ========== ================
    def _read_packet(self, timeout=0.8):
        """Read ASPEP packet"""
        hdr = self._read_header_sync(timeout)
        if not hdr: return None
        
        w = int.from_bytes(hdr, 'little')
        lower28 = w & 0x0FFFFFFF
        ptype = lower28 & 0xF
        length = (lower28 >> 4) & 0x1FFF
        
        log.debug(f"RX type=0x{ptype:X} len={length}")
        
        if ptype == TYPE_SILENT:
            log.debug("SILENT")
            return {"type": TYPE_SILENT, "payload": b''}
        
        if ptype == TYPE_ERROR:
            payload = self._read_exact(length, timeout) if length else b''
            log.error(f"ERROR: {hx(payload)}")
            return {"type": TYPE_ERROR, "payload": payload}
        
        if ptype in (TYPE_DATA, TYPE_ACK, TYPE_NACK):
            payload = self._read_exact(length, timeout) if length else b''
            return {"type": ptype, "payload": payload}
        
        if ptype in (TYPE_BEACON, TYPE_PING):
            return {"type": ptype, "payload": b''}
        
        return {"type": ptype, "payload": b''}

    # ====== ========== ========== ============== COMMAND SENDING ======== ========== ========== ============ ========== ==========
    def _send_data_command(self, payload: bytes, label: str,
                           expect_data: bool,
                           expect_string: bool = False,
                           allow_ack_only: bool = False,
                           data_timeout: float = 1.5):
        """Send DATA command"""
        
        hdr = self.build_data_header(len(payload)) # 4-byte header
        log.info(f"CMD {label}: {hx(payload)}")
        
        self._tx(hdr, f"{label}_H")  # Send header via serial
        if payload:
            time.sleep(0.0008)
            self._tx(payload, f"{label}_P")
        
        first = self._read_packet(timeout=0.8)
        if not first:
            log.error(f"ERROR: {label}: No response")
            return False
        
        if first["type"] == TYPE_SILENT:
            first = self._read_packet(timeout=0.8)
            if not first:
                log.error(f"ERROR: {label}: No response after SILENT")
                return False
        
        if first["type"] == TYPE_ERROR:
            log.error(f"ERROR: {label}: ERROR")
            return False
        
        if first["type"] == TYPE_NACK:
            log.error(f"ERROR: {label}: NACK")
            return False
        
        if first["type"] == TYPE_DATA:
            self.last_data_payload = first["payload"]
            self._log_payload(label, expect_string)
            return True
        
        if first["type"] == TYPE_ACK:
            if first["payload"]:
                self.last_data_payload = first["payload"]
                self._log_payload(label, expect_string)
                return True
            
            if not expect_data:
                log.info(f"OK: {label}")
                return True
            
            end = time.time() + data_timeout
            while time.time() < end:
                pkt = self._read_packet(timeout=0.5)
                if not pkt: continue
                
                if pkt["type"] == TYPE_SILENT: continue
                if pkt["type"] == TYPE_ERROR:
                    log.error(f"ERROR: {label}: Late ERROR")
                    return False
                if pkt["type"] == TYPE_DATA:
                    self.last_data_payload = pkt["payload"]
                    self._log_payload(label, expect_string)
                    return True
                if pkt["type"] == TYPE_ACK and pkt["payload"]:
                    self.last_data_payload = pkt["payload"]
                    self._log_payload(label, expect_string)
                    return True
                if pkt["type"] == TYPE_NACK:
                    log.error(f"ERROR: {label}: Late NACK")
                    return False
            
            if allow_ack_only:
                log.info(f"OK: {label} (ACK only)")
                self.last_data_payload = b''
                return True
            
            log.error(f"ERROR: {label}: Timeout waiting for DATA")
            return False
        
        log.error(f"ERROR: {label}: Unexpected type 0x{first['type']:X}")
        return False

    def _log_payload(self, label: str, expect_string: bool):
        """Log payload"""
        if expect_string:
            txt = self.last_data_payload.rstrip(b"\x00").decode(errors="ignore")
            log.info(f"OK: {label}: '{txt}'")
        else:
            log.info(f"OK: {label}: {len(self.last_data_payload)} bytes")

    # ================================================== SPEED SCALING CONFIGURATION ======================================================================
    def set_max_speed(self, max_speed_rpm: int):
        """Set maximum speed for percentage conversion"""
        self._max_speed_rpm = max_speed_rpm
        log.info(f"Max speed set to {max_speed_rpm} RPM")

    def set_acceleration(self, acceleration_rpm_s: float):
        """Set acceleration rate in RPM per second"""
        self._acceleration_rpm_s = acceleration_rpm_s
        log.info(f"Acceleration set to {acceleration_rpm_s} RPM/s")

    def set_speed_unit(self, unit: str):
        """Set speed unit (RPM or PERCENT)"""
        if unit.upper() in ["RPM", "PERCENT"]:
            self._speed_unit = unit.upper()
            log.info(f"Speed unit set to {self._speed_unit}")
        else:
            log.error("Speed unit must be 'RPM' or 'PERCENT'")

    def percentage_to_rpm(self, percentage: int) -> int:
        """Convert percentage to RPM"""
        rpm = int((percentage / 100.0) * self._max_speed_rpm)
        log.info(f"{percentage}% = {rpm} RPM (max: {self._max_speed_rpm} RPM)")
        return rpm

    def rpm_to_percentage(self, rpm: int) -> int:
        """Convert RPM to percentage"""
        percentage = int((rpm / self._max_speed_rpm) * 100)
        log.info(f"{rpm} RPM = {percentage}% (max: {self._max_speed_rpm} RPM)")
        return percentage

    # ======= ========== ========== = ====================== MOTOR COMMANDS ======= ========== ========== ========== =============
    def request_name(self):
        """Request motor name"""
        if not self.handshake(): return False
        
        formats = [
            ("F1", CMD_NAME.to_bytes(2, 'little') + (0x00E1).to_bytes(2, 'little')),
            ("F2", CMD_NAME.to_bytes(2, 'little')),
            ("F3", bytes([0x00]) + CMD_NAME.to_bytes(2, 'little')),
        ]
        
        for name, payload in formats:
            log.info(f"Name {name}")
            if self._send_data_command(payload, f"Name-{name}", expect_data=True, expect_string=True, data_timeout=2.0):
                return True
        
        log.error("ERROR: All name formats failed")
        return False

    def start_motor(self, motor_index: int = 1) -> bool:
        """Start motor using MCP command"""
        if not self.handshake(): return False
        
        mcp_header = START_MOTOR | (motor_index & MOTOR_MASK)
        payload = mcp_header.to_bytes(2, 'little')
        
        log.info(f"Starting motor {motor_index} (header=0x{mcp_header:04X})")
        return self._send_data_command(payload, "START_MOTOR", expect_data=False, allow_ack_only=True)

    def stop_motor(self, motor_index: int = 1) -> bool:
        """Stop motor using MCP command"""
        if not self.handshake(): return False
        
        mcp_header = STOP_MOTOR | (motor_index & MOTOR_MASK)
        payload = mcp_header.to_bytes(2, 'little')
        
        log.info(f"Stopping motor {motor_index}")
        return self._send_data_command(payload, "STOP_MOTOR", expect_data=False, allow_ack_only=True)

    # ====== ======== ============ ============== PHYSICALLY ACCURATE SPEED CONTROL ========= ========== =========== ========== ==========
    def set_speed_auto_ramp(self, target_rpm: int, motor_index: int = 1) -> bool:
        """
        AUTOMATIC ramp handling with PHYSICALLY ACCURATE formula:
        ramp_duration_ms = speed_change / acc_rpm_s * 1000
        """
        if not self.handshake():
            return False
        
        current_speed = self._last_speed_ref or 0
        speed_change = abs(target_rpm - current_speed)
        
        if speed_change == 0:
            # No change needed
            log.info(f"Speed unchanged: {target_rpm} RPM")
            return True
        
        # PHYSICALLY ACCURATE FORMULA: ramp_duration_ms = speed_change / acc_rpm_s * 1000
        ramp_duration_ms = int(speed_change / self._acceleration_rpm_s * 1000)
        
        # Ensure minimum ramp time for stability
        ramp_duration_ms = max(ramp_duration_ms, 500)  # Minimum 500ms # Ensure minimum ramp time for stability
        
        log.info(f" ♿➡️ AUTO-RAMP: {current_speed} → {target_rpm} RPM "
                 f"over {ramp_duration_ms}ms ({self._acceleration_rpm_s} RPM/s acceleration)")
        
        # Try RAW speed ramp first (prevents over-voltage)
        if self.set_speed_ramp_raw(target_rpm, ramp_duration_ms, motor_index):
            self._last_speed_ref = target_rpm
            return True
        
        # Fallback: Use step-wise approach if RAW ramp fails
        log.warning("RAW ramp failed, using step-wise fallback")
        if self._set_speed_stepwise(target_rpm, motor_index):
            self._last_speed_ref = target_rpm
            return True
        
        return False
    
   #converting Python commands into actual motor movements! 
    def set_speed_ramp_raw(self, target_rpm: int, ramp_duration_ms: int = 2000, motor_index: int = 1) -> bool:
        """
        Set speed with ramp using RAW data format - PREVENTS OVER-VOLTAGE FAULTS
        """
        if not self.handshake():
            return False
        
        # Calculate the actual register ID for this motor
        speed_ramp_reg = MC_REG_SPEED_RAMP_BASE | (motor_index & MOTOR_MASK)
        
        # Pack raw data: RPM (int32, little-endian) + Duration (uint16, little-endian)  PACK DATA: RPM (4 bytes) + Duration (2 bytes)
        raw_data = struct.pack('<iH', target_rpm, ramp_duration_ms)     # 3360 RPM = 0x200D in hex → b'\x0D\x20\x00\x00' (little-endian)
        raw_data_size = len(raw_data)  # Should be 6 bytes
        
        log.debug(f"Speed Ramp RAW: {target_rpm} RPM over {ramp_duration_ms}ms (reg=0x{speed_ramp_reg:04X})")
        
        # Build MCP command for RAW data register write
        mcp_cmd = MCP_CMD_WRITE_REG | (motor_index & MOTOR_MASK)
        
        # Try different payload formats
        formats = [
            # Format 1: Standard MCP write with raw data
            struct.pack('<HHH', mcp_cmd, speed_ramp_reg, raw_data_size) + raw_data,
            
            # Format 2: With motor index separate
            struct.pack('<BHHH', motor_index, MCP_CMD_WRITE_REG, speed_ramp_reg, raw_data_size) + raw_data,
            
            # Format 3: Alternative ordering
            struct.pack('<HH', mcp_cmd, speed_ramp_reg) + struct.pack('<H', raw_data_size) + raw_data,
        ]
        
        for i, payload in enumerate(formats, 1):
            log.debug(f"Trying format {i}: {hx(payload)}")
            
            ok = self._send_data_command(
                payload,
                f"SPEED_RAMP_RAW_{i}",
                expect_data=False,
                allow_ack_only=True,
                data_timeout=1.0
            )
            
            if ok:
                log.debug(f"✓ Speed ramp programmed: {target_rpm} RPM over {ramp_duration_ms}ms")
                return True
            else:
                log.debug(f"Format {i} failed, trying next...")
                time.sleep(0.1)
        
        log.error("✗ All speed ramp formats failed")
        return False

    def _set_speed_stepwise(self, target_rpm: int, motor_index: int = 1, step_size: int = 500, step_delay: float = 0.2) -> bool:
        """
        Step-wise speed transition as fallback when RAW ramp fails
        """
        current = self._last_speed_ref or 0
        
        if abs(target_rpm - current) <= step_size:
            # Small change, use direct command
            return self._set_speed_instant(target_rpm, motor_index)
        
        # Large change, step through speeds
        steps = abs(target_rpm - current) // step_size
        direction = 1 if target_rpm > current else -1
        
        log.info(f"Step-wise transition: {current} → {target_rpm} RPM in {steps} steps")
        
        for step in range(steps):
            intermediate = current + (direction * step_size * (step + 1))
            if not self._set_speed_instant(intermediate, motor_index):
                log.error(f"Step failed at {intermediate} RPM")
                return False
            time.sleep(step_delay)
        
        # Final target
        return self._set_speed_instant(target_rpm, motor_index)

      
    def _set_speed_instant(self, rpm: int, motor_index: int = 1) -> bool:
        """
        Set speed instantly (used only as fallback)
        """
        wire_motor = max(0, motor_index - 1)
        rpm_i32 = int(rpm)
        data4 = struct.pack('<i', rpm_i32)
        
        speed_ref_reg = MC_REG_SPEED_REF_BASE | (motor_index & MOTOR_MASK)
        reg_lo = speed_ref_reg & 0xFF
        reg_hi = (speed_ref_reg >> 8) & 0xFF
        
        log.debug(f"Set speed instant: {rpm} RPM (reg=0x{speed_ref_reg:04X})")
        
        formats = [
            bytes([MCP_CMD_WRITE_REG, wire_motor, reg_lo, reg_hi]) + data4,
            bytes([wire_motor, MCP_CMD_WRITE_REG, reg_lo, reg_hi]) + data4,
            bytes([wire_motor, MCP_CMD_WRITE_REG, 0x01, reg_lo, reg_hi]) + data4,
        ]
        
        for idx, p in enumerate(formats, 1):
            if self._send_data_command(p, f"SetSpeed_{idx}", expect_data=False, allow_ack_only=True):
                log.debug(f"Speed set (format {idx})")
                return True
            time.sleep(0.02)
        
        log.error("ERROR: Speed set failed")
        return False

    # ====== ========== ========== ============== OPERATOR-FACING SPEED COMMANDS ======== ========== ========== ========== ============
    def set_speed_rpm(self, rpm: int, motor_index: int = 1) -> bool:
        """Set speed with AUTOMATIC ramp handling"""
        return self.set_speed_auto_ramp(rpm, motor_index)

    def set_speed_percentage(self, percentage: int, motor_index: int = 1) -> bool:
        """Set speed as percentage with AUTOMATIC ramp handling"""
        rpm = self.percentage_to_rpm(percentage)
        return self.set_speed_auto_ramp(rpm, motor_index)

    # Legacy ramp commands (kept for compatibility)
    def program_speed_ramp(self, rpm: int, duration_ms: int, motor_index: int = 1):
        """Legacy speed ramp command"""
        return self.set_speed_ramp_raw(rpm, duration_ms, motor_index)

    def stop_ramp(self, motor_index: int = 1):
        """Stop ramp"""
        if not self.handshake(): return False
        return self._send_data_command(bytes([motor_index, CMD_STOP_RAMP]), "StopRamp", expect_data=False)

    def ramp_status(self, motor_index: int = 1):
        """Check ramp status"""
        if not self.handshake(): return False
        ok = self._send_data_command(
            bytes([motor_index, CMD_RAMP_STATUS]),
            "RampStatus",
            expect_data=True,
            allow_ack_only=True
        )
        if ok and self.last_data_payload:
            done = self.last_data_payload[0] != 0
            log.info(f"Ramp done: {done}")
            return done
        return False

    # =========== ========== ========== =================== REGISTER READING ============= ========== ========== ========== ========== ========== ======
    def poll_speed(self, motor_index: int = 1, repeat: int = 5, delay: float = 0.5) -> None:
        """Poll speed using WORKING MCP format"""
        
        speed_reg = MC_REG_SPEED_MEAS_BASE | (motor_index & MOTOR_MASK)
        
        log.info(f"Polling speed (reg=0x{speed_reg:04X})...")
        
        mcp_header = GET_DATA_ELEMENT | (motor_index & MOTOR_MASK)
        
        log.info(f"    MCP header: cmd=0x{GET_DATA_ELEMENT:02X} | motor={motor_index} = 0x{mcp_header:04X}")
        
        for i in range(repeat):
            payload = mcp_header.to_bytes(2, 'little') + speed_reg.to_bytes(2, 'little')
            
            log.info(f"Poll_{i+1}: {hx(payload)}")
            
            ok = self._send_data_command(
                payload,
                f"POLL_SPEED_{i+1}",
                expect_data=True,
                allow_ack_only=True,
                data_timeout=1.0
            )
            
            if ok and self.last_data_payload:
                raw = self.last_data_payload
                log.info(f"Response: {len(raw)}B = {hx(raw)}")
                
                if len(raw) >= 4:
                    speed_val = int.from_bytes(raw[:4], 'little', signed=True)
                    percentage = self.rpm_to_percentage(speed_val)
                    log.info(f"Speed: {speed_val} RPM = {percentage}% (ref={self._last_speed_ref})")
                    time.sleep(delay)
                    break
                elif len(raw) == 1:
                    log.error(f"ERROR: MCP Error: 0x{raw[0]:02X}")
                else:
                    log.warning(f"WARNING: Unexpected {len(raw)} bytes")
            
            time.sleep(delay)

    def read_faults(self, motor_index: int = 1) -> Optional[int]:
        """Read motor fault flags using WORKING MCP format"""
        if not self.handshake():
            return None
        
        faults_reg = MC_REG_FAULTS_BASE | (motor_index & MOTOR_MASK)
        mcp_header = GET_DATA_ELEMENT | (motor_index & MOTOR_MASK)
        
        payload = mcp_header.to_bytes(2, 'little') + faults_reg.to_bytes(2, 'little')
        
        log.info(f"Reading Faults (reg=0x{faults_reg:04X})")
        log.info(f"Read Faults: {hx(payload)}")
        
        ok = self._send_data_command(
            payload,
            "READ_FAULTS",
            expect_data=True,
            allow_ack_only=True,
            data_timeout=1.0
        )
        
        if ok and self.last_data_payload:
            raw = self.last_data_payload
            log.info(f"Response: {len(raw)}B = {hx(raw)}")
            
            if len(raw) >= 4:
                fault_flags = int.from_bytes(raw[:4], 'little', signed=False)
                log.info(f"Fault Flags: 0x{fault_flags:08X} (decimal: {fault_flags})")
                
                if fault_flags == 0:
                    log.info(f"No faults detected - System OK")
                else:
                    active_faults = []
                    for bit_value, fault_name in FAULT_NAMES.items():
                        if fault_flags & bit_value:
                            active_faults.append(fault_name)
                    
                    if active_faults:
                        log.warning(f"Active Faults: {', '.join(active_faults)}")
                        print("\n" + "="*70)
                        print("FAULT DETAILS:")
                        for fault in active_faults:
                            print(f"   * {fault}")
                        print("="*70 + "\n")
                    else:
                        log.info(f"WARNING: Unknown fault bits set: 0x{fault_flags:08X}")
                
                return fault_flags
            elif len(raw) == 1:
                log.error(f"ERROR: MCP Error: 0x{raw[0]:02X}")
        
        return None

    def fault_acknowledge(self, motor_index: int = 1) -> bool:
        """
        Acknowledge/clear motor faults using FAULT_ACK command
        """
        if not self.handshake():
            return False
        
        mcp_header = FAULT_ACK | (motor_index & MOTOR_MASK)
        payload = mcp_header.to_bytes(2, 'little')
        
        log.info(f"Acknowledging faults on motor {motor_index} (header=0x{mcp_header:04X})")
        log.info(f"FAULT_ACK: {hx(payload)}")
        
        ok = self._send_data_command(
            payload,
            "FAULT_ACK",
            expect_data=False,
            allow_ack_only=True,
            data_timeout=1.0
        )
        
        if ok:
            log.info("Fault acknowledge sent successfully")
            
            # Read faults again to verify they're cleared
            time.sleep(0.1)
            log.info("Verifying faults cleared...")
            remaining_faults = self.read_faults(motor_index)
            
            if remaining_faults == 0:
                log.info("All faults cleared")
                return True
            else:
                log.warning(f"WARNING: Some faults remain: 0x{remaining_faults:08X}")
                log.info("NOTE: Some faults may require condition to clear (e.g., voltage/temp)")
                return False
        
        log.error("ERROR: Fault acknowledge failed")
        return False

    def read_status(self, motor_index: int = 1):
        """Read motor status (8-bit register)"""
        if not self.handshake():
            return None
        
        status_reg = MC_REG_STATUS_BASE | (motor_index & MOTOR_MASK)
        mcp_header = GET_DATA_ELEMENT | (motor_index & MOTOR_MASK)
        
        payload = mcp_header.to_bytes(2, 'little') + status_reg.to_bytes(2, 'little')
        
        log.info(f"Reading Status (reg=0x{status_reg:04X})")
        
        ok = self._send_data_command(
            payload,
            "READ_STATUS",
            expect_data=True,
            allow_ack_only=True,
            data_timeout=1.0
        )
        
        if ok and self.last_data_payload:
            raw = self.last_data_payload
            
            if len(raw) >= 1:
                status = raw[0]
                
                status_names = {
                    0: "IDLE",
                    1: "IDLE_ALIGNMENT",
                    2: "ALIGNMENT",
                    3: "IDLE_START",
                    4: "START",
                    5: "START_RUN",
                    6: "RUN",
                    7: "ANY_STOP",
                    8: "STOP",
                    9: "STOP_IDLE",
                    10: "FAULT_NOW",
                    11: "FAULT_OVER",
                }
                
                status_name = status_names.get(status, f"UNKNOWN({status})")
                log.info(f"Motor State: {status_name}")
                
                return status
        
        return None

    def read_bus_voltage(self, motor_index: int = 1):
        """Read bus voltage (16-bit register)"""
        if not self.handshake():
            return None
        
        voltage_reg = MC_REG_BUS_VOLTAGE_BASE | (motor_index & MOTOR_MASK)
        mcp_header = GET_DATA_ELEMENT | (motor_index & MOTOR_MASK)
        
        payload = mcp_header.to_bytes(2, 'little') + voltage_reg.to_bytes(2, 'little')
        
        log.info(f"Reading Bus Voltage (reg=0x{voltage_reg:04X})")
        
        ok = self._send_data_command(
            payload,
            "READ_BUS_VOLTAGE",
            expect_data=True,
            allow_ack_only=True,
            data_timeout=1.0
        )
        
        if ok and self.last_data_payload:
            raw = self.last_data_payload
            
            if len(raw) >= 2:
                voltage = int.from_bytes(raw[:2], 'little', signed=False)
                log.info(f"Bus Voltage: {voltage} (raw units)")
                return voltage
        
        return None

    # ====== ========== ========== ========== ============== DIAGNOSTICS ========== ========== ========== ========== ==========
    def diagnostics(self, motor_index: int = 1):
        """Run comprehensive diagnostics"""
        if not self.handshake():
            return
        
        print("\n" + "="*70)
        print("COMPREHENSIVE MOTOR DIAGNOSTICS")
        print("="*70)
        
        print(f"\nSpeed Configuration:")
        print(f"  Max Speed: {self._max_speed_rpm} RPM")
        print(f"  Acceleration: {self._acceleration_rpm_s} RPM/s")
        print(f"  Speed Unit: {self._speed_unit}")
        print(f"  Auto-Ramp: ENABLED (Physically Accurate)")
        
        print("\nReading Motor Status...")
        self.read_status(motor_index)
        
        print("\nReading Fault Flags...")
        faults = self.read_faults(motor_index)
        
        if faults and faults != 0:
            print("\nNOTE: Faults detected! You can clear them with 'a' command (FAULT_ACK)")
        
        print("\nReading Bus Voltage...")
        self.read_bus_voltage(motor_index)
        
        print("\nReading Speed...")
        self.poll_speed(motor_index, repeat=1)
        
        print("\n" + "="*70)

    def sniff(self, seconds: float = 2.0):
        """Sniff raw data"""
        if not self.ser: return
        
        log.info(f"Sniffing {seconds}s...")
        end = time.time() + seconds
        raw = b''
        
        while time.time() < end:
            chunk = self.ser.read(self.ser.in_waiting or 1)
            if chunk: raw += chunk
        
        if raw:
            log.info(f"Data: {len(raw)}B: {hx(raw[:128])}")
        else:
            log.info("No data")

# ========== ========== ==== ================ ==================== CLI ============ ========== ========== ==================
def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="ASPEP/MCP Motor Control Client v6.0 - Physically Accurate Ramp",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--port", default="/dev/ttyS0", help="Serial port")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate")
    parser.add_argument("--motor", type=int, default=1, help="Motor index")
    parser.add_argument("--max-speed", type=int, default=6000, help="Maximum speed in RPM")
    parser.add_argument("--acceleration", type=float, default=1000.0, help="Acceleration in RPM/s")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    
    args = parser.parse_args()
    
    if args.debug:
        log.setLevel(logging.DEBUG)
    
    client = ASPEPClient(args.port, args.baud)
    client.set_max_speed(args.max_speed)
    client.set_acceleration(args.acceleration)
    motor = args.motor
    
    try:
        client.open()
        
        print("\n" + "="*70)
        print("  STM32 Motor Control v6.0 - PHYSICALLY ACCURATE RAMP")
        print("="*70)
        print(f"  Max Speed: {args.max_speed} RPM")
        print(f"  Acceleration: {args.acceleration} RPM/s")
        print("  AUTO-RAMP: ENABLED (Physically Accurate Formula)")
        print("\nCommands:")
        print("  h - handshake    n - name         s - start        t - stop")
        print("  v - velocity     V - velocity %   m - poll speed   f - read faults")
        print("  a - fault_ack    d - diagnostics  u - bus voltage  x - status")
        print("  M - set max RPM  A - set accel    U - set unit     sn - sniff")
        print("  q - quit")
        print("="*70)
        print("FORMULA: ramp_duration_ms = speed_change / acceleration * 1000")
        print("="*70 + "\n")
        
        while True:
            try:
                cmd = input("> ").strip().lower()
                
                if not cmd:
                    continue
                elif cmd == 'h':
                    client.handshake()
                elif cmd == 'n':
                    client.request_name()
                elif cmd == 's':
                    client.start_motor(motor)
                elif cmd == 't':
                    client.stop_motor(motor)
                elif cmd == 'v':
                    rpm = int(input("  RPM: "))
                    client.set_speed_rpm(rpm, motor)
                elif cmd == 'V':
                    percent = int(input("  Percentage (0-100): "))
                    client.set_speed_percentage(percent, motor)
                elif cmd == 'm':
                    client.poll_speed(motor)
                elif cmd == 'f':
                    client.read_faults(motor)
                elif cmd == 'a':
                    client.fault_acknowledge(motor)
                elif cmd == 'd':
                    client.diagnostics(motor)
                elif cmd == 'u':
                    client.read_bus_voltage(motor)
                elif cmd == 'x':
                    client.read_status(motor)
                elif cmd == 'M':
                    max_rpm = int(input("  Max RPM: "))
                    client.set_max_speed(max_rpm)
                elif cmd == 'A':
                    accel = float(input("  Acceleration (RPM/s): "))
                    client.set_acceleration(accel)
                elif cmd == 'U':
                    unit = input("  Unit (RPM/PERCENT): ").strip().upper()
                    client.set_speed_unit(unit)
                elif cmd == 'sn':
                    sec = float(input("  Seconds: ") or "2")
                    client.sniff(sec)
                elif cmd == 'q':
                    break
                else:
                    print(f"Unknown: {cmd}")
            
            except KeyboardInterrupt:
                print("\n\nInterrupted")
                break
            except Exception as e:
                log.error(f"ERROR: {e}", exc_info=args.debug)
    
    finally:
        client.close()
        print("\nGoodbye!\n")
