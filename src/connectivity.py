from __future__ import annotations

import asyncio
import binascii
import os
import re
import subprocess
import sys
import threading
import time
from typing import Callable, Dict, Optional, List, Set

BTHOME_UUID = "0000fcd2-0000-1000-8000-00805f9b34fb"

def _is_linux() -> bool:
    return sys.platform.startswith("linux")

class BLEUnavailableError(RuntimeError):
    pass

def _normalize_mac(mac: Optional[str]) -> Optional[str]:
    if not mac:
        return None
    return mac.upper()

class BTHomeShellyBridge:
    """
    BLE bridge for Shelly BLU Button devices using BTHome v2 advertisements (unencrypted).
    Emits per decoded event:
        {
          "type": "bthome",
          "gesture": "single|double|triple|long|hold|release|unknown",
          "button": 1..4 or None,
          "mac": "AA:BB:CC:DD:EE:FF",
          "rssi": -XX,
          "raw": "hexstring"
        }
    """

    def __init__(
        self,
        on_event: Callable[[Dict], None],
        device_name_filter: Optional[re.Pattern] = None,
        debug: bool = False,
    ) -> None:
        self._on_event = on_event
        self._device_name_filter = device_name_filter
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_evt = threading.Event()
        self._scanner = None
        self._debug = debug

        # Allowlist via env
        macs = os.getenv("ALLOWLIST_MACS", "").strip()
        self._allowlist: Set[str] = {m.strip().upper() for m in macs.split(",") if m.strip()}

        # Dedup: last packet_id per MAC
        self._last_packet_id: Dict[str, int] = {}

    # Public API
    def start(self) -> None:
        if not _is_linux():
            raise BLEUnavailableError("BLE scanning requires Linux/BlueZ.")
        if self._thread and self._thread.is_alive():
            return
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._run, name="BTHomeBLE", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_evt.set()
        if self._loop and self._loop.is_running():
            try:
                self._loop.call_soon_threadsafe(lambda: None)
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._thread = None
        self._loop = None
        self._scanner = None

    # Internal runner
    def _run(self) -> None:
        try:
            from bleak import BleakScanner
        except Exception as exc:
            raise BLEUnavailableError(f"Bleak not available: {exc}") from exc

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._scanner = BleakScanner(self._detection_cb)

        async def runner():
            await self._scanner.start()
            try:
                while not self._stop_evt.is_set():
                    await asyncio.sleep(0.25)
            finally:
                try:
                    await self._scanner.stop()
                except Exception:
                    pass

        try:
            self._loop.run_until_complete(runner())
        finally:
            try:
                self._loop.close()
            except Exception:
                pass

    # Advertisement callback
    def _detection_cb(self, device, advertisement_data):  # type: ignore[no-untyped-def]
        if self._stop_evt.is_set():
            return

        if self._device_name_filter and device.name:
            if not self._device_name_filter.search(device.name):
                return

        mac = _normalize_mac(getattr(device, "address", None))
        if self._allowlist and mac and mac not in self._allowlist:
            return

        service_data: Dict[str, bytes] = getattr(advertisement_data, "service_data", {}) or {}
        payload = service_data.get(BTHOME_UUID)
        if not payload:
            # attempt case-insensitive fallback
            for k, v in service_data.items():
                if k.lower() == BTHOME_UUID:
                    payload = v
                    break
        if not payload:
            return

        raw_hex = binascii.hexlify(payload).decode()

        # First try proper BTHome v2 minimal parse
        event_dict = self._parse_bthome_v2(payload)
        # Fallback to legacy parse if nothing decoded
        if not event_dict.get("button") and not event_dict.get("gesture"):
            legacy_events = self._legacy_tlv_parse(payload)
            # Emit each if any
            for ev in legacy_events:
                self._emit_event(ev, mac, advertisement_data, raw_hex)
            if legacy_events:
                return

        # If we got a packet_id perform dedup
        packet_id = event_dict.get("packet_id")
        if mac and isinstance(packet_id, int):
            if self._last_packet_id.get(mac) == packet_id:
                return
            self._last_packet_id[mac] = packet_id

        self._emit_event(event_dict, mac, advertisement_data, raw_hex)

    def _emit_event(self, ev: Dict, mac: Optional[str], advertisement_data, raw_hex: str):
        button = ev.get("button")
        gesture = ev.get("gesture") or "unknown"
        if self._debug:
            print(f"DEBUG BLE mac={mac} pid={ev.get('packet_id')} btn={button} gest={gesture} raw={raw_hex}")
        out = {
            "type": "bthome",
            "gesture": gesture,
            "button": button,
            "mac": mac,
            "rssi": getattr(advertisement_data, "rssi", None),
            "raw": raw_hex,
        }
        try:
            self._on_event(out)
        except Exception as e:
            if self._debug:
                print(f"BLE callback error: {e}")

    # Proper minimal BTHome v2 parse (unencrypted only)
    def _parse_bthome_v2(self, payload: bytes) -> Dict:
        """
        BTHome v2 fixed-length object parser (simple subset):
          device_info (1B):
            bits5..7 version (expect 2)
            bit0 encryption flag
          sequence of [id][value] 1-byte pairs:
            0x00 packet_id
            0x01 battery
            0x3A event (may appear multiple times)
            0x60 channel (button index)
        If channel absent, treat sequential 0x3A occurrences as slots 1..4.
        """
        out: Dict[str, Optional[int | str]] = {}
        if not payload:
            return out

        device_info = payload[0]
        version = (device_info >> 5) & 0x07
        encrypted = (device_info & 0x01) == 0x01
        if version != 2 or encrypted:
            return out  # unsupported here

        i = 1
        packet_id: Optional[int] = None
        channel: Optional[int] = None
        events: List[int] = []
        # Parse pairs
        while i + 1 < len(payload):
            obj_id = payload[i]
            val = payload[i + 1]
            i += 2
            if obj_id == 0x00:
                packet_id = val
            elif obj_id == 0x60:
                channel = val
            elif obj_id == 0x3A:
                events.append(val)
            elif obj_id == 0x01:
                # battery = val  # keep if needed
                pass
            else:
                # Unknown; ignore
                pass

        button: Optional[int] = None
        gesture: Optional[str] = None

        if channel and 1 <= channel <= 4:
            button = channel
            if events:
                # last non-zero event
                code = next((e for e in reversed(events) if e != 0), 0)
                gesture = _map_bthome_event_code(code)
        else:
            # Slot model
            for idx, code in enumerate(events[:4]):
                if code != 0:
                    button = idx + 1
                    gesture = _map_bthome_event_code(code)
                    break

        if packet_id is not None:
            out["packet_id"] = packet_id
        if button:
            out["button"] = button
        if gesture:
            out["gesture"] = gesture
        return out

    # Legacy TLV fallback (less accurate)
    def _legacy_tlv_parse(self, payload: bytes) -> List[Dict]:
        """
        Fallback parser treating stream as TLV [id][len][value...] (not spec-accurate).
        Returns list of events (button increments per event object).
        
        """
        events: List[Dict] = []
        if len(payload) < 3:
            return events
        # Assume first byte = flags / device_info
        i = 1
        button_num = 1
        while i + 1 < len(payload):
            obj_id = payload[i]
            if i + 1 >= len(payload):
                break
            length = payload[i + 1]
            i += 2
            if i + length > len(payload):
                break
            val = payload[i:i + length]
            i += length
            if obj_id == 0x3A and length >= 1 and val[0] != 0:
                events.append({"button": button_num, "gesture": _map_bthome_event_code(val[0])})
                button_num += 1
            elif obj_id in (0x3B, 0x45) and length >= 1 and val[0] != 0:
                events.append({"button": button_num, "gesture": _map_bthome_event_code(val[0])})
                button_num += 1
        return events

