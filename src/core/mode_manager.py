#ModeManager class for handling mode logic , duration and training plans .

from core.config import TRAINING_PLANS, MODE_DURATIONS, MODE_NAMES

class ModeManager:
    "Handles mode transition, duration and training Plan retrieval"
    
    def __init__(self):
        # List of all available modes 
        self.modes = list(MODE_NAMES.keys())  # ["P0", "T", "P1", "P2", "P3", "P4", "P5"]
        
    def get_next_mode(self, current_mode):
        #returns the next mode in the sequence.
        idx = self.modes.index(current_mode)
        return self.modes[(idx+1) % len(self.modes)]
    
    def get_mode_durations(self,mode):
        #returns the default duration for a mode in sec 
        return MODE_DURATIONS.get(mode,0)
    
    def get_training_plan(self,mode):
        #returns the training plan for a given mode 
        return TRAINING_PLANS.get(mode,[])
    
    def get_mode_name(self,mode):
        #returns the mode names 
        return MODE_NAMES.get(mode,mode)
        