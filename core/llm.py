# core/llm.py
"""
LLM helpers for:
- Loading system prompt from prompt.txt
- Calling an open-source model via Ollama HTTP API
- NLG-only "polish_reply" or general chat_text / chat_json utilities

Env vars:
  USE_LLM=1 # turn on actual LLM calls; default 0 (fallback local)
  LLM_MODEL=mistral:instruct  # or phi3:mini, llama3.1:8b-instruct, etc.
  OLLAMA_URL=http://localhost:11434/api/generate
  PROMPT_PATH=core/prompt.txt
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import List, Optional
import requests

USE_LLM = os.getenv("USE_LLM", "0") == "1"
MODEL = os.getenv("LLM_MODEL", "mistral:instruct")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
PROMPT_PATH = os.getenv("PROMPT_PATH", "core/prompt.txt")


def load_prompt() -> str:
    """Load the system prompt from PROMPT_PATH (used for both NLG and parsing)."""
    try:
        return Path(PROMPT_PATH).read_text(encoding="utf-8")
    except Exception:
        # Fallback short prompt if missing
        return "You are a concise, professional plumbing call assistant."


def _ollama_generate(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """
    Call Ollama /api/generate with a single-turn prompt.
    Wrap system prompt in <<SYS>> ... <<SYS>> to simulate system role.
    """
    payload = {
        "model": MODEL,
        "prompt": f"<<SYS>>{system_prompt}<<SYS>>\n{user_prompt}",
        "temperature": temperature,
        "stream": False,
    }
    r = requests.post(OLLAMA_URL, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return (data.get("response") or "").strip()


def polish_reply(raw_text: str, context: Optional[List[str]] = None) -> str:
    """
    NLG-only: rewrite assistant reply per system prompt and (optionally) short context.
    If USE_LLM=0, fallback = keep the text but ensure terminal punctuation.
    """
    t = (raw_text or "").strip()
    if not USE_LLM:
        if t and t[-1] not in ".?!":
            t += "."
        return t

    system_prompt = load_prompt()
    ctx = "\n".join(context or [])
    user_prompt = (
        "Rewrite the assistant reply for a courteous call-center agent. "
        "Keep all facts and data unchanged. Be concise, polite, one sentence."
        + (f"\nRecent context:\n{ctx}\n" if ctx else "")
        + f"\nAssistant reply draft:\n{t}\n"
    )
    try:
        out = _ollama_generate(system_prompt, user_prompt, temperature=0.2)
        return out or t
    except Exception:
        if t and t[-1] not in ".?!":
            t += "."
        return t


def chat_text(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """
    Generic text generation. If USE_LLM=0, return user_prompt (noop) to keep flow safe.
    """
    if not USE_LLM:
        return user_prompt.strip()
    try:
        return _ollama_generate(system_prompt, user_prompt, temperature=temperature)
    except Exception:
        return user_prompt.strip()


def chat_json(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> dict:
    """
    Ask the model to return JSON. If parsing fails (or USE_LLM=0), return {}.
    """
    if not USE_LLM:
        return {}
    ask = user_prompt + "\n\nReturn ONLY valid JSON (no backticks, no prose)."
    text = chat_text(system_prompt, ask, temperature=temperature)
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        # Try to extract a JSON substring
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start:end + 1])
        except Exception:
            return {}
    return {}
