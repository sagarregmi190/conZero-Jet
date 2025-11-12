#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')
import tkinter as tk
from services.fault_service import FaultMonitor
from core.config import FAULT_COLORS, FONTS

root = tk.Tk()
root.title("All 10 Faults Test")
root.geometry("480x320")
root.configure(bg="#071226")

display_frame = tk.Frame(
    root, 
    bg="#071226", 
    highlightthickness=16, 
    highlightbackground="#cc0000"
)
display_frame.pack(fill=tk.BOTH, expand=True)

status_label = tk.Label(
    display_frame, 
    text="", 
    font=("Rajdhani", 12),
    fg=FAULT_COLORS["active"], 
    bg="#071226", 
    wraplength=450, 
    justify="center"
)
status_label.pack(expand=True)

# ALL 10 FAULTS AT ONCE (0x03FF = all 10 bits set)
all_faults_code = 0x03FF

def on_fault_changed(fault_list, color_key):
    """Callback - not used in this test"""
    pass

fault_monitor = FaultMonitor(on_fault_changed=on_fault_changed)
fault_monitor.update_faults(all_faults_code)

# Get the EXACT formatted message from FaultMonitor
message = fault_monitor.get_fault_message()

# Display it
status_label.config(text=message)

print("="*60)
print("SHOWING ALL 10 FAULTS SIMULTANEOUSLY")
print("="*60)
print(message)
print("="*60)
print(f"Total faults: {len(fault_monitor.active_fault_list)}")
print(f"System stalled: {fault_monitor.system_stalled}")
print(f"Fault code: 0x{all_faults_code:04X}")
print("="*60)

root.mainloop()
