##config.py configuration for 3.5 inc display 

#screen dimension 
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 320

#Colors palette for the UI 

COLORS={
    "bg": "#232b2f",
    "display_bg": "#232b2f",
    "text": "#ffffff",
    "primary": "#ffffff",
    "accent": "#ffffff",
    "button_bg": "#2c2c2c",
    "button_active": "#3c3c3c",
    "connected": "#4caf50",
    "disconnected": "#cccccc"
}


#Training plans for different modes (durations in seconds , speed %)
TRAINING_PLANS = {
    "P1": [(120, 20), (180, 30), (60, 20), (180, 35), (60, 20), (180, 30), (120, 20)],
    "P2": [(180, 45), (180, 55), (120, 45), (240, 70), (60, 45), (240, 55), (180, 45)],
    "P3": [(300, 70), (240, 80), (60, 70), (240, 85), (60, 70), (300, 80), (300, 70)],
    "P4": [(420, 45), (960, 65), (360, 45)]
}


# Default durations for each mode (in seconds)
MODE_DURATIONS = {
    "P1": 15 * 60,
    "P2": 20 * 60,
    "P3": 25 * 60,
    "P4": 30 * 60,
    "P5": 0,
    "P0": 0,
    "T": 0
}

# GPIO pin mapping for hardware buttons
GPIO_PINS = {
    'power': 17,    # ON/OFF
    'mode': 27,     # MODE
    'timer': 22,    # TIMER
    'speed': 5,     # SPEED
    'pause': 6      # Pause/Resume
}

# --- Timer options (minutes) ---
TIMER_OPTIONS = [15, 30, 45, 60, 75, 90]

# --- Speed presets (% values) ---
SPEED_PRESETS = [20, 40, 60, 80, 100]

# --- Mode names/descriptions ---
MODE_NAMES = {
    "P0": "P0",
    "T": "T",
    "P1": "P1",
    "P2": "P2",
    "P3": "P3",
    "P4": "P4",
    "P5": "P5"
}

# --- Font settings ---
FONTS = {
    "title": ("Helvetica", 18, "bold"),
    "label": ("Segoe UI", 11),
    "value": ("Segoe UI", 22, "bold"),
    "status": ("Segoe UI", 14),
    "button": ("Segoe UI", 9),
    "test_label": ("Arial", 8)
}

# --- UI dimensions ---
UI_DIMENSIONS = {
    "window_size": "480x320",
    "header_padx": 8,
    "header_pady": (4, 0),
    "shadow_height": 200,
    "shadow_width": 440,
    "display_height": 180,
    "display_padx": 3,
    "display_pady": (1, 1)
}

# --- Default values ---
DEFAULTS = {
    "speed": 40,
    "mode": "P0",
    "timer": 0
}

# --- Status messages ---
STATUS_MESSAGES = {
    "bt_connecting": "Connecting Bluetooth...",
    "bt_connected": "Bluetooth Connected",
    "wifi_connecting": "Connecting WiFi...",
    "wifi_connected": "WiFi Connected",
    "power_on": "Power ON",
    "power_off": "Power OFF",
    "paused": "Paused",
    "running": "Running"
}

LONG_PRESS_MS = 600 #hold time threshold for long press 