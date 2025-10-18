# Technical Design — Jacob’s Plumbing Agentic AI

This document explains the architecture and design choices behind the **rule-based** and **LLM** agents, context handling, validation logic, mock tool contracts, configuration matrix, and testing/deployment notes.

> TL;DR  
> - **Two runtimes**: deterministic **Rule-based** and **LLM-driven** (semantic parsing + NLG).  
> - **Prompt incorporated**: `core/prompt.txt` guides tone/behavior; enforced by rules and/or LLM NLG.  
> - **Tool calls**: coverage, availability, booking, confirmation — implemented as mock functions.

---

## 1) Architecture Overview

### 1.1 Components
- **`core/state.py`**  
  Conversation data model + required fields ordering, helpers `missing()` and `to_payload()`.

- **`core/validators.py`**  
  Input normalization and validation (phone/email/address/date/time) + heuristics (name / service text).

- **`core/tools.py`**  
  Mock “business” APIs:
  - `check_coverage(address) -> {"covered": bool}`
  - `check_availability(date, time_window, cfg) -> {"available": bool, "alternatives":[..]}`
  - `create_appointment(payload) -> "APT-..."`
  - `send_confirmation(channel, payload) -> None`

- **`core/config.py`**  
  Policy toggles and demo availability (busy windows).

- **`core/agent.py`** — *Rule-based agent*  
  Deterministic state machine (no external models). Asks for missing fields, confirms service request, checks tools, recaps, finalizes.

- **`core/llm.py`**  
  Loads `prompt.txt`. Optional calls to **Ollama** (`/api/generate`) for:
  - `polish_reply` (NLG-only rewrite per prompt; safe fallback if `USE_LLM=0`)
  - `chat_text`, `chat_json` (LLM utilities, with robust JSON parsing fallback)

- **`core/llm_agent.py`** — *LLM agent*  
  Uses LLM to **extract slots** from free-form inputs (JSON) and **rewrite replies** per prompt, while validators & tools enforce correctness.

- **`core/cli.py`**  
  Command-line chat loop. Modes: `--mode rule | llm`. Auto-records transcripts to `logs/session-*.csv`. Maintains short **context memory** in `state.notes`.

### 1.2 Data Flow (high-level)
1. **User turn** → `cli.py` → `agent.update(state, user_text)`  
2. Agent decides:  
   - Rule-based: pattern/validators → next prompt or recap  
   - LLM: `chat_json` to parse slots → merge → next prompt or recap  
3. When address provided: `check_coverage` (optional by config)  
4. When date & time_window set: `check_availability`  
5. If all required fields present **and** service request confirmed:  
   - **Recap** → user confirms `yes`  
   - `create_appointment` → `send_confirmation` (mock) → Done

---

## 2) State Model

### 2.1 Required Fields (ordered)
```
full_name → service_address → phone_number → email → service_request → date → time_window
```

### 2.2 ConversationState (essentials)
```python
class ConversationState:
    full_name: str | None
    service_address: str | None
    phone_number: str | None
    email: str | None
    service_request: str | None
    service_request_confirmed: bool = False
    date: str | None             # YYYY-MM-DD
    time_window: str | None      # HH:MM-HH:MM
    lead_source: str | None
    notes: list[str]             # short context memory
    appointment_id: str | None
    done: bool = False
```

### 2.3 Helpers
- `missing()` → ordered list of fields still empty  
- `to_payload()` → booking payload for tools

---

## 3) Validation & Normalization

| Aspect     | Function                    | Behavior (key points)                                              |
|------------|-----------------------------|--------------------------------------------------------------------|
| Phone      | `normalize_phone(s)`        | Keep digits only; valid if 10–11 digits                            |
| Email      | `looks_like_email(s)`       | Light regex `local@domain.tld`                                     |
| Address    | `looks_like_address(s)`     | Requires street number + word (e.g., `33 Main St`)                 |
| Date       | `to_iso_date(s)`            | Accepts `YYYY-MM-DD`, `MM/DD/YYYY`, `DD/MM/YYYY`, `tomorrow`, `next Tuesday` |
| Time       | `to_window_or_none(s)`      | Accepts `HH:MM-HH:MM`, `HH:MM` (expanded by +1h), `11 am`/`3 pm`   |
| Heuristics | `is_probably_name(s)`       | 2–4 name tokens, no digits/@                                       |
| Heuristics | `looks_like_service_request`| Contains repair/estimate keywords, >= 3 tokens                      |

> Rationale: keep validators **strict enough** to prevent garbage, but **forgiving** for natural input.

---

## 4) Dialog Management

### 4.1 Rule-based Agent (`core/agent.py`)
**Flow:**
1. Try to **pre-capture** `service_request` from free-form → **must confirm** (`yes/no`).  
2. Ask **one missing field** at a time (`missing()[0]`).  
3. *(Optional)* After address → `check_coverage`; if not covered, offer referral.  
4. With date + time_window → `check_availability`; if busy, propose alternatives.  
5. **Recap** all fields. If user says `yes` → finalize (create apt + confirmation).

