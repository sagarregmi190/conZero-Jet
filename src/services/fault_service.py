"""
Fault Monitoring Service (localized)

This implementation uses core.i18n_helpers.get_fault_names() so fault labels
are always returned in the currently selected language.
"""
from typing import Optional, List, Callable
from core.config import FAULT_NAMES, STALL_FAULTS, CLEARABLE_FAULTS, FAULT_COLORS, get_fault_names
from core.translations import t

class FaultMonitor:
    def __init__(self, on_fault_changed: Optional[Callable[[Optional[List[str]], str], None]] = None):
        """
        on_fault_changed callback signature: callback(fault_list_or_None, color_key)
        color_key: "normal", "warning", "active"
        """
        self.on_fault_changed = on_fault_changed
        self.current_faults: int = 0
        self.active_fault_list: List[str] = []
        self.system_stalled: bool = False

    def update_faults(self, fault_code: int) -> None:
        old_faults = self.current_faults
        self.current_faults = int(fault_code)

        fault_names = get_fault_names()
        self.active_fault_list = [
            name for bit, name in fault_names.items() if (self.current_faults & bit)
        ]

        self.system_stalled = bool(self.current_faults & STALL_FAULTS)

        if old_faults != self.current_faults and self.on_fault_changed:
            if self.current_faults == 0:
                try:
                    self.on_fault_changed(None, "normal")
                except Exception as e:
                    print(f"[FaultMonitor] callback error (clear): {e}")
            else:
                color = "active" if self.system_stalled else "warning"
                try:
                    self.on_fault_changed(self.active_fault_list, color)
                except Exception as e:
                    print(f"[FaultMonitor] callback error (set): {e}")

    def get_fault_message(self) -> str:
        if not self.active_fault_list:
            return ""

        if len(self.active_fault_list) == 1:
            return t("fault.single_format", fault=self.active_fault_list[0])
        else:
            header = t("fault.multiple_format", count=len(self.active_fault_list))
            numbered = "\n".join(f"{i+1}. {name}" for i, name in enumerate(self.active_fault_list))
            return f"{header}\n{numbered}"

    def is_stalled(self) -> bool:
        return self.system_stalled

    def has_stall_faults(self) -> bool:
        """Check if any stall faults are present"""
        return bool(self.current_faults & STALL_FAULTS)

    def has_clearable_faults(self) -> bool:
        """Check if any clearable faults are present"""
        return bool(self.current_faults & CLEARABLE_FAULTS)

    # helpers
    def get_fault_code(self) -> int:
        return self.current_faults

    def has_faults(self) -> bool:
        return self.current_faults != 0

    def get_active_faults(self) -> List[str]:
        return list(self.active_fault_list)

    def clear_faults(self) -> None:
        self.update_faults(0)

    def get_fault_color(self) -> str:
        if self.current_faults == 0:
            return "normal"
        return "active" if self.system_stalled else "warning"