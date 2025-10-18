from dataclasses import dataclass, field
from typing import Optional, List

REQUIRED_FIELDS = [
    "full_name",
    "service_address",
    "phone_number",
    "email",
    "service_request",
    "date",         # YYYY-MM-DD
    "time_window",  # HH:MM-HH:MM
]

@dataclass
class ConversationState:
    full_name: Optional[str] = None
    service_address: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None

    # Issue
    service_request: Optional[str] = None
    # MUST be True trước khi recap/finalize
    service_request_confirmed: bool = False

    date: Optional[str] = None
    time_window: Optional[str] = None

    # Optional
    lead_source: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    # Runtime
    done: bool = False
    appointment_id: Optional[str] = None

    def missing(self) -> List[str]:
        """
        Trả về danh sách field REQUIRED chưa có GIÁ TRỊ.
        Lưu ý: cờ confirm issue xử lý ở agent, không nằm trong REQUIRED_FIELDS.
        """
        return [f for f in REQUIRED_FIELDS if not getattr(self, f)]

    def to_payload(self) -> dict:
        return {
            "full_name": self.full_name,
            "service_address": self.service_address,
            "phone_number": self.phone_number,
            "email": self.email,
            "service_request": self.service_request,
            "date": self.date,
            "time_window": self.time_window,
            "lead_source": self.lead_source,
            "notes": self.notes,
        }
