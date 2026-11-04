"""AI crash explainer. Builds a QNX-aware prompt; LLM call is pluggable via
QNXRAY_LLM_URL/QNXRAY_LLM_KEY (OpenAI-compatible). Without a key it returns
a rule-based explanation so the demo works offline."""
import json, os, urllib.request

RULES = {"SIGSEGV": "Invalid memory access. On QNX, SEGV_MAPERR at 0x0 usually means a NULL pointer dereference.",
         "SIGBUS": "Misaligned or unmapped physical access; common with mmap_device_memory() misuse in drivers.",
         "SIGABRT": "abort() called, often a failed assert()."}

def explain(report: dict) -> str:
    url, key = os.environ.get("QNXRAY_LLM_URL"), os.environ.get("QNXRAY_LLM_KEY")
    if not (url and key):
        return f"[offline] {RULES.get(report.get('signal'), 'Unknown signal')} Top frame: {report.get('backtrace', ['?'])[0]}"
    prompt = ("You are a QNX 8.0 expert. Explain this crash, the likely root cause, and a fix. "
              "Consider QNX specifics (message passing, priority inheritance, abilities/procmgr_ability).\n" + json.dumps(report))
    body = json.dumps({"model": os.environ.get("QNXRAY_LLM_MODEL", "default"),
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(url, body, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["choices"][0]["message"]["content"]