def _map_bthome_event_code(code: int) -> str:
    return {
        0x00: "none",
        0x01: "single",
        0x02: "double",
        0x03: "triple",
        0x04: "long",
        0x05: "release",
        0x06: "hold",
        0x80: "hold",
    }.get(code, f"unknown:{code:02x}")

class ConnectivityManager:
    """
    Exposes BLE start/stop and (future) Wi-Fi helpers.
    """

    def __init__(
        self,
        on_ble_event: Optional[Callable[[Dict], None]] = None,
        ble_name_regex: Optional[str] = None,
        debug: bool = False,
    ) -> None:
        self._on_ble_event = on_ble_event or (lambda e: None)
        name_filter = re.compile(ble_name_regex) if ble_name_regex else None
        self._ble = BTHomeShellyBridge(
            on_event=self._on_ble_event,
            device_name_filter=name_filter,
            debug=debug,
        )

    def start_ble(self) -> None:
        self._ble.start()

    def stop_ble(self) -> None:
        self._ble.stop()

    # Wi-Fi stubs (can expand later)
    def wifi_enable(self, enable: bool) -> bool:
        if not _is_linux():
            return False
        try:
            _run(f"rfkill {'unblock' if enable else 'block'} wlan")
            return True
        except Exception:
            return False

    def wifi_connect(self, ssid: str, psk: str) -> bool:
        if not _is_linux():
            return False
        if _has_cmd("nmcli"):
            try:
                _run(f'nmcli dev wifi connect "{ssid}" password "{psk}"')
                return True
            except Exception:
                return False
        return False

def _has_cmd(cmd: str) -> bool:
    from shutil import which
    return which(cmd) is not None

def _run(cmd: str) -> Optional[str]:
    try:
        proc = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = proc.stdout.decode(errors="ignore").strip()
        return out if out else None
    except subprocess.CalledProcessError:
        return None

# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Connectivity (BLE BTHome) scanner")
    parser.add_argument("--scan", action="store_true", help="Run BLE scanner and print events")
    parser.add_argument("--filter", type=str, default="Shelly|SBBT|BLU", help="Regex device name filter")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    if args.scan:
        def _printer(evt: Dict):
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] BLE {evt.get('mac')} RSSI {evt.get('rssi')}: button={evt.get('button')} gesture={evt.get('gesture')} raw={evt.get('raw')}")

        try:
            cm = ConnectivityManager(on_ble_event=_printer, ble_name_regex=args.filter, debug=args.debug)
            cm.start_ble()
            print("Scanning... Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}")
        finally:
            try:
                cm.stop_ble()
            except Exception:
                pass