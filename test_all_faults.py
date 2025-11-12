#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')
import tkinter as tk
from services.fault_service import FaultMonitor
from core.config import FAULT_COLORS, FONTS

root = tk.Tk()
root.title("All Faults Test")
root.geometry("480x320")
root.configure(bg="#071226")

display_frame = tk.Frame(root, bg="#071226", highlightthickness=16, highlightbackground="#cc0000")
display_frame.pack(fill=tk.BOTH, expand=True)

status_label = tk.Label(
    display_frame, 
    text="", 
    font=("Rajdhani", 11),
    fg=FAULT_COLORS["active"], 
    bg="#071226", 
    wraplength=450, 
    justify="left"
)
status_label.pack(expand=True)

# ALL 10 FAULTS AT ONCE
all_faults_code = 0x03FF  # Binary: 1111111111 (all 10 bits set)

fault_monitor = FaultMonitor(on_fault_changed=lambda f, c: None)
fault_monitor.update_faults(all_faults_code)

# Get numbered fault list
fault_list = fault_monitor.active_fault_list
numbered_faults = "\n".join([f"{i+1}. {fault}" for i, fault in enumerate(fault_list)])

message = f"FAULTS ({len(fault_list)}):\n\n{numbered_faults}"

status_label.config(text=message)

print(f"Showing {len(fault_list)} faults simultaneously")
print(message)

root.mainloop()
