from .state import ConversationState, REQUIRED_FIELDS
from .validators import (
    normalize_phone, looks_like_email, looks_like_address,
    to_iso_date, to_window_or_none,
    is_probably_name, looks_like_service_request
)
from .tools import (
    check_coverage, check_availability,
    create_appointment, send_confirmation
)
from .config import CONFIG

PROMPTS = {
    "full_name": "May I have your full name (first and last)?",
    "service_address": "What is the service address (street number + street name; city/zip if available)?",
    "phone_number": "What is the best phone number to reach you?",
    "email": "What email should we use for the confirmation?",
    "service_request": "Briefly, what is the plumbing issue or request?",
    "date": "Which date works? (YYYY-MM-DD or 'tomorrow')",
    "time_window": "What time works? (HH:MM-HH:MM or a single time like '11:00' or '11 am')",
}

def _confirm_issue_prompt(state: ConversationState) -> str:
    return f'I noted your issue as: "{state.service_request}". Is that correct? (yes/no)'

class Agent:
    """
    Policy 'plus':
      - Pre-capture service_request từ câu tự do, NHƯNG yêu cầu confirm.
      - Hỏi từng field còn thiếu.
      - Check coverage sau address (nếu bật).
      - Check availability ở time_window.
      - Recap chỉ khi đã đủ field VÀ issue đã confirm.
    """

    def next_prompt(self, state: ConversationState) -> str:
        # Nếu đã có issue mà chưa confirm → ưu tiên xác nhận
        if state.service_request and not state.service_request_confirmed:
            return _confirm_issue_prompt(state)
        missing = state.missing()
        return PROMPTS[missing[0]] if missing else ""

    def recap(self, state: ConversationState) -> str:
        return (
            f"Let me confirm: {state.full_name} at {state.service_address}. "
            f"Phone {state.phone_number}, email {state.email}. "
            f"Issue: {state.service_request}. "
            f"Appointment on {state.date}, {state.time_window}. "
            f"Is everything correct? (yes/no)"
        )

    def finalize(self, state: ConversationState, yes: bool) -> str:
        if not yes:
            fields = ", ".join(REQUIRED_FIELDS)
            return f"No problem—what would you like to change? ({fields})"

        # Guards
        if state.missing():
            return "We are missing some details. " + self.next_prompt(state)
        if not state.service_request_confirmed:
            return _confirm_issue_prompt(state)

        payload = state.to_payload()
        apt_id = create_appointment(payload)
        state.appointment_id = apt_id
        if CONFIG.send_email_confirmation_after_booking:
            send_confirmation("email", payload)
        state.done = True

        tail = " The technician may call ahead." if CONFIG.technician_may_call_ahead else ""
        return f"All set! Your appointment ID is {apt_id}. You will receive an email confirmation shortly.{tail}"

    def update(self, state: ConversationState, user_text: str) -> str:
        text = (user_text or "").strip()

        # --- Pre-capture issue từ câu tự do (chưa confirm) ---
        if not state.service_request and looks_like_service_request(text):
            state.service_request = text
            state.service_request_confirmed = False  # bắt buộc xác nhận

        # --- Nếu đang cần xác nhận issue, xử lý yes/no tại đây ---
        if state.service_request and not state.service_request_confirmed:
            low = text.lower()
            if low in {"yes", "y"}:
                state.service_request_confirmed = True
                if not state.missing():
                    return self.recap(state)
                return self.next_prompt(state)
            if low in {"no", "n"}:
                state.service_request = None
                state.service_request_confirmed = False
                return "No problem—please describe the plumbing issue or request briefly."
            # Nếu người dùng mô tả lại issue thay vì yes/no → nhận luôn và xác nhận xong
            if looks_like_service_request(text):
                state.service_request = text
                state.service_request_confirmed = True
                if not state.missing():
                    return self.recap(state)
                return self.next_prompt(state)
            # Nếu không phải yes/no, nhắc lại
            return 'Please answer "yes" or "no" about the issue I noted.'

        # --- Nếu đã đủ field (và issue đã confirm) → recap ---
        if not state.missing():
            return self.recap(state)

        # --- Hỏi lần lượt theo slot ---
        want = state.missing()[0]

        if want == "full_name":
            if is_probably_name(text):
                state.full_name = text
                return self.next_prompt(state)
            return PROMPTS["full_name"]

        if want == "service_address":
            if looks_like_address(text):
                state.service_address = text
                if CONFIG.require_coverage_check_before_slots:
                    cov = check_coverage(text)
                    if not cov["covered"]:
                        return "I’m sorry, it looks like we do not cover that area. Would you like a nearby referral?"
                return self.next_prompt(state)
            return "Please include a street number and street name (e.g., '33 Main St, Springfield')."

        if want == "phone_number":
            ph = normalize_phone(text)
            if ph:
                state.phone_number = ph
                return self.next_prompt(state)
            return "I didn’t catch that—please read the digits (10–11 digits)."

        if want == "email":
            if looks_like_email(text):
                state.email = text
                return self.next_prompt(state)
            return "That email looks off. Please provide one like name@example.com."

        if want == "service_request":
            if len(text) >= 3:
                state.service_request = text
                state.service_request_confirmed = True
                return self.next_prompt(state)
            return "A short description helps the technician—what seems to be the issue?"

        if want == "date":
            iso = to_iso_date(text)
            if iso:
                state.date = iso
                return self.next_prompt(state)
            return "Please provide a date like 2025-10-21 or say 'tomorrow'."

        if want == "time_window":
            w = to_window_or_none(text, default_hours=CONFIG.default_window_hours)
            if w:
                a = check_availability(state.date or "", w, cfg=CONFIG)
                if a["available"]:
                    state.time_window = w
                    # Chỉ recap nếu issue đã confirm
                    if state.service_request_confirmed:
                        return self.recap(state)
                    return self.next_prompt(state)
                return f"Sorry, {w} is booked. I can do {', '.join(a['alternatives'])}. Which do you prefer?"
            return "Please provide a time like '11:00-12:00' or a single time '11:00' / '11 am'."

        return "Thanks—let’s continue."
