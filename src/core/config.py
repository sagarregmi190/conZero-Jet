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
    'power': 3,    # ON/OFF
    'mode': 23,     # MODE
    'timer': 16,    # TIMER
    'speed':6,     #SPEED
    'led':27, # LED 
   
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
    # Sleek, futuristic title font (great for app name or mode headings)
    "title": ("Montserrat SemiBold", 20, "bold"),

    # Clean modern label font — thin, minimal for SPEED / TIMER / MODE titles
    "label": ("Rajdhani SemiBold", 13),

    # Larger data values — bold and clear, ideal for % and timer numbers
    "value": ("Orbitron Bold", 28, "bold"),

    # Status / sublabels like "RUN: 00:51"
    "status": ("Roboto Medium", 16),

    # Button text — compact but crisp
    "button": ("Inter SemiBold", 10),

    # Small test/debug text
    "test_label": ("Consolas", 9)
}

# --- UI dimensions ---
UI_DIMENSIONS = {
    "window_size": "480x320",
    "header_padx": 8,                    # ADDED THIS
    "header_pady": (4, 0),               # ADDED THIS
    "shadow_height": 320,                # full screen
    "shadow_width": 480,
    "display_height": 180,               # CHANGED from 320 to 180
    "display_padx": 3,                   # CHANGED from 0 to 3
    "display_pady": (1, 1)               # CHANGED from (0, 0) to (1, 1)
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

# UART Manger and Faults code and all handles 
# Fault register bit mapping
FAULT_NAMES = {
    0x0001: "FOC DURATION",
    0x0002: "OVER VOLTAGE",
    0x0004: "UNDER VOLTAGE",
    0x0008: "OVER TEMPERATURE",
    0x0010: "START UP_FAILURE",
    0x0020: "SPEED FEEDBACK",
    0x0040: "OVER CURRENT",
    0x0080: "SOFTWARE ERROR",
    0x0400: "DRIVER PROTECTION",    
}

STALL_FAULTS = (
    0x0400 |  # DRIVER_PROTECTION - Hardware issue
    0x0008 |  # OVER_TEMPERATURE - Must cool down
    0x0010    # START_UP_FAILURE - Mechanical block/wrong parameters
)

CLEARABLE_FAULTS = (
    0x0001 |  # FOC_DURATION
    0x0002 |  # OVER_VOLTAGE
    0x0004 |  # UNDER_VOLTAGE
    0x0020 |  # SPEED_FEEDBACK
    0x0040 |  # OVER_CURRENT
    0x0080    # SOFTWARE_ERROR
)

# UI color scheme for fault states
FAULT_COLORS = {
    "active": "#ff5555",    # Red for active faults
    "warning": "#ff9800",   # Orange for warnings
    "normal": "#2798AA"     # Teal for normal operation
}

PATHS = {
    "paired_remotes": "/home/pi/conzero-jet-project/paired_remotes.json",
    "icon_bt_off": "/home/pi/conzero-jet-project/icons/ble_off.png",
    "icon_bt_on": "/home/pi/conzero-jet-project/icons/ble_On.png",
    "icon_wifi_off": "/home/pi/conzero-jet-project/icons/Off_Wifi.png",
    "icon_wifi_on": "/home/pi/conzero-jet-project/icons/On_Wifi.png"
}

# Motor speed conversion factor
SPEED_PERCENT_TO_RPM_FACTOR = 48  # 100% = 5000 RPM

# UI timing intervals (milliseconds)
TIMING = {
    "motor_init_delay": 200,           # Delay before motor init
    "fault_check_interval": 2000,      # Fault monitoring frequency
    "speed_check_interval": 1000,      # Speed monitoring frequency
    "fault_cycle_interval": 10000,     # Multi-fault display cycle time
    "pairing_blink_interval": 500,     # BLE pairing icon blink
    "finish_flash_interval": 500,      # Timer finish animation
    "auto_poweroff_delay": 30 * 60 * 1000,  # 30 minutes in milliseconds
    "power_default_delay": 3000,       # Auto-enter P0 mode after power on
    "mode_long_press": 3000,           # MODE button long press for pairing
    "pairing_timeout": 30000,          # Pairing mode auto-disable
    "status_clear_delay": 2000         # Clear status message delay
}

