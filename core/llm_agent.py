# core/llm_agent.py
"""
LLM-driven dialog manager (semantic parse + NLG), still enforced by validators & mock tools.

- Extract slots from user free-form text via chat_json() and merge into state.
- Ask for the next missing field using NLG per prompt.
- Check coverage & availability (mock), then recap, confirm, and finalize (mock booking + email).
"""

from __future__ import annotations
from typing import List, Optional

from .state import ConversationState, REQUIRED_FIELDS
from .validators import (
    normalize_phone, looks_like_email, looks_like_address,
    to_iso_date, to_window_or_none,
)
from .tools import (
    check_coverage, check_availability,
    create_appointment, send_confirmation,
)
from .config import CONFIG
from .llm import load_prompt, chat_json, chat_text


SCHEMA = [
    "full_name",
    "service_address",
    "phone_number",
    "email",
    "service_request",
    "date",
    "time_window",
    "lead_source",
]


def _merge_slots(state: ConversationState, slots: dict) -> None:
    """Merge parsed JSON slots into state with validation."""
    if not slots:
        return
    v = slots.get("full_name")
    if v and len(v.split()) >= 2:
        state.full_name = v.strip()

    v = slots.get("service_address")
    if v and looks_like_address(v):
        state.service_address = v.strip()

    v = slots.get("phone_number")
    if v:
        ph = normalize_phone(v)
        if ph:
            state.phone_number = ph

    v = slots.get("email")
    if v and looks_like_email(v):
        state.email = v.strip()

    v = slots.get("service_request")
    if v and len(v.strip()) >= 3:
        state.service_request = v.strip()
        # For LLM agent, treat an explicit user description as confirmed
        if hasattr(state, "service_request_confirmed"):
            state.service_request_confirmed = True

    v = slots.get("date")
    if v:
        iso = to_iso_date(v)
        if iso:
            state.date = iso

    v = slots.get("time_window")
    if v:
        w = to_window_or_none(v, default_hours=CONFIG.default_window_hours)
        if w:
            state.time_window = w

    v = slots.get("lead_source")
    if v:
        state.lead_source = v.strip()


def _need_next_field(state: ConversationState) -> Optional[str]:
    """
    Determine the next required field to ask for.
    If your ConversationState uses service_request_confirmed flag, prioritize it.
    """
    if getattr(state, "service_request", None) and not getattr(state, "service_request_confirmed", True):
        return "service_request"
    missing = state.missing()
    return missing[0] if missing else None


def _ask_for(field: str) -> str:
    prompts = {
        "full_name": "May I have your full name (first and last)?",
        "service_address": "What is the service address (street number + street name; city/zip if available)?",
        "phone_number": "What is the best phone number to reach you?",
        "email": "What email should we use for the confirmation?",
        "service_request": "Briefly, what is the plumbing issue or request?",
        "date": "Which date works? (YYYY-MM-DD or 'tomorrow')",
        "time_window": "What time works? (HH:MM-HH:MM or a single time like '11:00' or '11 am')",
    }
    return prompts[field]


class LLMAgent:
    """
    Simple LLM agent:
    - Uses LLM to semantically parse user text into slots (JSON).
    - Keeps the deterministic business rules via validators and mock tools.
    - Uses the same recap/finalize pattern as the rule-based agent.
    """

    def __init__(self) -> None:
        self.system = load_prompt()

    # ---------- NLG helper ----------
    def _say(self, draft: str, state: ConversationState) -> str:
        ctx = state.notes[-3:] if getattr(state, "notes", None) else []
        user_prompt = (
            "Rewrite the assistant reply for a courteous call-center agent. "
            "Keep all facts unchanged. Be concise, one sentence.\n"
            f"Draft: {draft}\n"
            f"Recent context: {ctx}"
        )
        return chat_text(self.system, user_prompt, temperature=0.2)

    # ---------- Main stages ----------
    def recap(self, state: ConversationState) -> str:
        msg = (
            f"Let me confirm: {state.full_name} at {state.service_address}. "
            f"Phone {state.phone_number}, email {state.email}. "
            f"Issue: {state.service_request}. "
            f"Appointment on {state.date}, {state.time_window}. "
            f"Is everything correct? (yes/no)"
        )
        return self._say(msg, state)

    def finalize(self, state: ConversationState, yes: bool) -> str:
        if not yes:
            fields = ", ".join(REQUIRED_FIELDS)
            return self._say(f"No problem—what would you like to change? ({fields})", state)

        need = _need_next_field(state)
        if need:
            return self._say("We are missing some details.", state)

        payload = state.to_payload()
        apt_id = create_appointment(payload)
        state.appointment_id = apt_id
        send_confirmation("email", payload)
        state.done = True
        return self._say(
            f"All set! Your appointment ID is {apt_id}. You will receive an email confirmation shortly.",
            state,
        )

    # ---------- Update turn ----------
    def update(self, state: ConversationState, user_text: str) -> str:
        # 1) Extract slots from free-form using LLM (noop if USE_LLM=0 → {})
        extract_prompt = (
            "Extract the following fields as JSON with keys:\n"
            + ", ".join(SCHEMA)
            + ". Use null if unknown.\n"
              "- time_window can be 'HH:MM-HH:MM' or a single time like '11:00' or '3 pm'.\n"
              "- date can be 'YYYY-MM-DD' or 'tomorrow'.\n"
              "User says:\n" + (user_text or "")
        )
        slots = chat_json(self.system, extract_prompt, temperature=0.1)
        _merge_slots(state, slots)

        # 2) If still missing any required field → ask next field
        need = _need_next_field(state)
        if need:
            # coverage check when address is provided right now in free-form
            if need == "service_address" and looks_like_address(user_text or ""):
                state.service_address = (user_text or "").strip()
                cov = check_coverage(state.service_address)
                if not cov["covered"]:
                    return self._say("I’m sorry, it looks like we do not cover that area. Would you like a nearby referral?", state)
                # recompute next need
                need = _need_next_field(state)
                if not need:
                    # fall through to availability/recap
                    pass
            if need:
                return self._say(_ask_for(need), state)

        # 3) If we have date & time_window, check availability (mock)
        if state.date and state.time_window:
            avail = check_availability(state.date, state.time_window, cfg=CONFIG)
            if not avail["available"]:
                alts = ", ".join(avail["alternatives"])
                return self._say(f"Sorry, {state.time_window} is booked. I can do {alts}. Which do you prefer?", state)

        # 4) Otherwise, recap
        return self.recap(state)
