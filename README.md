# Jacob’s Plumbing — Agentic AI Demo

A simple, reliable **agentic assistant** for plumbing calls that collects required fields, checks coverage/availability (mock), recaps, and books an appointment.

- **Two runtimes**
  - **Rule-based agent** (deterministic; zero external dependencies)
  - **LLM agent** (semantic parsing + NLG using your `prompt.txt`, powered by open-source models via **Ollama**)
- **Meets spec**
  - Incorporates the developed **prompt** (`core/prompt.txt`)
  - Proper **context handling** (stateful, recap, explicit confirmation)
  - **Tool calls (mock)**: coverage, availability, booking, confirmation

---

## 1) Requirements

- **Python** ≥ 3.9  
- (LLM mode) **Ollama** installed & running (`ollama serve`)  
  Suggested models: `mistral:instruct`, `phi3:mini`, `llama3.1:8b-instruct`  
- Python package: `requests` (LLM mode only)

---

## 2) Project Structure

```
core/
  __init__.py
  config.py
  state.py
  validators.py
  tools.py
  agent.py           # Rule-based agent
  llm.py             # LLM helpers (prompt loading + Ollama HTTP)
  llm_agent.py       # LLM-driven agent (semantic parsing + NLG)
  cli.py             # Command-line runner (auto-logs to CSV)
  prompt.txt         # Assistant policy/tone/flow (incorporated by both modes)
docs/
  flow.png           # (optional) call flow diagram
  screenshot_run.png # (optional) demo screenshot
logs/
  session-YYYYMMDD-HHMMSS.csv  # auto-generated conversation logs
```

**Sample CSV scripts** (optional to include for reviewers, placed in `logs`):
- `rule_based/session-20251018-busy_slot.csv`
- `rule_based/session-20251018-correction.csv`
- `rule_based/session-20251018-happy.csv`
- `llm/session-20251019-llm.csv`
---

## 3) Setup

Create and activate a virtual environment:

**macOS/Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install requirements (LLM mode only):
```bash
pip install requests
```

---

## 4) Running

### A) Rule-based (deterministic)
```bash
python -m core.cli --mode rule
```
- The assistant greets the caller.
- Type caller messages line by line.
- When you see the **recap**, reply `yes` to confirm and complete booking.
- Each run is auto-recorded to `logs/session-*.csv`.

### B) LLM agent (open-source via Ollama)
1) Start Ollama & pull a model:
```bash
ollama serve
ollama pull mistral:instruct   # or: ollama pull phi3:mini
```

2) Enable LLM mode & run:
```bash
export USE_LLM=1
export LLM_MODEL="mistral:instruct"
python -m core.cli --mode llm
```

> The LLM agent uses the same validators and mock tools—LLM only helps **parse free-form inputs** and **polish responses** per the prompt.

---

## 5) How the Prompt Is Used

- **`core/prompt.txt`** contains tone, do/don’t, data requirements, flow rules.
- **Rule-based agent**: Treats the prompt as the **policy spec** (code enforces it).
- **LLM agent**:
  - Loads `prompt.txt` as the **system prompt**.
  - Uses it to **rewrite** assistant replies (NLG-only, facts preserved).
  - Optionally **extracts slots** (JSON) from caller free-form messages.

Environment variables:
- `PROMPT_PATH` (defaults to `core/prompt.txt`)
- `USE_LLM` (`0`/`1`), `LLM_MODEL` (e.g., `mistral:instruct`), `OLLAMA_URL` (default `http://localhost:11434/api/generate`)

---

## 6) Context Handling

- **`ConversationState`** stores all required fields:
  - `full_name`, `service_address`, `phone_number`, `email`, `service_request`, `date`, `time_window`
- **`service_request_confirmed: bool`** ensures the agent explicitly confirms the issue (`yes/no`) before finalize.
- Short **context memory** (`state.notes`) is passed into NLG to keep tone & coherence.

---

## 7) Tool Calls (Mock)

- `check_coverage(address)` → `{"covered": bool}`
- `check_availability(date, time_window, cfg)` → `{"available": bool, "alternatives": [...] }`
- `create_appointment(payload)` → returns booking ID `APT-...`
- `send_confirmation("email", payload)` → mocked email send

> Replace with real integrations any time (CRM, email, scheduling API).

---

## 8) Troubleshooting

- **`ModuleNotFoundError: core...`**  
  Run from the project root (folder that contains `core/`).

- **No CSV output**  
  Ensure the included `cli.py` is the auto-recording version (it prints `[Recorder] logs/session-...csv` at startup).

- **Ollama connection error**  
  Run `ollama serve`. Pull a model. Verify `OLLAMA_URL` (defaults to `http://localhost:11434/api/generate`).

- **LLM responses too wordy**  
  Lower temperature in `core/llm.py` (e.g., `0.1`) or tighten prompt wording.

- **PII**  
  Scripts use synthetic PII. Mask appropriately if sharing logs.

---

**That’s it!**  
- Rule-based for deterministic grading.  
- LLM agent to demonstrate “incorporate prompt” + agentic behavior with open-source models.  
- Auto-generated CSV transcripts for review.

## Technical Docs
For a deeper dive into architecture, state machine, validators, mock tool contracts,
LLM integration, configuration matrix, edge cases, testing, and deployment notes,
see **[docs/TECHNICAL.md](docs/TECHNICAL.md)**.