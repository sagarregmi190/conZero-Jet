#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')
import tkinter as tk
from services.fault_service import FaultMonitor
from core.config import FAULT_COLORS, FONTS

root = tk.Tk()
root.title("Fault Test")
root.geometry("480x320")
root.configure(bg="#071226")

display_frame = tk.Frame(root, bg="#071226", highlightthickness=16, highlightbackground="#12314a")
display_frame.pack(fill=tk.BOTH, expand=True)

status_label = tk.Label(display_frame, text="", font=FONTS["status"], fg=FAULT_COLORS["active"], 
                       bg="#071226", wraplength=450, justify="center")
status_label.pack(expand=True)

info_label = tk.Label(display_frame, text="Press SPACE for next fault", font=("Rajdhani", 10), 
                     fg="#aaaaaa", bg="#071226")
info_label.pack(side=tk.BOTTOM, pady=10)

test_faults = [
    0x0001, 0x0002, 0x0004, 0x0008, 0x0010,
    0x0020, 0x0040, 0x0080, 0x0100, 0x0200,
    0x0003, 0x0024, 0x0210
]

current = [0]

def show_fault(code):
    fault_monitor = FaultMonitor(on_fault_changed=lambda f, c: None)
    fault_monitor.update_faults(code)
    msg = fault_monitor.get_fault_message()
    font = ("Rajdhani", 14) if len(fault_monitor.active_fault_list) == 1 else ("Rajdhani", 12)
    status_label.config(text=msg, font=font)
    color = "#cc0000" if code & 0x0280 else "#ff9800"
    display_frame.config(highlightbackground=color)
    info_label.config(text=f"Fault {current[0]+1}/{len(test_faults)} | 0x{code:04X} | Press SPACE")

def next_fault(e=None):
    show_fault(test_faults[current[0]])
    current[0] = (current[0] + 1) % len(test_faults)

root.bind('<space>', next_fault)
next_fault()
root.mainloop()
