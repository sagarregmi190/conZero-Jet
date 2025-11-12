"""
Fault Monitoring Service
Handles fault detection, display, and management
"""

from typing import Callable, List, Optional
from core.config import FAULT_NAMES, STALL_FAULTS, CLEARABLE_FAULTS, FAULT_COLORS

class FaultMonitor:
    """Monitors and displays motor faults"""
    
    def __init__(self, on_fault_changed: Callable[[Optional[List[str]], str], None]):
        """
        Initialize fault monitor
        
        Args:
            on_fault_changed: Callback function(fault_list, color_key)
                - fault_list: None if no faults, list of fault names if faults present
                - color_key: "normal", "active", "warning"
        """
        self.on_fault_changed = on_fault_changed
        self.current_faults = 0x0000
        self.active_fault_list = []
        self.system_stalled = False
        self._fault_display_index = 0
    
    def update_faults(self, fault_flags: int) -> bool:
        """
        Process new fault flags and update state
        
        Args:
            fault_flags: 32-bit fault register value
            
        Returns:
            True if faults changed, False if same
        """
        # Check if faults actually changed
        if fault_flags == self.current_faults:
            return False
        
        self.current_faults = fault_flags
        
        if fault_flags == 0:
            # No faults - clear state
            self.active_fault_list = []
            self.system_stalled = False
            print(" All faults cleared")
            self.on_fault_changed(None, "normal")
            return True
        else:
            # Decode active faults
            self.active_fault_list = []
            for bit_value, fault_name in FAULT_NAMES.items():
                if fault_flags & bit_value:
                    self.active_fault_list.append(fault_name)
            
            # Check if stall faults present
            self.system_stalled = bool(fault_flags & STALL_FAULTS)
            
            print(f" Faults detected: {', '.join(self.active_fault_list)}")
            if self.system_stalled:
                print("CRITICAL: System stalled due to fault")
            
            # Notify UI
            self.on_fault_changed(self.active_fault_list, "active")
            return True
    
    def get_fault_message(self) -> str:
        """
        Format fault message for display
        
        Returns:
            Formatted fault message string
        """
        if not self.active_fault_list:
            return ""
        
        if len(self.active_fault_list) == 1:
            # Single fault - simple display
            return f"FAULT: {self.active_fault_list[0]}"
        
        # Multiple faults - display in 2 columns
        columns = 2
        fault_lines = []
        items_per_col = (len(self.active_fault_list) + columns - 1) // columns
        
        for row in range(items_per_col):
            line_parts = []
            for col in range(columns):
                index = row + col * items_per_col
                if index < len(self.active_fault_list):
                    fault_name = self.active_fault_list[index]
                    line_parts.append(f"{index+1}. {fault_name}")
                else:
                    line_parts.append("")  # Empty for alignment
            
            fault_lines.append("    ".join(line_parts))
        
        return "\n".join(fault_lines)
    
    def has_faults(self) -> bool:
        """Check if any faults are present"""
        return self.current_faults != 0
    
    def is_stalled(self) -> bool:
        """Check if system is stalled due to critical faults"""
        return self.system_stalled
    
    def has_clearable_faults(self) -> bool:
        """Check if current faults can be cleared"""
        return bool(self.current_faults & CLEARABLE_FAULTS)
    
    def has_stall_faults(self) -> bool:
        """Check if stall faults are present"""
        return bool(self.current_faults & STALL_FAULTS)
    
    def get_fault_color(self) -> str:
        """
        Get appropriate color for current fault state
        
        Returns:
            Hex color code string
        """
        if self.current_faults == 0:
            return FAULT_COLORS["normal"]
        elif self.system_stalled:
            return FAULT_COLORS["active"]
        else:
            return FAULT_COLORS["warning"]
    
    def reset(self):
        """Reset fault monitor state"""
        self.current_faults = 0x0000
        self.active_fault_list = []
        self.system_stalled = False
        self._fault_display_index = 0
        print("🔄 Fault monitor reset")
        