**NLG polish (optional):**  
All replies can pass through `llm.polish_reply` to keep tone concise/polite (facts unchanged). Safe fallback if `USE_LLM=0`.

### 4.2 LLM Agent (`core/llm_agent.py`)
- **Parsing**: `chat_json(system=prompt.txt, user=extract_prompt)`  
  → merge into state **only if** validators pass.  
- **Prompting**: uses `chat_text(system=prompt.txt, user=draft)` to rewrite assistant replies.  
- **Guards**: Availability/coverage/recap/finalize same as rule-based → deterministic checkpoints.

---

## 5) Tool Contracts (Mock)

| Tool                 | Input                            | Output / Behavior                                                             |
|----------------------|----------------------------------|-------------------------------------------------------------------------------|
| `check_coverage`     | `address: str`                   | `{"covered": bool}` — simple heuristic (everything covered unless “nocover”)  |
| `check_availability` | `date: str`, `time_window: str`  | `{"available": bool, "alternatives": [...]}` — uses `config.busy_by_date`    |
| `create_appointment` | `payload: dict`                  | Returns `APT-<random>`                                                        |
| `send_confirmation`  | `channel: "email"`, `payload`    | No-op mock (replace with provider later)                                      |

**Why mocks?**  
They let us prove the agentic orchestration without external dependencies. Replace with real APIs later.

---

## 6) Configuration Matrix (`core/config.py`)

| Key                                   | Type  | Default | Meaning |
|---------------------------------------|-------|---------|---------|
| `default_window_hours`                | int   | `1`     | Single time expands to a 1-hour window |
| `recap_before_finalize`               | bool  | `True`  | Always recap before booking |
| `send_email_confirmation_after_booking`| bool | `True`  | Trigger (mock) confirmation |
| `technician_may_call_ahead`           | bool  | `True`  | Adds a courtesy sentence in the final reply |
| `require_coverage_check_before_slots` | bool  | `False` | If `True`, check coverage right after address |
| `busy_by_date`                        | dict  | demo    | Mark specific time windows as busy |

> Adjust these to fit a client’s policy or test scenarios.

---

## 7) Prompt Incorporation (`core/prompt.txt`)

- Defines **tone**, **do/don’t**, **required fields**, **recap/finalize** rules.  
- **Rule-based**: prompt acts as *spec* that the code implements.  
- **LLM**: prompt is the **system prompt** for both:  
  - NLG-only rewrite (`polish_reply`)  
  - JSON slot extraction (`chat_json`) with **strict parsing fallback**.

**Environment variables:**
- `USE_LLM` (`0`/`1`) — turn LLM calls on/off  
- `LLM_MODEL` — e.g., `mistral:instruct`, `phi3:mini`, `llama3.1:8b-instruct`  
- `OLLAMA_URL` — default `http://localhost:11434/api/generate`  
- `PROMPT_PATH` — default `core/prompt.txt`

---

## 8) Context Handling

- **Short memory** in `state.notes` (last few turns) is passed to NLG to keep responses contextually polite and concise.  
- **Business state** is explicit (fields + flags), ensuring deterministic outcomes regardless of LLM verbosity.

---

## 9) Logging & CSV

- Each CLI run writes `logs/session-YYYYMMDD-HHMMSS.csv` with:  
  ```
  Speaker,Dialogue
  Assistant,"Thanks for calling ..."
  Caller,"I need an estimate ..."
  ...
  ```
- Include 2–3 curated CSVs for evaluation: **happy**, **busy_slot**, **corrections**.

---

## 10) Edge Cases & Error Handling

- **Invalid phone** → ask again with format hint.  
- **Invalid email** → ask again with example `name@example.com`.  
- **Address missing street number** → ask again with example `33 Main St, Springfield`.  
- **Unavailable slot** → propose two alternatives; require the user to pick one.  
- **Recap ‘no’** → ask which field to change (list `REQUIRED_FIELDS`).  
- **LLM failure / off** → graceful fallbacks (keep draft text, skip JSON extraction).

---

## 11) Testing Strategy

### Unit tests (suggested)
- `validators.py`: phones/emails/addresses + date/time parsers.  
- `tools.check_availability`: overlapping windows and alternatives.  
- Agent transitions: service request confirm → recap → finalize.

### Integration tests
- **Happy path** (all good).  
- **Busy slot** (alternative choice).  
- **Corrections** (invalid → fixed).  
- **LLM one-shot** (all info in one message) — ensure recap matches.
---


## 12) Design Rationale (ADR-lite)

- **Rule-based core** for reliability & grading determinism.  
- **LLM as NLG-only + semantic parse** (opt-in) for natural UX without sacrificing correctness.  
- **Validators as guards** to prevent hallucinations from affecting critical fields.  
- **Mock tools** to prove orchestration and make it easy to swap real services later.  
- **Config-driven** availability/coverage to model realistic constraints.

---


