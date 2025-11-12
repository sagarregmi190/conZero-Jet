import os 
import time
import json
import subprocess
import tkinter as tk 
from tkinter import PhotoImage
from hardware.connectivity import ConnectivityManager
from hardware.wave import WaveAnimation

# Import Configuration and helpers 
from core.config import (COLORS, TRAINING_PLANS, SPEED_PRESETS, GPIO_PINS, MODE_DURATIONS, 
                   MODE_NAMES, FONTS, UI_DIMENSIONS, DEFAULTS, TIMER_OPTIONS,FAULT_NAMES,STALL_FAULTS,CLEARABLE_FAULTS,FAULT_COLORS,
                   SPEED_PERCENT_TO_RPM_FACTOR,PATHS)
from hardware.gpio_handler import GPIOHandler
from core.mode_manager import ModeManager
from hardware.uart_manager import ASPEPClient

class JetUI:
    def __init__(self, root):
        self.root = root
        self.root.title("conZero-Jet")
        self.root.geometry(UI_DIMENSIONS["window_size"])
        self.root.configure(bg=COLORS["bg"])
        
        # State Variables 
        self.power_on = False
        self.mode = DEFAULTS["mode"]
        self.speed = DEFAULTS["speed"]
        self.timer_duration = DEFAULTS["timer"]
        self.remaining_time = 0
        self.timer_selecting = False
        self.timer_select_start = None
        self.timer_options = TIMER_OPTIONS
        self.paused = False
        self.training_plans = TRAINING_PLANS.copy()
        self.current_segment = 0
        self.bluetooth_connected = False
        self.wifi_connected = False
        self._power_default_id = None
        self.running_elapsed = 0
        self.show_running = False
        self.colors = COLORS
        self.mode_manager = ModeManager()
        self.cm: ConnectivityManager | None = None
        self.POWER_LONG_MS = 000
        self._press_start = {}
        self._power_long_timer_id = None
        self._power_long_done = False
        self.motor_client: ASPEPClient | None = None
        self.motor_ready = False
        self._motor_port = os.environ.get("CONZERO_UART_PORT", "/dev/ttyS0")
    
        
        # Fault monitoring variables
        self.current_faults = 0x0000
        self.active_fault_list = []
        self.fault_check_interval = 2000  # Check faults every 2 seconds
        self.speed_reference = 0
        self.speed_actual = 0
        self.speed_check_interval = 1000  # Check speed every 1 second
        self._fault_display_index = 0
        self._fault_cycle_id = None
        self.system_stalled = False
        
        # Pairing system variables
        self.paired_remotes = set()
        self.pairing_mode = False
        self._pre_pairing_count = 0
        self._pairing_blink_id = None
        self._mode_long_timer_id = None
        self.single_remote_mode = True # TRUE for one remote , false for multiple remotes
        
                
        # LED setup
        self.led_pin = GPIO_PINS["led"]
        self._setup_led()
        
         
        
        self._load_paired_remotes()
            
        # Map(button, gesture) action method 
        self._ble_actions = {
            (1, "single"): self.toggle_pause,
            (1, "long"): self.toggle_power,
            (2, "single"): self.switch_mode,
            (3, "single"): self.set_timer,
            (4, "single"): self.adjust_speed,   
        }
            
        # Main Display Area
        self.shadow_frame = tk.Frame(
            root,
            bg="#071226",
            height=320,
            width=480,
            bd=0,
            relief=tk.FLAT
        )
        self.shadow_frame.pack_propagate(False)
        self.shadow_frame.pack(fill=tk.BOTH, expand=True)

        self.display_frame = tk.Frame(
            self.shadow_frame,
            bg="#071226",
            bd=0,
            relief=tk.FLAT,
            highlightthickness=16,
            highlightbackground="#12314a"
        )
        self.display_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create an inner frame to center content vertically
        self.center_frame = tk.Frame(self.display_frame, bg="#071226")
        self.center_frame.place(relx=0.5, rely=0.5, anchor="center")

        self.display_frame.pack_propagate(False)
        self.display_frame.columnconfigure(0, weight=1)
        self.display_frame.columnconfigure(1, weight=1)
        self.display_frame.columnconfigure(2, weight=1)    
        
        # Load icons
        try:
            self.bt_icon_off = tk.PhotoImage(file="/home/pi/conzero-jet-project/icons/ble_off.png").subsample(15,15)
            self.bt_icon_on = tk.PhotoImage(file="/home/pi/conzero-jet-project/icons/ble_On.png").subsample(15,15)
            self.wifi_icon_off = tk.PhotoImage(file="/home/pi/conzero-jet-project/icons/Off_Wifi.png").subsample(15,15)
            self.wifi_icon_on = tk.PhotoImage(file="/home/pi/conzero-jet-project/icons/On_Wifi.png").subsample(15,15)
        except Exception as e:
            print(f"Could not load icons: {e}")
            self.bt_icon_off = self.bt_icon_on = None
            self.wifi_icon_off = self.wifi_icon_on = None 
            
        # Bluetooth and WiFi status labels
        self.bt_img_label = tk.Label(self.display_frame, image=self.bt_icon_off if self.bt_icon_off else None, 
                                   text='BLE' if not self.bt_icon_off else '', font=FONTS["label"], bg=self.display_frame['bg'])
        self.bt_img_label.grid(row=0, column=0, sticky="nw", padx=(8,0), pady=(4,0))
        
        self.wifi_img_label = tk.Label(self.display_frame, image=self.wifi_icon_off if self.wifi_icon_off else None, 
                                     text="WiFi" if not self.wifi_icon_off else '', font=FONTS["label"], bg=self.display_frame['bg'])
        self.wifi_img_label.grid(row=0, column=2, sticky="ne", padx=(0,8), pady=(4,0))

        self.bt_connecting = False
        self.wifi_connecting = False
        self.bt_flash_id = None
        self.wifi_flash_id = None
        
        # Speed/Timer/Mode titles and values
        self.center_frame = tk.Frame(self.display_frame, bg=self.display_frame['bg'])
        self.center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        self.speed_title = tk.Label(self.display_frame, text="SPEED", font=FONTS["label"], fg=COLORS["text"], 
                                  bg=self.display_frame['bg'], width=8, height=1)
        self.speed_title.grid(row=1, column=0, pady=(8, 0), padx=(0, 0), sticky="nsew")
        
        self.timer_title = tk.Label(self.display_frame, text="TIMER", font=FONTS["label"], fg=COLORS["text"], 
                                  bg=self.display_frame['bg'], width=8, height=1)
        self.timer_title.grid(row=1, column=1, pady=(8, 0), padx=(0, 0), sticky="nsew")
        
        self.mode_title = tk.Label(self.display_frame, text="MODE", font=FONTS["label"], fg=COLORS["text"], 
                                 bg=self.display_frame['bg'], width=8, height=1)
        self.mode_title.grid(row=1, column=2, pady=(8, 0), padx=(0, 0), sticky="nsew")

        self.speed_label = tk.Label(self.display_frame, text=f"{self.speed}%", font=FONTS["value"], 
                                  fg=COLORS["text"], bg=self.display_frame['bg'], width=8, height=1)
        self.speed_label.grid(row=2, column=0, pady=(0, 0), padx=(0, 0), sticky="nsew")
        
        self.time_label = tk.Label(self.display_frame, text="00:00", font=FONTS["value"], fg="#dbefff", 
                                 bg=self.display_frame['bg'], width=8, height=1)
        self.time_label.grid(row=2, column=1, pady=(0, 0), padx=(0, 0), sticky="nsew")
        
        self.mode_label = tk.Label(self.display_frame, text=self.mode, font=FONTS["value"], fg=COLORS["text"], 
                                 bg=self.display_frame['bg'], width=8, height=1)
        self.mode_label.grid(row=2, column=2, pady=(0, 0), padx=(0, 0), sticky="nsew")

        self.speed_time_label = tk.Label(self.display_frame, text="", font=FONTS["label"], fg=COLORS["text"], 
                                       bg=self.display_frame['bg'], width=8, height=1)
        self.speed_time_label.grid(row=3, column=0, pady=(0, 6), sticky="nsew")
        
        self.wave_anim = WaveAnimation(self.display_frame)

        
        # Speed actual vs reference display
        self.speed_actual_label = tk.Label(self.display_frame, text="", font=("Rajdhani SemiBold", 10), 
                                         fg="#aaaaaa", bg=self.display_frame['bg'])
        self.speed_actual_label.grid(row=3, column=1, pady=(0, 6), sticky="nsew")
        
        self.status_label = tk.Label(self.display_frame, text="", font=FONTS["status"], fg="#dbefff", 
                                   bg=self.display_frame['bg'], wraplength=450, justify="center")
        self.status_label.grid(row=4, column=0, columnspan=3, pady=(8, 10), sticky="nsew")       
         
        # Timer loop (updates every second) - heartbeat of the project
        self.root.after(1000, self.update_timer)

        # GPIO setup using GPIOHandler
        self.gpio_handler = None
        try:
            self.gpio_handler = GPIOHandler(GPIO_PINS, self.handle_button_press)
            self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        except Exception as e:
            print(f"GPIO not available: {e}")   
                
        # Start BLE (after UI widgets exists)
        try:
            self.cm = ConnectivityManager(
                on_ble_event=self._on_ble_event, 
                ble_name_regex="Shelly|SBBT|BLU",
                debug=False,
                initial_allowed_macs=self.paired_remotes
            )
            self.cm.start_ble()
        except Exception as e:
            print(f"BLE start failed: {e}")

        # Initialize motor after a short delay
        self.root.after(200, self._init_motor)
        
        # Start fault monitoring loop
        self.root.after(self.fault_check_interval, self._monitor_faults)
        
        # Start speed monitoring loop
        self.root.after(self.speed_check_interval, self._monitor_speed)

    # ==================== FAULT MONITORING ====================
    
    def _monitor_faults(self):
        """Periodically check motor faults"""
        if self.motor_ready and self.motor_client:
            try:
                faults = self.motor_client.read_faults(motor_index=1)
                if faults is not None:
                    self._update_fault_display(faults)
            except Exception as e:
                print(f"Fault check error: {e}")
        
        # Schedule next check
        self.root.after(self.fault_check_interval, self._monitor_faults)
    
    def _update_fault_display(self, fault_flags):
        """Update UI based on fault status"""
        self.current_faults = fault_flags
        
        if fault_flags == 0:
            # No faults - clear display and resume normal operation
            self.active_fault_list = []
            self.system_stalled = False
            self._stop_fault_cycle()
            
            # Restore normal frame color
            if self.power_on:
                if self.paused:
                    self.display_frame.config(highlightbackground="#A3D9E6")
                    self.shadow_frame.config(bg="#BFE5EA")
                else:
                    self.display_frame.config(highlightbackground=FAULT_COLORS["normal"])
                    self.shadow_frame.config(bg="#7ACAD5")
            else:
                self.display_frame.config(highlightbackground="#12314a")
                self.shadow_frame.config(bg="#071226")
            
            # Clear status if showing fault
            if "FAULT" in self.status_label.cget("text").upper():
                self.status_label.config(text="", fg=COLORS["text"])
        else:
            # FAULTS DETECTED - STALL SYSTEM
            self.system_stalled = True
            
            # Stop motor immediately
            if self.power_on and not self.paused:
                self._motor_stop_safe()
                self.paused = True
                self.speed = 0
            
            # Decode active faults
            self.active_fault_list = []
            for bit_value, fault_name in FAULT_NAMES.items():
                if fault_flags & bit_value:
                    self.active_fault_list.append(fault_name)
            
            # Set solid red frame
            self.display_frame.config(highlightbackground=FAULT_COLORS["active"])
            self.shadow_frame.config(bg="#cc0000")
            
            # Show fault messages
            self._display_fault_messages()
    
    def _display_fault_messages(self):
        """Display all fault messages in compact multi-column layout"""
        if not self.active_fault_list:
            return
        
        if len(self.active_fault_list) == 1:
            # Single fault - show it compactly
            fault_msg = f"FAULT: {self.active_fault_list[0]}"
            self.status_label.config(text=fault_msg, fg=FAULT_COLORS["active"], font=("Rajdhani", 14))
        else:
            # Multiple faults - display in 2 columns for better fit
            columns = 2
            fault_lines = []
            
            # Calculate how many items per column
            items_per_col = (len(self.active_fault_list) + columns - 1) // columns
            
            # Create columns with compact formatting
            for row in range(items_per_col):
                line_parts = []
                for col in range(columns):
                    index = row + col * items_per_col
                    if index < len(self.active_fault_list):
                        fault_name = self.active_fault_list[index]
                        # Compact formatting - shorter numbers and names
                        line_parts.append(f"{index+1}. {fault_name}")
                    else:
                        line_parts.append("")  # Empty space for alignment
                
                # Join with adequate spacing between columns
                fault_lines.append("    ".join(line_parts))
            
            # Join all lines with newlines
            fault_text = "\n".join(fault_lines)
            self.status_label.config(text=fault_text, fg=FAULT_COLORS["active"], font=("Rajdhani", 12))
        
        # Stop any existing cycling
        self._stop_fault_cycle()
        
   
    
    def _stop_fault_cycle(self):
        """Stop fault message cycling"""
        if self._fault_cycle_id:
            self.root.after_cancel(self._fault_cycle_id)
            self._fault_cycle_id = None
        self._fault_display_index = 0
           
    def _setup_led(self):
        """Initialize LED GPIO pin"""
        try:
            # Use gpiozero for easy LED control
            from gpiozero import LED
            self.led = LED(self.led_pin)
            self.led.off()  # Start with LED off
            print(f"LED initialized on GPIO {self.led_pin}")
        except Exception as e:
            print(f"LED setup failed: {e}")
            self.led = None    

    def _update_led(self):
        """Update LED state based on power status"""
        if not self.led:
            return
            
        try:
            if self.power_on and not self.system_stalled:
                self.led.on()
                print("LED ON - System powered")
            else:
                self.led.off()
                print("LED OFF - System powered down or stalled")
        except Exception as e:
            print(f"LED control error: {e}")            
            
    # ==================== SPEED MONITORING ====================
    
    def _monitor_speed(self):
        """Periodically check actual motor speed vs reference"""
        if self.motor_ready and self.motor_client and self.power_on and not self.paused and not self.system_stalled:
            try:
                # Poll actual speed
                self.motor_client.poll_speed(motor_index=1, repeat=1, delay=0)
                
                if self.motor_client.last_data_payload and len(self.motor_client.last_data_payload) >= 4:
                    self.speed_actual = int.from_bytes(
                        self.motor_client.last_data_payload[:4], 'little', signed=True
                    )
                    self.speed_reference = self.motor_client._last_speed_ref or 0
                    
                    # Update display
                    self._update_speed_display()
                    
            except Exception as e:
                print(f"Speed check error: {e}")
        else:
            # Motor off or paused - clear speed display
            self.speed_actual_label.config(text="")
        
        # Schedule next check
        self.root.after(self.speed_check_interval, self._monitor_speed)
    
    def _update_speed_display(self):
        """Update speed actual vs reference display"""
        if self.speed_reference == 0:
            self.speed_actual_label.config(text="")
            return
        
        # Calculate percentage of reference
        actual_pct = (self.speed_actual / self.speed_reference * 100) if self.speed_reference > 0 else 0
        
        # Show actual speed if different from reference
        if abs(self.speed_actual - self.speed_reference) > (self.speed_reference * 0.05):  # >5% difference
            # Speed reduction detected
            color = FAULT_COLORS["warning"] if actual_pct < 95 else "#aaaaaa"
           #self.speed_actual_label.config(
             #   text=f"Act: {self.speed_actual} RPM ({actual_pct:.0f}%)",
              #  fg=color
            #)
        else:
            # Speed normal
            self.speed_actual_label.config(text="")

    # ==================== MOTOR SPEED CONTROL ====================
    
    def _send_speed_to_motor(self, speed_percent):
        """
        Convert UI speed percentage to RPM and send to motor
        Called whenever speed changes in UI
        """
        if not self.motor_ready or not self.motor_client:
            print(f"WARNING: Motor not ready - speed {speed_percent}% not sent")
            return False
        
        if not self.power_on or self.paused or self.system_stalled:
            print(f"WARNING: Motor paused/off/stalled - speed {speed_percent}% not sent")
            return False
        
                # FIX: Use the motor client's max speed setting, not the global factor
        if hasattr(self.motor_client, '_max_speed_rpm'):
                # Motor client has its own max speed setting
                target_rpm = int((speed_percent / 100.0) * self.motor_client._max_speed_rpm)
                print(f"Using motor client max speed: {self.motor_client._max_speed_rpm} RPM")
        else:
                # Fallback to global factor
                target_rpm = int(speed_percent * SPEED_PERCENT_TO_RPM_FACTOR)
            
        print(f"Sending speed: {speed_percent}% -> {target_rpm} RPM")
            
        try:
                success = self.motor_client.set_speed_rpm(target_rpm, motor_index=1)
                
                if success:
                    print(f"Speed set: {target_rpm} RPM")
                    return True
                else:
                    print(f"ERROR: Failed to set speed: {target_rpm} RPM")
                    return False
                    
        except Exception as e:
                print(f"ERROR: Error sending speed: {e}")
                return False

    # ==================== PAIRING SYSTEM ==================== #
    
    def _load_paired_remotes(self):
        """Load paired remotes from file"""
        try:
            config_file = "/home/pi/conzero-jet-project/paired_remotes.json"
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    self.paired_remotes = set(data.get("paired_macs", []))
                    print(f"Loaded {len(self.paired_remotes)} paired remotes")
        except Exception as e:
            print(f"Error loading paired remotes: {e}")
            self.paired_remotes = set()

    def _save_paired_remotes(self):
        """Save paired remotes to file"""
        try:
            config_file = "/home/pi/conzero-jet-project/paired_remotes.json"
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump({"paired_macs": list(self.paired_remotes)}, f)
            print(f"Saved {len(self.paired_remotes)} paired remotes")
        except Exception as e:
            print(f"Error saving paired remotes: {e}")

    def enable_pairing_mode(self):
        """LERNMODUS: Smart pairing based on single_remote_mode"""
        self.pairing_mode = True
        
        #  SINGLE REMOTE MODE: Clear existing remotes 
        if self.single_remote_mode:
            old_count = len(self.paired_remotes)
            self.paired_remotes.clear()
            print(f"Single remote mode: Cleared {old_count} old remotes")
        else:
            # Multi-remote mode: Keep existing remotes
            old_count = len(self.paired_remotes)
            print(f"Multi-remote mode: Keeping {old_count} existing remotes")
        
        # Allow all devices temporarily
        if self.cm:
            self.cm.update_allowed_macs(set())
        
        # Show appropriate message
        if self.single_remote_mode and old_count > 0:
            self.status_label.config(
                text="LEARNMode - Press remote button", 
                fg="#ff9800"
            )
        else:
            self.status_label.config(
                text="PAIRING: Press any button on your remote", 
                fg="#ff9800"
            )
        
        self._start_pairing_blink()
        self.root.after(30000, self.disable_pairing_mode)

    def disable_pairing_mode(self):
        """Exit pairing mode and restore security"""
        self.pairing_mode = False
        self._stop_pairing_blink()
        
        if self.cm:
            self.cm.update_allowed_macs(self.paired_remotes)
        
        # IMPROVED MESSAGING 
        if len(self.paired_remotes) > 0:
            self.status_label.config(text="Remote connected - Ready to use", fg="#4caf50")
        else:
            self.status_label.config(text="Pairing mode ended - No remote connected", fg="#ff5555")
        
        # Restore normal Bluetooth icon
        if self.bluetooth_connected and self.bt_icon_on:
            self.bt_img_label.config(image=self.bt_icon_on)
        
        # Clear message after 3 seconds only if no faults
        self.root.after(3000, lambda: self.status_label.config(text="") if self.current_faults == 0 else None)

    def _start_pairing_blink(self):
        """Start blinking Bluetooth icon during pairing mode"""
        if not self.pairing_mode:
            return
            
        current_image = self.bt_img_label.cget("image")
        if current_image == str(self.bt_icon_on):
            self.bt_img_label.config(image=self.bt_icon_off)
        else:
            self.bt_img_label.config(image=self.bt_icon_on)
            
        self._pairing_blink_id = self.root.after(500, self._start_pairing_blink)

    def _stop_pairing_blink(self):
        """Stop the pairing blink animation"""
        if self._pairing_blink_id:
            self.root.after_cancel(self._pairing_blink_id)
            self._pairing_blink_id = None

    def _show_pairing_success(self):
        """Show fast blink feedback when pairing succeeds"""
        #  FIRST: Stop any existing blinking 
        self._stop_pairing_blink()
        
        def fast_blink(count=0):
            if count >= 6:  # 3 full cycles (on-off-on-off-on-off)
                # Final state: Solid ON if connected
                if self.bluetooth_connected and self.bt_icon_on:
                    self.bt_img_label.config(image=self.bt_icon_on)
                return
                
            if count % 2 == 0:
                self.bt_img_label.config(image=self.bt_icon_off)
            else:
                self.bt_img_label.config(image=self.bt_icon_on)
                
            self.root.after(200, lambda: fast_blink(count + 1))
        
        fast_blink()

    # ==================== BLE EVENT HANDLING ====================
    
    def _on_ble_event(self, evt: dict):
            """Runs in BLE background thread. Marshal to Tk main thread."""
            self.root.after(0, self._handle_ble_event, evt)

    def _handle_ble_event(self, evt: dict):
        button = evt.get("button")
        gesture = evt.get("gesture") 
        mac = evt.get("mac")
        
        #  SINGLE REMOTE PAIRING LOGIC 
        if self.pairing_mode and mac:
                # SINGLE MODE: Clear all and keep only this one
                old_remotes = self.paired_remotes.copy()
                self.paired_remotes.clear()
                self.paired_remotes.add(mac)
                   #  CRITICAL: EXIT PAIRING MODE IMMEDIATELY AFTER SUCCESS 
                self.disable_pairing_mode()
                
                if old_remotes:
                    self.status_label.config(text="Remote replaced!", fg="#4caf50")
                else:
                    self.status_label.config(text="Remote paired!", fg="#4caf50")
            
            
                self._show_pairing_success()
                self._save_paired_remotes()
            
        if self.cm:
            self.cm.update_allowed_macs(self.paired_remotes)
        
        # Execute button actions
        action = self._ble_actions.get((button, gesture))
        if action and mac in self.paired_remotes:
            action()
    # ==================== CONNECTIVITY ====================
    
    
        
    def toggle_wifi(self):
        if not self.wifi_connected and not self.wifi_connecting:
            self.wifi_connecting = True
            self._flash_wifi_icon()
            self.root.after(2000, self._finish_wifi_connect)
        else:
            self.wifi_connected = False
            self.wifi_connecting = False
            if self.wifi_flash_id:
                self.root.after_cancel(self.wifi_flash_id)
            if self.wifi_icon_off:
                self.wifi_img_label.config(image=self.wifi_icon_off)
            self.status_label.config(text="", fg=self.colors["disconnected"])
            self.root.after(2000, lambda: self.status_label.config(text=""))

    def _flash_wifi_icon(self):
        if not self.wifi_connecting:
            return
        if self.wifi_icon_on and self.wifi_icon_off:
            current = self.wifi_img_label.cget("image")
            next_icon = self.wifi_icon_on if current == str(self.wifi_icon_off) else self.wifi_icon_off
            self.wifi_img_label.config(image=next_icon)
        self.wifi_flash_id = self.root.after(500, self._flash_wifi_icon)

    def _finish_wifi_connect(self):
        """Complete WiFi connection after delay"""
        self.wifi_connecting = False
        self.wifi_connected = True
        if self.wifi_flash_id:
            self.root.after_cancel(self.wifi_flash_id)
        if self.wifi_icon_on:
            self.wifi_img_label.config(image=self.wifi_icon_on)
        self.status_label.config(text="", fg=self.colors["connected"])

    # ==================== GPIO BUTTON HANDLING ====================
    
    def handle_button_press(self, pin, level):
        """Handle GPIO button events from gpiozero"""
        power_pin = 3
        mode_pin = 23
        
        if pin == power_pin:
            if level == 0:
                # Button pressed - start timing
                self._press_start[power_pin] = time.time()
                self._power_long_done = False
                
                # Cancel any existing timers
                if self._power_long_timer_id:
                    try:
                        self.root.after_cancel(self._power_long_timer_id)
                    except Exception:
                        pass
                    self._power_long_timer_id = None
                
                # Set up ONLY long-press timer (3 seconds for shutdown)
                # Short press will be handled on button release
                self._power_long_timer_id = self.root.after(3000, lambda: self._power_long_timeout(power_pin))
                
            else:
                # Button released
                duration = time.time() - self._press_start.get(power_pin, 0)
                
                if self._power_long_timer_id:
                    try:
                        self.root.after_cancel(self._power_long_timer_id)
                    except Exception:
                        pass
                    self._power_long_timer_id = None
                
                self._press_start.pop(power_pin, None)

                # Check if this was a short press (released before 3 seconds)
                if not self._power_long_done and duration < 2.5:  # Allow some margin
                    # SHORT PRESS behavior
                    if not self.power_on:
                        # Power on the system + will auto-enter default mode
                        print(" SHORT PRESS - Powering ON")
                        self.toggle_power()
                    else:
                        # System is already on - toggle pause/resume
                        print(" SHORT PRESS - Toggle pause")
                        self.toggle_pause()
                        
                # Reset the long press flag
                self._power_long_done = False
            return




        if pin == mode_pin:
            if level == 0:
                self._press_start[mode_pin] = time.time()
                self._mode_long_timer_id = self.root.after(3000, self._enter_pairing_mode)
            else:
                if hasattr(self, '_mode_long_timer_id') and self._mode_long_timer_id:
                    self.root.after_cancel(self._mode_long_timer_id)
                    self._mode_long_timer_id = None
                if not self.pairing_mode:
                    self.switch_mode()
            return

        if level == 0:
            if pin == 16:
                self.set_timer()
            elif pin == 6:
                self.adjust_speed()
   

    def _enter_pairing_mode(self):
        """Enter pairing mode after MODE button long press"""
        self.enable_pairing_mode()

    def _power_long_timeout(self, pin):
        """Called when power button has been held long enough to request shutdown"""
        self._power_long_timer_id = None
        self._power_long_done = True

        # If system is on, stop motor safely first
        try:
            # Provide user feedback
            self.status_label.config(text="SHUTDOWN", fg="#ff5555")
        except Exception:
            pass

        # Attempt a graceful shutdown sequence
        try:
            self._shutdown_system()
        except Exception as e:
            print(f"Shutdown failed: {e}")
            try:
                # Fallback immediate poweroff
                subprocess.run(["sudo","poweroff"], check=False)
            except Exception as e2:
                print(f"Fallback poweroff failed: {e2}")
    
    def _shutdown_system(self):
        """Gracefully stop motor, services and power off the Pi."""
        print("🛑 CRITICAL: Stopping motor before shutdown...")

        # ==================== EMERGENCY MOTOR STOP ====================
        try:
            # Method 1: Send immediate stop command via UART
            if self.motor_client and self.motor_ready:
                print("🔄 Sending emergency motor stop...")
                self.motor_client.stop_motor()
                time.sleep(0.5)  # Give time for command to be sent
                
            # Method 2: If UART fails, try GPIO emergency stop (if available)
            # This depends on your motor controller hardware
            
        except Exception as e:
            print(f"⚠️ Motor stop error: {e}")

        # ==================== HARDWARE RESET (if available) ====================
        try:
            # If your motor controller has a reset pin, trigger it
            # Example: GPIO pin that controls motor power
            print("🔌 Attempting hardware motor disable...")
            # Add your specific hardware reset code here
            
        except Exception as e:
            print(f"⚠️ Hardware reset error: {e}")

        # ==================== ADD SAFETY DELAY ====================
        print("⏳ Waiting for motor to stop...")
        time.sleep(2)  # Critical: Wait for motor to actually stop

        # ==================== THEN PROCEED WITH NORMAL SHUTDOWN ====================
        try:
            # Stop BLE scanning if running
            if self.cm:
                try:
                    self.cm.stop_ble()
                except Exception:
                    pass

            # Turn off LED
            if hasattr(self, 'led') and self.led:
                try:
                    self.led.off()
                except Exception:
                    pass

            # Sync filesystems
            print("💾 Syncing filesystems...")
            subprocess.run(["sync"])
            
            # Shutdown
            print(" Executing: sudo poweroff")
            subprocess.run(["sudo", "poweroff"])
        
        except Exception as e:
            print(f"Shutdown error: {e}")
            # Force shutdown
            subprocess.run(["sudo", "shutdown", "-h", "now"])            
                    
   
    def on_close(self):
        """Cleanup GPIO and close the window"""
        self.wave_anim.cleanup()
        if hasattr(self, 'led') and self.led:
            try:
                self.led.off()
                self.led.close()
            except Exception as e:
                print(f"LED cleanup error: {e}")
        if self.gpio_handler:
            self.gpio_handler.cleanup()
        if self.cm:
            try: 
                self.cm.stop_ble()
            except Exception:
                pass   
        try:
            if self.motor_client:
                self.motor_client.close()
        except Exception:
            pass     
        self.root.destroy()    
        
    # ==================== MOTOR CONTROL ====================
    
    def _init_motor(self):
        """Open UART and handshake once"""
        try:
            self.motor_client = ASPEPClient(port=self._motor_port, baud=115200)
            self.motor_client.open()
            if self.motor_client.handshake():
                self.motor_ready = True
                print("Motor ready")
            else:
                self.status_label.config(text="MOTOR LINK FAIL", fg="#ff5555")
                print("ERROR: Motor handshake failed")
        except Exception as e:
            self.status_label.config(text="UART ERR", fg="#ff5555")
            print(f"Motor init failed: {e}")

    def _motor_start_safe(self):
        """Start motor with fault checking"""
        if not self.motor_ready or not self.motor_client:
            return
        
        if self.system_stalled:
            print("WARNING: System stalled - cannot start motor")
            return
        
        if not self.motor_client.handshake():
            return
        
        try:
            self.motor_client.start_motor()
            print("Motor start command sent")
            
            # Send current speed to motor
            if self.speed > 0:
                self._send_speed_to_motor(self.speed)
            
        except Exception as e:
            print(f"Start motor error: {e}")
            self.status_label.config(text="START ERR", fg="#ff5555")

    def _motor_stop_safe(self):
        """Stop motor safely"""
        if not self.motor_ready or not self.motor_client:
            return
        try:
            self.motor_client.stop_motor()
            print("Motor stop command sent")
        except Exception as e:
            print(f"Stop motor error: {e}")
            self.status_label.config(text="STOP ERR", fg="#ff5555")   
        
    # ==================== MAIN LOGIC ====================
    
    def toggle_power(self):
        """Toggle main power on/off"""
        if not self.motor_client or not self.motor_ready:  
            print("ERROR: Motor client not ready")
            return
        if not self.power_on:
            # POWER ON
            self.power_on = True
            
            # Check for faults immediately
            if self.current_faults != 0:
                # Faults present - stay in stall mode
                print("WARNING: Power ON blocked - faults present")
                self.display_frame.config(highlightbackground=FAULT_COLORS["active"])
                self.shadow_frame.config(bg="#cc0000")
            else:
                # No faults - proceed normally
                self.display_frame.config(highlightbackground="#2798AA")   
                self.shadow_frame.config(bg="#7ACAD5")
                
                if self._power_default_id:
                    try:
                        self.root.after_cancel(self._power_default_id)
                    except:
                     pass
                self._power_default_id = self.root.after(3000, self._enter_default_after_power)
               
            
            self.show_running = False
            self._update_led()
            print("Power ON")
            self.wave_anim.set_system_state(
                power_on=self.power_on,
                paused=self.paused,
                fault=self.system_stalled,
                speed=self.speed
            )
            
        else:
            # POWER OFF
            self.power_on = False
            self.remaining_time = 0
            self._cancel_power_default()
            self.show_running = False
            self.running_elapsed = 0
            self.system_stalled = False
            self.display_frame.config(highlightbackground="#3A4A53")
            self.shadow_frame.config(bg="#7A8A99")
            self.update_labels()
            self._motor_stop_safe()
            self._update_led()
            print("Power OFF")
            
    def switch_mode(self):
        """Switch between different operating modes"""
        # Block if system stalled
        if self.system_stalled:
            print("BLOCKED: Mode switch blocked - system stalled due to faults")
            return
        
        self._cancel_power_default()
        if not self.power_on:
            return 
        
        self.mode = self.mode_manager.get_next_mode(self.mode)
        self.current_segment = 0
        self.surf_prep = False
        self.timer_duration = self.mode_manager.get_mode_durations(self.mode)
        self.remaining_time = self.timer_duration 
        
        if self.mode == "P5":
            self.speed = 30
            self.surf_prep = True
            self.show_running = False
        elif self.mode == "P0":
            self.speed = 40 
            self.show_running = True
            self.running_elapsed = 0
        else:
            self.show_running = False
        
        # Send speed to motor if running
        if not self.paused:
            self._send_speed_to_motor(self.speed)
            
        if self.current_faults == 0:
            self.status_label.config(text="", fg=self.colors["primary"])
            self.root.after(2000, lambda: self.status_label.config(text="", fg="#4caf50") if self.power_on and not self.paused and self.current_faults == 0 else None)
        
        self.update_labels()
           # TURN LED OFF
      
        print(f"Mode: {self.mode}")
            
    def set_timer(self):
        """Set timer duration"""
        # Block if system stalled
        if self.system_stalled:
            print("BLOCKED: Timer set blocked - system stalled due to faults")
            return
        
        self._cancel_power_default()
        if not self.power_on:
            return
        
        self.mode = "T"
        self.current_segment = 0
        
        if self.current_faults == 0:
            self.status_label.config(text="", fg=self.colors["primary"])
            self.root.after(1500, lambda: self.status_label.config(text="", fg="#4caf50") if self.power_on and not self.paused and self.current_faults == 0 else None)

        if not self.timer_selecting:
            self.timer_selecting = True
            self.timer_select_start = self.root.after(3000, self._confirm_timer_selection)
            if self.timer_duration == 0:
                self._timer_idx = 0
            else:
                try:
                    self._timer_idx = self.timer_options.index(self.timer_duration // 60)
                except ValueError:
                    self._timer_idx = 0
        else:
            if hasattr(self, '_timer_idx'):
                self._timer_idx = (self._timer_idx + 1) % len(self.timer_options)
            else:
                self._timer_idx = 0
            if self.timer_select_start:
                self.root.after_cancel(self.timer_select_start)
            self.timer_select_start = self.root.after(3000, self._confirm_timer_selection)

        mins = self.timer_options[self._timer_idx]
        self.timer_duration = mins * 60
        self.remaining_time = self.timer_duration
        self.status_label.config(fg=self.colors["primary"])
        self.update_labels()

    def _confirm_timer_selection(self):
        """Confirm timer selection after 3 seconds"""
        if not self.timer_selecting:
            return
        self.timer_selecting = False
        if hasattr(self, '_timer_idx'):
            self.timer_duration = self.timer_options[self._timer_idx] * 60
        else:
            self.timer_duration = 0
        self.remaining_time = self.timer_duration
        if self.timer_duration > 0:
            self.status_label.config(fg=self.colors["primary"])
        else:
            self.status_label.config(fg=self.colors["disconnected"])
        self.timer_select_start = None
        self.update_labels()

    def adjust_speed(self):
        """Adjust motor speed through presets"""
        # Block if system stalled
        if self.system_stalled:
            print("BLOCKED: Speed adjust blocked - system stalled due to faults")
            return
        
        if not self.power_on:
            return
        
        speeds = SPEED_PRESETS
        if self.paused:
            current = getattr(self, '_pre_pause_speed', self.speed)
        else:
            current = self.speed
        
        try:
            current_idx = speeds.index(current)
        except ValueError:
            current_idx = min(range(len(speeds)), key=lambda i: abs(speeds[i] - current))
        
        new_speed = speeds[(current_idx + 1) % len(speeds)]
        
        if self.paused:
            # Store for when resumed
            self._pre_pause_speed = new_speed
        else:
            # Update speed in training plan if applicable
            if self.mode.startswith("P") and int(self.mode[1:]) in range(1, 5):
                try:
                    segs = list(self.training_plans[self.mode])
                    if 0 <= self.current_segment < len(segs):
                        duration, _ = segs[self.current_segment]
                        segs[self.current_segment] = (duration, new_speed)
                        self.training_plans[self.mode] = segs
                        self.speed = new_speed
                    else:
                        self.speed = new_speed
                except Exception:
                    self.speed = new_speed
            else:
                self.speed = new_speed
            
            # Send speed to motor immediately
            self._send_speed_to_motor(new_speed)
        
        if self.current_faults == 0:
            self.status_label.config(text="", fg=self.colors["primary"])
            self.root.after(2000, lambda: self.status_label.config(text="", fg="#4caf50") if self.power_on and not self.paused and self.current_faults == 0 else None)
        
        self.update_labels()
        print(f"Speed: {new_speed}%")

    def toggle_pause(self):
        """
        Toggle pause/resume with AUTOMATIC FAULT CLEARING
        START/PAUSE button clears faults and starts motor
        """
        self._cancel_power_default()
        if not self.power_on:
            self.display_frame.config(highlightbackground="#12314a")
            return
        
        # ==================== PAUSING ====================
        if not self.paused:
            # Motor is running -> pause it
            self._pre_pause_speed = getattr(self, '_pre_pause_speed', self.speed)
            self.paused = True
            self.speed = 0
            
            if not self.system_stalled:
                self.display_frame.config(highlightbackground="#A3D9E6")
                self.shadow_frame.config(bg="#BFE5EA")
            
            self._auto_off_id = self.root.after(30 * 60 * 1000, self._auto_power_off)
            self._motor_stop_safe()
            print("Paused")
            return
        
        
        # ==================== RESUMING (Start button pressed) ====================
        print("START button pressed - checking faults...")
        
        # Step 1: Get current faults
        current_faults = self.current_faults
        
        if current_faults == 0:
            # No faults - resume normally
            print("No faults - resuming")
            self._resume_motor()
            return
        
        # Step 2: Analyze fault types
        has_stall_faults = bool(current_faults & STALL_FAULTS)
        has_clearable_faults = bool(current_faults & CLEARABLE_FAULTS)
        
        print(f"Fault analysis:")
        print(f"  Current faults: 0x{current_faults:04X}")
        print(f"  Has stall faults: {has_stall_faults}")
        print(f"  Has clearable faults: {has_clearable_faults}")
        
        if has_stall_faults:
            # CRITICAL: Stall faults present - cannot auto-clear
            print("ERROR: STALL FAULTS - cannot auto-start")
            self.status_label.config(
                text="CRITICAL FAULT - FIX REQUIRED",
                fg=FAULT_COLORS["active"]
            )
            return
        
        if has_clearable_faults:
            # Only clearable faults - auto-acknowledge and resume
            print("Clearable faults detected - auto-clearing...")
            self._auto_clear_faults_and_resume()

    def _resume_motor(self):
        """Resume motor from pause (no faults)"""
        self.paused = False
        self.system_stalled = False
        
        if hasattr(self, '_pre_pause_speed'):
            self.speed = self._pre_pause_speed
        
        self.display_frame.config(highlightbackground=FAULT_COLORS["normal"])
        self.shadow_frame.config(bg="#7ACAD5")
        
        if hasattr(self, '_auto_off_id') and self._auto_off_id:
            try:
                self.root.after_cancel(self._auto_off_id)
            except:
                pass
            self._auto_off_id = None
        
        self._motor_start_safe()
        print("Motor resumed")

    def _auto_clear_faults_and_resume(self):
        """Automatically clear faults and resume motor"""
        if not self.motor_client or not self.motor_ready:
            print("ERROR: Motor client not ready")
            return
        
        try:
            # Send FAULT_ACK command
            print("Sending FAULT_ACK...")
            success = self.motor_client.fault_acknowledge(motor_index=1)
            
            if not success:
                print("ERROR: FAULT_ACK failed")
                self.status_label.config(
                    text="FAULT CLEAR FAILED",
                    fg=FAULT_COLORS["active"]
                )
                return
            
            # Wait for fault register to update
            time.sleep(0.2)
            
            # Verify faults cleared
            print("Verifying faults cleared...")
            faults_after = self.motor_client.read_faults(motor_index=1)
            
            if faults_after == 0:
                # Success - faults cleared
                print("Faults cleared successfully")
                self.status_label.config(
                    text="FAULTS CLEARED",
                    fg="#4caf50"
                )
                
                # Clear message after 1 second and resume
                self.root.after(500, self._resume_motor)
                self.root.after(2000, lambda: self.status_label.config(text="") if self.current_faults == 0 else None)
                
            elif faults_after & STALL_FAULTS:
                # Stall faults remain
                print(f"ERROR: Stall faults remain: 0x{faults_after:04X}")
                self.status_label.config(
                    text="CRITICAL FAULT - FIX REQUIRED",
                    fg=FAULT_COLORS["active"]
                )
                
            else:
                # Other faults remain (voltage/current still out of range)
                print(f"WARNING: Faults remain: 0x{faults_after:04X}")
                self.status_label.config(
                    text="CONDITION NOT FIXED",
                    fg=FAULT_COLORS["warning"]
                )
                
        except Exception as e:
            print(f"ERROR: Error clearing faults: {e}")
            self.status_label.config(
                text="FAULT CLEAR ERROR",
                fg=FAULT_COLORS["active"]
            )

    def _auto_power_off(self):
        """Auto power off after 30 minutes of pause"""
        try:
            self.power_on = False
            self.paused = False
            self.remaining_time = 0
            self.speed = 0
            self.status_label.config(text="", fg="#cccccc")
            self.update_labels()
            print("Auto power off (30 min idle)")
        except Exception:
            pass

    def update_timer(self):
        """Main timer loop - runs every second"""
        # Block timer updates if system stalled
        if self.power_on and not self.paused and not self.system_stalled:
            if self.show_running and self.mode == "P0":
                self.running_elapsed += 1
            
            if self.mode == "P5":
                if self.surf_prep and self.remaining_time >= 0:
                    self.remaining_time = max(self.remaining_time - 1, 0)
                    if self.remaining_time <= 0:
                        self.surf_prep = False
                        self.remaining_time = 15
                else:
                    self.remaining_time = max(self.remaining_time - 1, 0)
                    if self.remaining_time == 0:
                        self.speed = 100 if self.speed == 30 else 30
                        self.remaining_time = 15
                        # Send new speed to motor
                        self._send_speed_to_motor(self.speed)
            
            elif self.remaining_time > 0:
                self.remaining_time -= 1
                if self.remaining_time == 0 and self.mode != "P0":
                    if self.current_faults == 0:
                        self.status_label.config(fg="#ff9800")
                    self._start_finish_flash()
            
            # Handle training plan speed changes
            if self.mode.startswith("P") and int(self.mode[1:]) in range(1, 5):
                if self.current_segment < len(self.training_plans[self.mode]):
                    duration, seg_speed = self.training_plans[self.mode][self.current_segment]
                    if duration > 0:
                        # Check if speed changed
                        if self.speed != seg_speed:
                            self.speed = seg_speed
                            # Send new speed to motor
                            self._send_speed_to_motor(seg_speed)
                        
                        duration -= 1
                        self.training_plans[self.mode][self.current_segment] = (duration, seg_speed)
                    else:
                        self.current_segment += 1
            
            self.update_labels()
        
        self.root.after(1000, self.update_timer)

    def update_labels(self):
        """Update all display labels"""
        self.speed_label.config(text=f"{self.speed}%")
        self.mode_label.config(text=self.mode_manager.get_mode_name(self.mode))
        
        if self.show_running and self.mode == "P0":
            rmins, rsecs = divmod(self.running_elapsed, 60)
            self.speed_time_label.config(text=f"RUN: {rmins:02d}:{rsecs:02d}")
        else:
            self.speed_time_label.config(text="")
        
        mins, secs = divmod(self.remaining_time, 60)
        self.time_label.config(text=f"{mins:02d}:{secs:02d}")

    def _start_finish_flash(self):
        """Start timer finish animation"""
        self._finish_flash_count = 0
        self._finish_flash_id = self.root.after(0, self._finish_flash_tick)

    def _finish_flash_tick(self):
        """Flash animation for timer completion"""
        try:
            if getattr(self, '_finish_flash_count', 0) >= 6:
                self._finish_flash_count = 0
                self.mode = "P0"
                self.timer_duration = 0
                self.remaining_time = 0
                self.current_segment = 0
                if self.current_faults == 0:
                    self.status_label.config(text="", fg="#4caf50")
                self.update_labels()
                return
            
            if self._finish_flash_count % 2 == 0:
                self.time_label.config(fg="#ff9800")
                self.speed_label.config(fg="#ff9800")
            else:
                self.time_label.config(fg=self.colors["text"])
                self.speed_label.config(fg=self.colors["primary"])
            
            self._finish_flash_count += 1
            self._finish_flash_id = self.root.after(500, self._finish_flash_tick)
        except Exception:
            pass

    def _enter_default_after_power(self):
        """Enter default mode (P0) 3 seconds after power on"""
        self._power_default_id = None
        if not self.power_on:
            return
        
        # Check for faults before auto-starting
        if self.current_faults != 0:
            print("WARNING: Auto-start blocked - faults present")
            return
        
        self.mode = "P0"
        self.speed = 40
        self.remaining_time = 0
        self.current_segment = 0
        self.show_running = True
        self.running_elapsed = 0
        
        if self.current_faults == 0:
            self.status_label.config(text="", fg=self.colors["primary"])
        
        self.update_labels()
        
        # Only start motor if no faults
        if self.current_faults == 0:
            self._motor_start_safe()
        else:
            print("WARNING: Cannot auto-start - faults present")

    def _cancel_power_default(self):
        """Cancel the auto-enter-default timer"""
        if getattr(self, '_power_default_id', None):
            try:
                self.root.after_cancel(self._power_default_id)
            except:
                pass
            self._power_default_id = None


