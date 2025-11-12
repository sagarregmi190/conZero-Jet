import os 
import time
import tkinter as tk 
from tkinter import PhotoImage
from connectivity import ConnectivityManager

#Import Configuration and helpers 
from config import  (COLORS, TRAINING_PLANS, SPEED_PRESETS,GPIO_PINS,MODE_DURATIONS,MODE_NAMES,FONTS,UI_DIMENSIONS,DEFAULTS,TIMER_OPTIONS)
from gpio_handler import GPIOHandler
from mode_manager import ModeManager

try: 
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

class JetUI:
    def __init__(self,root):
        self.root = root
        self.root.title("conZero-Jet")
        self.root.geometry(UI_DIMENSIONS["window_size"])
        self.root.configure(bg=COLORS["bg"])
        
        #State Variables 
        self.power_on = False
        self.mode = DEFAULTS["mode"]
        self.speed = DEFAULTS["speed"]
        self.timer_duration = DEFAULTS["timer"]
        self.remaining_time = 0
        self.timer_selecting = False
        self.timer_select_start = None
        self.timer_options  = TIMER_OPTIONS
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
        self.POWER_LONG_MS = 2000  # Duration to consider a press as "long"
        self._press_start = {}
        self._power_long_timer_id = None
        self._power_long_done = False
        
        # Map(button , gesture ) action medot 
        self._ble_actions ={
            (1,"single"): self.toggle_pause,
            (1,"long"): self.toggle_power,
            (2,"single"): self.switch_mode,
            (3, "single"): self.set_timer,
            (4,"single"): self.adjust_speed,   
        }
        
        
        #Header Area
        self.header_frame = tk.Frame(root, bg=self.root['bg'])
        self.header_frame.pack(fill=tk.X,pady = UI_DIMENSIONS["header_pady"], padx= UI_DIMENSIONS["header_padx"])
        try:
            #Lead Wave image for branding 
            self.wave_img = tk.PhotoImage(file="/home/pi/conzero-jet-project/icons/Group.png").subsample(15,15)
            self.wave_label = tk.Label(self.header_frame, image=self.wave_img, bg=self.root['bg'], bd=0)
            self.wave_label.pack(side=tk.LEFT, pady=(2,0),padx=(0,0))  # Negative pady to bring it closer to the title
        except Exception as e:
            print(f"Could not load wave image:{e}")
            
        #------Main Display Area-------#
        self.shadow_frame = tk.Frame(root, bg="#071226", height=UI_DIMENSIONS["shadow_height"], width=UI_DIMENSIONS["shadow_width"], bd=0, relief=tk.FLAT)
        self.shadow_frame.pack_propagate(False)
        self.shadow_frame.pack(fill=tk.X, pady=(0, 2), padx=0)
        self.display_frame = tk.Frame(self.shadow_frame, bg="#071226", height=UI_DIMENSIONS["display_height"], bd=0, relief=tk.FLAT)
        self.display_frame.pack(fill=tk.X, pady=UI_DIMENSIONS["display_pady"], padx=UI_DIMENSIONS["display_padx"])
        self.display_frame.config(highlightthickness=5, highlightbackground="#12314a")
        self.display_frame.pack_propagate(False)
        self.display_frame.columnconfigure(0, weight=1)
        self.display_frame.columnconfigure(1, weight=1)
        self.display_frame.columnconfigure(2, weight=1)    
        
        
        # Load WiFi icon for display (right side)
        try:
            #Bluetooth icons 
            self.bt_icon_off = tk.PhotoImage(file ="/home/pi/conzero-jet-project/icons/ble_off.png").subsample(15,15)
            self.bt_icon_on = tk.PhotoImage(file="/home/pi/conzero-jet-project/icons/ble_On.png").subsample(15,15)
            
            #Wifi Icons
            self.wifi_icon_off = tk.PhotoImage(file ="/home/pi/conzero-jet-project/icons/Off_Wifi.png").subsample(15,15)
            self.wifi_icon_on = tk.PhotoImage(file ="/home/pi/conzero-jet-project/icons/On_Wifi.png").subsample(15,15)
        except Exception as e:
            print(f"could not load icons:{e}")
            #Fallback if icons fail to load 
            self.btn_icon_off = self.bt_icon_on = None
            self.wifi_icon_off = self.btn_icon_on = None 
            
        # Bluetooth and WiFi status labels
        self.bt_img_label = tk.Label(self.display_frame, image=self.bt_icon_off if self.bt_icon_off else None, text='BLE' if not self.bt_icon_off else '', font=FONTS["label"], bg=self.display_frame['bg'])
        self.bt_img_label.grid(row=0, column=0, sticky="nw", padx=(8,0), pady=(4,0))
        self.wifi_img_label = tk.Label(self.display_frame, image=self.wifi_icon_off if self.wifi_icon_off else None, text="WiFi" if not self.wifi_icon_off else '', font=FONTS["label"], bg=self.display_frame['bg'])
        self.wifi_img_label.grid(row=0, column=2, sticky="ne", padx=(0,8), pady=(4,0))

        self.bt_connecting = False
        self.wifi_connecting = False
        self.bt_flash_id = None
        self.wifi_flash_id = None
        
        # --- Speed/Timer/Mode titles and values ---#
        self.speed_title = tk.Label(self.display_frame, text="SPEED", font=FONTS["label"], fg=COLORS["text"], bg=self.display_frame['bg'], width=8, height=1)
        self.speed_title.grid(row=1, column=0, pady=(8, 0), padx=(0, 0), sticky="nsew")
        self.timer_title = tk.Label(self.display_frame, text="TIMER", font=FONTS["label"], fg=COLORS["text"], bg=self.display_frame['bg'], width=8, height=1)
        self.timer_title.grid(row=1, column=1, pady=(8, 0), padx=(0, 0), sticky="nsew")
        self.mode_title = tk.Label(self.display_frame, text="MODE", font=FONTS["label"], fg=COLORS["text"], bg=self.display_frame['bg'], width=8, height=1)
        self.mode_title.grid(row=1, column=2, pady=(8, 0), padx=(0, 0), sticky="nsew")

        self.speed_label = tk.Label(self.display_frame, text=f"{self.speed}%", font=FONTS["value"], fg=COLORS["text"], bg=self.display_frame['bg'], width=8, height=1)
        self.speed_label.grid(row=2, column=0, pady=(0, 0), padx=(0, 0), sticky="nsew")
        self.time_label = tk.Label(self.display_frame, text="00:00", font=FONTS["value"], fg="#dbefff", bg=self.display_frame['bg'], width=8, height=1)
        self.time_label.grid(row=2, column=1, pady=(0, 0), padx=(0, 0), sticky="nsew")
        self.mode_label = tk.Label(self.display_frame, text=self.mode, font=FONTS["value"], fg=COLORS["text"], bg=self.display_frame['bg'], width=8, height=1)
        self.mode_label.grid(row=2, column=2, pady=(0, 0), padx=(0, 0), sticky="nsew")

        self.speed_time_label = tk.Label(self.display_frame, text="", font=FONTS["label"], fg=COLORS["text"], bg=self.display_frame['bg'], width=8, height=1)
        self.speed_time_label.grid(row=3, column=0, pady=(0, 6), sticky="nsew")
        self.status_label = tk.Label(self.display_frame, text="", font=FONTS["status"], fg="#dbefff", bg=self.display_frame['bg'], width=8, height=1)
        self.status_label.grid(row=4, column=0, columnspan=3, pady=(8, 10), sticky="nsew")       
        
         # --- Test buttons for development ---
        self.test_frame = tk.Frame(root, bg=COLORS["bg"])
        self.test_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        test_label = tk.Label(self.test_frame, text="TEST BUTTONS", font=FONTS["test_label"], fg="#ff9900", bg=COLORS["bg"])
        test_label.pack()
        test_btn_frame = tk.Frame(self.test_frame, bg=COLORS["bg"])
        test_btn_frame.pack()
        test_config = {
            "font": FONTS["button"],
            "width": 2,
            "height": 1,
            "bd": 0,
            "relief": tk.RAISED,
            "bg": "#1f6feb",
            "fg": "#ffffff",
            "activebackground": "#5aa0ff"
        }
        btns = [
            ("PWR", self.toggle_power),
            ("MODE", self.switch_mode),
            ("TIME", self.set_timer),
            ("SPD", self.adjust_speed),
            ("PAUSE", self.toggle_pause),
            ("BT", self.toggle_bluetooth),
            ("Wifi", self.toggle_wifi),
        ]
        for (t, cmd) in btns:
            b = tk.Button(test_btn_frame, text=t, command=cmd, **test_config)
            b.pack(side=tk.LEFT, padx=0, pady=0)
            
         
        # --- Timer loop (updates every second) ---# heartbeat of the project
        self.root.after(1000, self.update_timer)

        # --- GPIO setup using GPIOHandler ---
        self.gpio_handler = None
        if GPIO:
            try:
                self.gpio_handler = GPIOHandler(GPIO_PINS, self.handle_button_press)
                self.root.protocol("WM_DELETE_WINDOW", self.on_close)
            except Exception as e:
                print(f"GPIO not available: {e}")   
                
        #start BLE (after UI widgets exists)
        try:
            self.cm = ConnectivityManager(on_ble_event=self._on_ble_event,ble_name_regex="Shelly|SBBT|BLU")
            self.cm.start_ble()
        except Exception as e:
            print(f"BLE start failed:{e}")
            
            # --- BLE event threading bridge ---
    def _on_ble_event(self, evt: dict):
        """
        Runs in BLE background thread. Marshal to Tk main thread.
        evt => {button, gesture, mac, rssi, raw}
        """
        self.root.after(0, self._handle_ble_event, evt)

    def _handle_ble_event(self, evt: dict):
        """
        Runs in Tk thread. Decides action based on (button, gesture).
        """
        button = evt.get("button")
        gesture = evt.get("gesture")
        if not button or not isinstance(button, int):
            return
        if not gesture or gesture.startswith("unknown"):
            return

        # Mark BLE connected (first valid event)
        if not self.bluetooth_connected:
            self.bluetooth_connected = True
            if getattr(self, "bt_icon_on", None):
                self.bt_img_label.config(image=self.bt_icon_on)

        action = self._ble_actions.get((button, gesture))
        if action:
            action()
            # UI feedback
            try:
               
                self.root.after(1200, lambda: self.status_label.config(text="") if self.power_on else None)
            except Exception:
                pass
        else:
            # Unknown mapping → optional debug
            # print(f"No mapping for BLE (button={button}, gesture={gesture})")
            pass

    # ...existing code...

                
    def toggle_bluetooth(self):
        #toggle bluetooth connection state with animation 
      self._cancel_power_default()
      
      if not self.bluetooth_connected and not self.bt_connecting:
        # Start connecting animation
        self.bt_connecting = True
        self._flash_bluetooth()
        # Simulate connection delay (3 sec)
        self.root.after(3000, self._finish_bt_connect)
      else:
        # Disconnect immediately
        self.bluetooth_connected = False
        self.bt_connecting = False
        if self.bt_flash_id:
            self.root.after_cancel(self.bt_flash_id)
        if self.bt_icon_off:
            self.bt_img_label.config(image=self.bt_icon_off)
        self.status_label.config(
            text="",
            fg=self.colors["disconnected"]
        )
        self.root.after(2000, lambda: self.status_label.config(text=""))
        
    def _flash_bluetooth(self):
        if not self.bt_connecting:
            return
        if self.bt_icon_on and self.bt_icon_off:
        # Get current icon
         current = self.bt_img_label.cget("image")
        # Toggle between ON/OFF icons
        next_icon = self.bt_icon_on if current == str(self.bt_icon_off) else self.bt_icon_off
        self.bt_img_label.config(image=next_icon)
    
    # Schedule next flash in 500ms
        self.bt_flash_id = self.root.after(500, self._flash_bluetooth)
    def _finish_bt_connect(self):
            """Complete BT connection after delay"""
            self.bt_connecting = False
            self.bluetooth_connected = True
            
            # Cancel flashing
            if self.bt_flash_id:
                self.root.after_cancel(self.bt_flash_id)
                
            # Show connected icon
            if self.bt_icon_on:
                self.bt_img_label.config(image=self.bt_icon_on)
                
            # Update status
            self.status_label.config(
                text="",
                fg=self.colors["connected"]
            )
            self.root.after(2000, lambda: self.status_label.config(text=""))
        
      #wifi handling ###
      
    def toggle_wifi(self):
        # Toggle WiFi connection state with animation
        if not self.wifi_connected and not self.wifi_connecting:
            self.wifi_connecting = True
            self._flash_wifi_icon()
            # Simulate connection delay (2 sec)
            self.root.after(2000, self._finish_wifi_connect)
        else:
            # Disconnect immediately
            self.wifi_connected = False
            self.wifi_connecting = False
            if self.wifi_flash_id:
                self.root.after_cancel(self.wifi_flash_id)
            if self.wifi_icon_off:
                self.wifi_img_label.config(image=self.wifi_icon_off)
            self.status_label.config(
                text="",
                fg=self.colors["disconnected"]
            )
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
        self.status_label.config(
            text="",
            fg=self.colors["connected"]
        )
        # ... keep all imports and code up to the GPIO handler section ...

    # --- GPIO handler (correct version) ---
    def handle_button_press(self, channel, level=None):
        """
        Handle GPIO button press/release:
        - Power button: Short press (<2s) = toggle_pause, Long press (≥2s) = toggle_power
        - Other buttons: Act on press only
        """
        if not GPIO:
            return
            
        # If level not passed, read it from GPIO
        if level is None:
            try:
                level = GPIO.input(channel)  # 0 = pressed, 1 = released
            except Exception:
                return

        power_pin = GPIO_PINS['power']

        # --- POWER button special handling ---
        if channel == power_pin:
            if level == 0:  # pressed
                self._press_start[power_pin] = time.time()
                self._power_long_done = False
                # cancel previous timer if any
                if self._power_long_timer_id:
                    try:
                        self.root.after_cancel(self._power_long_timer_id)
                    except Exception:
                        pass
                    self._power_long_timer_id = None
                # schedule long-press check
                self._power_long_timer_id = self.root.after(
                    self.POWER_LONG_MS, 
                    lambda: self._power_long_timeout(power_pin)
                )
            else:  # released
                # cancel pending long timer
                if self._power_long_timer_id:
                    try:
                        self.root.after_cancel(self._power_long_timer_id)
                    except Exception:
                        pass
                    self._power_long_timer_id = None
                self._press_start.pop(power_pin, None)
                if not self._power_long_done:
                    # Short press → pause/resume
                    self.toggle_pause()
                    
                    self.root.after(800, lambda: self.status_label.config(text="") if self.power_on else None)
            return  # stop here for power pin

        # --- Other buttons (act only on press edge) ---
        if level == 0:  # pressed
            if channel == GPIO_PINS['mode']:
                self.switch_mode()
            elif channel == GPIO_PINS['timer']:
                self.set_timer()
            elif channel == GPIO_PINS['speed']:
                self.adjust_speed()
           
            self.root.after(800, lambda: self.status_label.config(text="") if self.power_on else None)

    def _power_long_timeout(self, channel):
        """Called after POWER_LONG_MS; if still holding power button, trigger power toggle."""
        self._power_long_timer_id = None
        if not GPIO:
            return
        try:
            if GPIO.input(channel) == 0:  # still held
                self._power_long_done = True
                self.toggle_power()
             
                self.root.after(800, lambda: self.status_label.config(text=""))
        except Exception as e:
            print(f"Error in power long timeout: {e}")
        
             
    def on_close(self):
        # Cleanup GPIO and close the window
        if self.gpio_handler:
            self.gpio_handler.cleanup()
        if self.cm:
            try: self.cm.stop_ble()
            except Exception:
                pass    
        self.root.destroy()       
        
    
    #---Main Logic Methods-----#
    def toggle_power(self):
        if not self.power_on:
            self.power_on = True
            self.display_frame.config(highlightbackground="#2798AA")   
            self.shadow_frame.config(bg="#7ACAD5")
            if self._power_default_id:
                try:
                    self.root.after_cancel(self._power_default_id)
                except:
                    pass
            self._power_default_id = self.root.after(3000, self._enter_default_after_power)
            self.show_running = False
        else:
            self.power_on = False
            self.remaining_time = 0
            self._cancel_power_default()
            self.show_running = False
            self.running_elapsed = 0
            self.display_frame.config(highlightbackground="#3A4A53")
            self.shadow_frame.config(bg="#7A8A99")
            self.update_labels()
            
    #----Switching between various Modes-----#
            
    def switch_mode(self):   
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
            self.sur_prep = True
            self.show_running = False
        elif self.mode == "P0":
            self.speed = 40 
            self.show_running = True
            self.running_elapsed = 0
        else:
            self.show_running = False
            
        self.status_label.config(text="", fg=self.colors["primary"])
        self.root.after(2000, lambda: self.status_label.config(text="", fg="#4caf50") if self.power_on and not self.paused else None)
        self.update_labels()
            
        
    #------------Set Timer Mode----------#  
    def set_timer(self):
        self._cancel_power_default()
        if not self.power_on:
            return
        self.mode = "T"
        self.current_segment = 0
        self.status_label.config(text="", fg=self.colors["primary"])
        self.root.after(1500, lambda: self.status_label.config(text="", fg="#4caf50") if self.power_on and not self.paused else None)

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
            self._pre_pause_speed = new_speed
        else:
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
        self.status_label.config(text="", fg=self.colors["primary"])
        self.root.after(2000, lambda: self.status_label.config(text="", fg="#4caf50") if self.power_on and not self.paused else None)
        self.update_labels()

    def toggle_pause(self):
        self._cancel_power_default()
        if not self.power_on:
            self.display_frame.config(highlightbackground="#12314a")
            return
        self.paused = not self.paused
        if self.paused:
            self._pre_pause_speed = getattr(self, '_pre_pause_speed', self.speed)
            self.speed = 0
            self.display_frame.config(highlightbackground="#A3D9E6")
            self.shadow_frame.config(bg="#BFE5EA")
            self._auto_off_id = self.root.after(30 * 60 * 1000, self._auto_power_off)
        else:
            if hasattr(self, '_pre_pause_speed'):
                self.speed = self._pre_pause_speed
            self.display_frame.config(highlightbackground="#2798AA")
            self.shadow_frame.config(bg="#7ACAD5")
            if hasattr(self, '_auto_off_id') and self._auto_off_id:
                try:
                    self.root.after_cancel(self._auto_off_id)
                except:
                    pass
                self._auto_off_id = None

    def _auto_power_off(self):
        try:
            self.power_on = False
            self.paused = False
            self.remaining_time = 0
            self.speed = 0
            self.status_label.config(text="", fg="#cccccc")
            self.update_labels()
        except Exception:
            pass

    def update_timer(self):
        if self.power_on and not self.paused:
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
            elif self.remaining_time > 0:
                self.remaining_time -= 1
                if self.remaining_time == 0 and self.mode != "P0":
                    self.status_label.config(fg="#ff9800")
                    self._start_finish_flash()
            if self.mode.startswith("P") and int(self.mode[1:]) in range(1, 5):
                if self.current_segment < len(self.training_plans[self.mode]):
                    duration, seg_speed = self.training_plans[self.mode][self.current_segment]
                    if duration > 0:
                        self.speed = seg_speed
                        duration -= 1
                        self.training_plans[self.mode][self.current_segment] = (duration, seg_speed)
                    else:
                        self.current_segment += 1
            self.update_labels()
        self.root.after(1000, self.update_timer)

    def update_labels(self):
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
        self._finish_flash_count = 0
        self._finish_flash_id = self.root.after(0, self._finish_flash_tick)

    def _finish_flash_tick(self):
        try:
            if getattr(self, '_finish_flash_count', 0) >= 6:
                self._finish_flash_count = 0
                self.mode = "P0"
                self.timer_duration = 0
                self.remaining_time = 0
                self.current_segment = 0
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
        self._power_default_id = None
        if not self.power_on:
            return
        self.mode = "P0"
        self.speed = 40
        self.remaining_time = 0
        self.current_segment = 0
        self.show_running = True
        self.running_elapsed = 0
        self.status_label.config(text="", fg=self.colors["primary"])
        self.update_labels()

    def _cancel_power_default(self):
        if getattr(self, '_power_default_id', None):
            try:
                self.root.after_cancel(self._power_default_id)
            except:
                pass
            self._power_default_id = None    
            
                    
         
                    