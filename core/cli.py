# core/cli.py
import os
from datetime import datetime
from pathlib import Path
import csv, sys

from core.state import ConversationState
from core.agent import Agent
from core.llm_agent import LLMAgent  

# Auto-record 
LOG_DIR = Path(os.getenv("LOG_DIR", "logs")); LOG_DIR.mkdir(exist_ok=True)
def _open_writer():
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    p = LOG_DIR / f"session-{ts}.csv"
    f = p.open("w", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=["Speaker","Dialogue"]); w.writeheader()
    print(f"[Recorder] {p.as_posix()}")
    return f, w

def main():
    mode = "rule"
    if "--mode" in sys.argv:
        try: mode = sys.argv[sys.argv.index("--mode")+1].lower()
        except: pass
    bot = Agent() if mode != "llm" else LLMAgent()

    st = ConversationState()
    f, w = _open_writer()

    def log(s, t):
        print(f"{s}: {t}")
        w.writerow({"Speaker": s, "Dialogue": t})
        if hasattr(st, "notes"):
            st.notes.append(f"{s}: {t}")

    log("Assistant", "Thanks for calling Jacob's Plumbing. How can I help today?")

    try:
        while not st.done:
            user = input("Caller: ").strip()
            log("Caller", user)
            if user.lower() in {"yes","y"} and not st.missing():
                log("Assistant", bot.finalize(st, True))
                break
            if user.lower() in {"no","n"} and not st.missing():
                log("Assistant", bot.finalize(st, False))
                continue
            reply = bot.update(st, user)
            log("Assistant", reply)
    finally:
        f.close()

if __name__ == "__main__":
    main()
