from dataclasses import dataclass, field
from typing import List

@dataclass
class BusinessConfig:
    # If caller gives a single time (e.g., "11:00" or "11 am"), expand to this many hours
    default_window_hours: int = 1

    # Demo: busy windows to force alternative offering
    busy_windows: List[str] = field(default_factory=lambda: ["12:00-14:00"])

    # Alternatives to propose when busy
    alternative_windows: List[str] = field(default_factory=lambda: ["10:00-12:00", "14:00-16:00"])

    # Toggle/extend behaviors
    require_coverage_check_before_slots: bool = True
    recap_before_finalize: bool = True
    send_email_confirmation_after_booking: bool = True
    technician_may_call_ahead: bool = True

# Default singleton config
CONFIG = BusinessConfig()
