"""Application State - Extracted from JetUI"""

class AppState:
    """Centralized state management"""
    
    def __init__(self):
        # Power & Mode
        self.power_on = False
        self.paused = False
        self.mode = "P0"
        
        # Speed
        self.speed = 40
        self.speed_reference = 0
        self.speed_actual = 0
        
        # Timer
        self.timer_duration = 0
        self.remaining_time = 0
        self.timer_selecting = False
        self.timer_select_start = None
        self.running_elapsed = 0
        self.show_running = False
        
        # Training
        self.current_segment = 0
        self.surf_prep = False
        
        # Faults
        self.current_faults = 0x0000
        self.active_fault_list = []
        self.system_stalled = False
        
        # BLE
        self.bluetooth_connected = False
        self.paired_remotes = set()
        self.pairing_mode = False
        
        # WiFi
        self.wifi_connected = False
        self.wifi_connecting = False
        self.bt_connecting = False
        
        # Motor
        self.motor_ready = False
        
        # Internal timers
        self._power_default_id = None
        self._fault_display_index = 0
        self._press_start = {}
        self._power_long_timer_id = None
        self._power_long_done = False
        self._pre_pairing_count = 0
        self._pairing_blink_id = None
        self._mode_long_timer_id = None
        self.single_remote_mode = True