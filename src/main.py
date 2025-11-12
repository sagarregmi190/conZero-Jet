#Main entry point for thr SwimJet UI application 
#This files launches the TKinter GUI using the SwimJet Class
import tkinter as tk 
from conzero_jet_ui import JetUI



if __name__ == "__main__":
    root=tk.Tk()
    app=JetUI(root)
    root.mainloop()

