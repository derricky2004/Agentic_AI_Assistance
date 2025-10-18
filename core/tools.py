from typing import Dict, Any
from .validators import looks_like_address
from .config import BusinessConfig, CONFIG

def check_coverage(service_address: str) -> Dict[str, bool]:
    """Demo coverage: valid-looking addresses are covered."""
    return {"covered": looks_like_address(service_address)}

def check_availability(date_iso: str, window: str, *, cfg: BusinessConfig = CONFIG) -> Dict[str, Any]:
    """Demo availability: mark certain windows as busy and offer alternatives."""
    busy = set(cfg.busy_windows)
    if window in busy:
        return {"available": False, "alternatives": list(cfg.alternative_windows)}
    return {"available": True, "alternatives": []}

def create_appointment(payload: dict) -> str:
    """Demo booking: create a short-ish ID."""
    from datetime import datetime
    ts = datetime.now().strftime("%m%d%H%M%S")
    return f"APT-{ts}"

def send_confirmation(contact_method: str, payload: dict) -> Dict[str, Any]:
    """Demo confirmation always OK."""
    return {"ok": True, "channel": contact_method}
