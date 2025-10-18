import re
from datetime import datetime, timedelta
from typing import Optional

# ---------- Phone ----------
_PHONE_NON_DIGIT_RE = re.compile(r"\D+")

def normalize_phone(s: str) -> Optional[str]:
    """Return digits-only phone with length 10–11; else None."""
    digits = _PHONE_NON_DIGIT_RE.sub("", s or "")
    return digits if 10 <= len(digits) <= 11 else None

# ---------- Email ----------
def looks_like_email(s: str) -> bool:
    """Very light email validation."""
    return bool(s) and bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", s.strip()))

# ---------- Address ----------
def looks_like_address(s: str) -> bool:
    """Minimum: street number + at least one word token."""
    return bool(re.search(r"\d+\s+\w+", s or ""))

# ---------- Date normalization ----------
def to_iso_date(s: str) -> Optional[str]:
    """Map 'tomorrow' or common formats to YYYY-MM-DD; else None."""
    if not s:
        return None
    raw = s.strip().lower()
    if raw in {"tomorrow", "tmrw"}:
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None

# ---------- Time window normalization ----------
def to_window_or_none(s: str, default_hours: int = 1) -> Optional[str]:
    """
    Accept:
      - 'HH:MM-HH:MM'
      - 'HH:MM' -> expand to default_hours
      - '11 am' / '3pm' -> expand to default_hours
    Return normalized 'HH:MM-HH:MM' or None.
    """
    s = (s or "").strip()

    if re.match(r"^\d{1,2}:\d{2}-\d{1,2}:\d{2}$", s):
        return s

    m = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if m:
        h, mnt = int(m.group(1)), int(m.group(2))
        start = f"{h:02d}:{mnt:02d}"
        end_h = (h + default_hours) % 24
        end = f"{end_h:02d}:{mnt:02d}"
        return f"{start}-{end}"

    m = re.match(r"^(\d{1,2})\s*(am|pm)$", s, re.I)
    if m:
        h = int(m.group(1)) % 12
        if m.group(2).lower() == "pm":
            h += 12
        start = f"{h:02d}:00"
        end = f"{(h + default_hours) % 24:02d}:00"
        return f"{start}-{end}"

    return None

# ---------- Heuristics ----------
_NAME_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z.'-]*$")

def is_probably_name(s: str) -> bool:
    """
    Heuristic cho 'full name':
    - 2–4 token
    - Không có số / '@'
    - Token chỉ gồm chữ và . ' -
    """
    if not s:
        return False
    txt = s.strip()
    if any(ch.isdigit() for ch in txt):
        return False
    if "@" in txt:
        return False
    tokens = [t for t in re.split(r"\s+", txt) if t]
    if not (2 <= len(tokens) <= 4):
        return False
    return all(_NAME_TOKEN_RE.match(t) for t in tokens)

_SERVICE_HINTS = (
    "estimate", "install", "add", "repair", "leak", "drain",
    "toilet", "sink", "shower", "water heater", "convert",
    "apartment", "clog", "burst", "pipe"
)

def looks_like_service_request(s: str) -> bool:
    """True nếu câu có vẻ mô tả nhu cầu dịch vụ (chứa keyword plumbing & >= ~3 từ)."""
    if not s:
        return False
    low = s.lower()
    return any(k in low for k in _SERVICE_HINTS) and len(low.split()) >= 3
