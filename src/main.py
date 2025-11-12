#!/usr/bin/env python3
# Main entry point for the Jet UI application 
# This files launches the TKinter GUI using the JetUI Class
import os
import tkinter as tk 
from ui_handlers.conzero_jet_ui import JetUI


if __name__ == "__main__":
    FULLSCREEN = True  # set True to start fullscreen, False for windowed
    root = tk.Tk()
    root.attributes("-fullscreen", FULLSCREEN)
    # Optional: toggle fullscreen with F11 and exit fullscreen with Escape
    root.bind("<F11>", lambda e: root.attributes("-fullscreen", not root.attributes("-fullscreen")))
    root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False))
    
  

    app = JetUI(root)
    root.mainloop()