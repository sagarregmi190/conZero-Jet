"""
Multi-language translations for conZero-Jet (English and German)

- Use LanguageManager.set_language("de") or .set_language("en")
- Use t("key", **kwargs) to get translated strings.
"""

from typing import Dict

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # UI labels
    
    "fault.critical_required": {"en": "CRITICAL FAULT", "de": "KRITISCHER FEHLER"},
    "fault.clear_failed": {"en": "FAULT CLEAR FAIL", "de": "FEHLER LÖSCHEN FEHLER"},

    "fault.cleared": {"en": "FAULTS CLEARED", "de": "FEHLER GELÖSCHT"},
    
    "ui.speed": {"en": "SPEED", "de": "SPEED"},
    "ui.timer": {"en": "TIMER", "de": "TIMER"},
    "ui.mode": {"en": "MODE", "de": "MODE"},
    "ui.run": {"en": "RUN", "de": "LAUF"},

    # Buttons / Touch labels
    "button.power": {"en": "POWER", "de": "EIN/AUS"},
    "button.mode": {"en": "MODE", "de": "MODUS"},
    "button.timer": {"en": "TIMER", "de": "ZEITSCHALTUHR"},
    "button.speed": {"en": "SPEED", "de": "GESCHWINDIGKEIT"},
    "button.pause": {"en": "PAUSE", "de": "PAUSE"},
    "button.resume": {"en": "RESUME", "de": "FORTSETZEN"},

    # Status messages
    "status.power_on": {"en": "Power ON", "de": "Eingeschaltet"},
    "status.power_off": {"en": "Power OFF", "de": "Ausgeschaltet"},
    "status.paused": {"en": "Paused", "de": "Pausiert"},
    "status.running": {"en": "Running", "de": "Läuft"},
    "status.shutdown": {"en": "SHUTDOWN", "de": "HERUNTERFAHREN"},
    "status.motor_link_fail": {"en": "MOTOR LINK FAIL", "de": "MOTOR VERBINDUNG FEHLER"},
    "status.start_err": {"en": "START ERR", "de": "START FEHLER"},
    "status.stop_err": {"en": "STOP ERR", "de": "STOPP FEHLER"},


    # BLE / WiFi / Pairing
    "ble.connecting": {"en": "BT Connecting...", "de": "BT verbinden..."},
    "ble.connected": {"en": "BT Connected", "de": "BT verbunden"},
    "ble.pairing_mode": {
        "en": "Press Remote Button",
        "de": "Fernbedienung drücken"
    },
    "ble.learn_mode": {"en": "Press Remote Button", "de": "Fernbedienung drücken"},
    "ble.remote_connected": {"en": "Remote Ready", "de": "Fernbedienung bereit"},
    "ble.remote_paired": {"en": "Paired!", "de": "Gekoppelt!"},
    "ble.remote_replaced": {"en": "Replaced!", "de": "Ersetzt!"},
    "ble.pairing_ended": {"en": "No Remote", "de": "Keine Fernbedienung"},
    
    # WiFi
    "wifi.connecting": {"en": "Connecting WiFi...", "de": "WLAN wird verbunden..."},
    "wifi.connected": {"en": "WiFi Connected", "de": "WLAN verbunden"},

    # Fault message formats
    "fault.single_format": {"en": "FAULT: {fault}", "de": "FEHLER: {fault}"},
    "fault.multiple_format": {"en": "FAULTS ({count}):", "de": "FEHLER ({count}):"},

    # Fault names (map to your FAULT_NAMES entries)
    "fault.foc_duration": {"en": "FOC DURATION", "de": "FOC DAUER"},
    "fault.over_voltage": {"en": "OVER VOLTAGE", "de": "ÜBERSPANNUNG"},
    "fault.under_voltage": {"en": "UNDER VOLTAGE", "de": "UNTERSPANNUNG"},
    "fault.over_temperature": {"en": "OVER TEMPERATURE", "de": "ÜBERTEMPERATUR"},
    "fault.startup_fail": {"en": "START UP_FAILURE", "de": "STARTFEHLER"},
    "fault.speed_feedback": {"en": "SPEED FEEDBACK", "de": "GESCHWINDIGKEITSRÜCKMELDUNG"},
    "fault.over_current": {"en": "OVER CURRENT", "de": "ÜBERSTROM"},
    "fault.software_error": {"en": "SOFTWARE ERROR", "de": "SOFTWAREFEHLER"},
    "fault.driver_protection": {"en": "DRIVER PROTECTION", "de": "TREIBERSCHUTZ"},

    # Mode descriptions (from manual)
    "mode.p0_desc": {"en": "Free Mode", "de": "Freier Modus"},
    "mode.t_desc": {"en": "Timer Mode", "de": "Zeitschaltuhr"},
    "mode.p1_desc": {"en": "Easy Training", "de": "Leichtes Training "},
    "mode.p2_desc": {"en": "Medium Training", "de": "Mittleres Training"},
    "mode.p3_desc": {"en": "Hard Training", "de": "Schweres Training"},
    "mode.p4_desc": {"en": "Endurance Training", "de": "Ausdauertraining"},
    "mode.p5_desc": {"en": "Surf Mode", "de": "Surf-Modus"},
    "mode.p1_short": {"en":"P1", "de":"P1"},
    "mode.p2_short": {"en":"P2", "de":"P2"},
    "mode.p3_short": {"en":"P3", "de":"P3"},
    "mode.p4_short": {"en":"P4", "de":"P4"},
    "mode.p5_short": {"en":"P5", "de":"P5"},

    # UI hints and help short strings
    "help.open_manual": {"en": "Open Manual", "de": "Handbuch öffnen"},
    "help.faq": {"en": "FAQ & Solutions", "de": "FAQ & Lösungen"},

    # Safety & warnings (short labels)
    "warn.general": {"en": "Read the manual and observe safety instructions.", "de": "Lesen Sie das Handbuch und beachten Sie die Sicherheitshinweise."},
    "warn.risk": {"en": "DANGER: Do not insert objects into the deflector outlet.", "de": "GEFAHR: Führen Sie keine Fremdkörper in die Steckdose des Deflektorgehäuses ein."},
}

# Language manager and helper
class LanguageManager:
    _instance = None
    _current_language = "en"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def set_language(cls, lang_code: str):
        if lang_code not in ("en", "de"):
            print(f"[LanguageManager] Unsupported language {lang_code}, defaulting to en")
            cls._current_language = "en"
        else:
            cls._current_language = lang_code
            print(f"[LanguageManager] Language set to {lang_code}")

    @classmethod
    def get_language(cls) -> str:
        return cls._current_language

    @classmethod
    def t(cls, key: str, **kwargs) -> str:
        entry = TRANSLATIONS.get(key)
        if not entry:
            # If key missing, return key for debugging
            print(f"[LanguageManager] Missing translation key: {key}")
            return key
        text = entry.get(cls._current_language) or entry.get("en") or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception as e:
                print(f"[LanguageManager] Translation format error for key {key}: {e}")
                return text
        return text

# Convenience function
def t(key: str, **kwargs) -> str:
    return LanguageManager.t(key, **kwargs)