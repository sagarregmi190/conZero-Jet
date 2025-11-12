import serial
import time
from datetime import datetime

def ts():
    return datetime.now().strftime("%H:%M:%S.%f")

def hx(b: bytes) -> str:
    return ' '.join(f"{x:02x}" for x in b)

class AdaptiveMotorPilot:
    # Handshake frames (observed)
    BEACON_INIT = bytes.fromhex("15 c7 01 94")
    BEACON_ECHO = bytes.fromhex("05 c7 01 14")
    PING        = bytes.fromhex("06 00 00 60")
    # Optional ping response example (36 00 00 90) not needed to send
    # Commands
    REQ_NAME = bytes.fromhex("49 00 00 70 11 00 e1 00")
    START    = bytes.fromhex("29 00 00 e0 19 00")
    STOP     = bytes.fromhex("29 00 00 e0 21 00")
    ACK_PREFIX = b"\x1a\x00\x00"       # Start/Stop ack begins with 1a 00 00 20 00

    def __init__(self, port="/dev/ttyS0", baud=115200):
        self.port = port
        self.baud = baud
        self.ser: serial.Serial | None = None
        self.connected = False
        self.name_cached = None

    # ---------- Low level ----------
    def open(self):
        self.ser = serial.Serial(
            self.port,
            self.baud,
            timeout=0.02,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            rtscts=False,
            dsrdtr=False
        )
        print(f"{ts()} Port open {self.port} @{self.baud}")
        return True

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def _drain(self, dwell=0.02):
        if not self.ser:
            return b''
        time.sleep(dwell)
        data = b''
        while True:
            n = self.ser.in_waiting
            if not n:
                break
            data += self.ser.read(n)
        return data

    def _wait_quiet(self, quiet_ms=40):
        # Wait until line stays empty for quiet_ms
        deadline = time.time() + 2
        while time.time() < deadline:
            if self.ser.in_waiting == 0:
                time.sleep(quiet_ms / 1000.0)
                if self.ser.in_waiting == 0:
                    return
            else:
                self._drain(0.01)
        return

    def _send_frame(self, frame: bytes, response_wait=0.12, min_resp=1, retry=True):
        if not self.ser:
            return b''
        self.ser.reset_input_buffer()
        print(f"{ts()} -->Tx {hx(frame)}")
        self.ser.write(frame)
        self.ser.flush()
        rx = self._collect(response_wait)
        if len(rx) < min_resp and retry:
            # One silent retry after short backoff
            time.sleep(0.06)
            self.ser.reset_input_buffer()
            print(f"{ts()} --RETRY-->Tx {hx(frame)}")
            self.ser.write(frame)
            self.ser.flush()
            rx = self._collect(response_wait)
        if rx:
            print(f"{ts()} <--Rx {hx(rx)}")
        else:
            print(f"{ts()} <--Rx (none)")
        return rx

    def _collect(self, window):
        end = time.time() + window
        buf = b''
        while time.time() < end:
            if self.ser.in_waiting:
                buf += self.ser.read(self.ser.in_waiting)
            else:
                time.sleep(0.005)
        return buf

    # ---------- Handshake ----------
    def handshake(self):
        if self.connected:
            return True
        # Ensure line is idle
        self._drain(0.05)
        self._wait_quiet()
        print("\nHandshake start")
        r1 = self._send_frame(self.BEACON_INIT, response_wait=0.15, min_resp=4)
        if len(r1) < 4 or r1[:4] != self.BEACON_ECHO:
            print("Unexpected BEACON response; abort")
            return False
        r2 = self._send_frame(self.BEACON_ECHO, response_wait=0.12, min_resp=4)
        if r2[:4] != self.BEACON_ECHO:
            print("Echo BEACON mismatch; abort")
            return False
        r3 = self._send_frame(self.PING, response_wait=0.15, min_resp=4)
        if len(r3) < 4:
            print("No PING reply")
            return False
        # Stabilize: board sometimes needs a short idle gap before first command
        self._wait_quiet(quiet_ms=80)
        self.connected = True
        print("Handshake complete")
        return True

    # ---------- Higher level ----------
    def ensure_link(self):
        if not self.ser or not self.ser.is_open:
            self.open()
        if not self.connected:
            if not self.handshake():
                return False
        # Prime with name request once (improves next command reliability)
        if self.name_cached is None:
            self.request_name()
            # Quiet gap
            self._wait_quiet(quiet_ms=60)
        return True

    def request_name(self):
        if not self.ensure_link():
            return None
        r = self._send_frame(self.REQ_NAME, response_wait=0.25, min_resp=8)
        if len(r) >= 6:
            payload = r[4:]  # drop simple ack header (if any)
            # Extract until double zero or end
            seg = payload.split(b"\x00\x00")[0]
            try:
                name = seg.decode(errors="ignore").strip()
            except:
                name = ""
            if name:
                self.name_cached = name
                print(f"Motor name: {name}")
            return name
        return None

    def start(self):
        if not self.ensure_link():
            return False
        r = self._send_frame(self.START, response_wait=0.18, min_resp=4)
        ok = r.startswith(self.ACK_PREFIX)
        print("Motor started" if ok else "Start failed")
        return ok

    def stop(self):
        if not self.ensure_link():
            return False
        r = self._send_frame(self.STOP, response_wait=0.18, min_resp=4)
        ok = r.startswith(self.ACK_PREFIX)
        print("Motor stopped" if ok else "Stop failed")
        return ok

# ---------- CLI ----------
def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyS0")
    ap.add_argument("--baud", type=int, default=115200)
    args = ap.parse_args()

    ctl = AdaptiveMotorPilot(port=args.port, baud=args.baud)
    try:
        ctl.open()
        ctl.handshake()
        ctl.request_name()
        while True:
            cmd = input("\n[s]tart [t]op [n]ame [q]uit: ").strip().lower()
            if cmd == 's':
                ctl.start()
            elif cmd == 't':
                ctl.stop()
            elif cmd == 'n':
                ctl.request_name()
            elif cmd == 'q':
                break
    finally:
        ctl.close()

if __name__ == "__main__":
    main()