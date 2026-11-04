"""AI crash/inversion explainer.

Online mode: set QNXRAY_LLM_KEY (and optionally QNXRAY_LLM_URL, default OpenAI-compatible
https://api.openai.com/v1/chat/completions, and QNXRAY_LLM_MODEL). The key is read from the
environment only - never stored in config or reports. Without a key, or if the call fails,
a rule-based offline explanation is returned so demos and CI work offline.
"""
import json, os, urllib.request

RULES = {"SIGSEGV": "Invalid memory access. On QNX, SEGV_MAPERR at 0x0 usually means a NULL pointer dereference.",
         "SIGBUS": "Misaligned or unmapped physical access; common with mmap_device_memory() misuse in drivers.",
         "SIGABRT": "abort() called, often a failed assert().",
         "SIGFPE": "Arithmetic fault, e.g. integer divide by zero.",
         "SIGILL": "Illegal instruction: corrupted code pointer or wrong -V target variant."}

def offline(report: dict) -> str:
    if "waiter" in report:
        return (f"[offline] Priority inversion: {report['waiter']} (prio {report['prio']}, {report['state']}) waits on "
                f"{report['owner']}[{report.get('owner_pid')}] running at prio {report['owner_max_prio']}"
                + (f", which is preempted by {', '.join(report['preempted_by'])}" if report.get("preempted_by") else "")
                + ". Fix: let the server inherit client priority (don't use _NTO_CHF_FIXED_PRIORITY), or use a "
                  "PTHREAD_PRIO_INHERIT mutex.")
    return f"[offline] {RULES.get(report.get('signal'), 'Unknown signal')} Top frame: {report.get('backtrace', ['?'])[0]}"

def explain(report: dict) -> str:
    key = os.environ.get("QNXRAY_LLM_KEY")
    if not key:
        return offline(report)
    url = os.environ.get("QNXRAY_LLM_URL", "https://api.openai.com/v1/chat/completions")
    prompt = ("You are a QNX 8.0 expert. Explain this issue, the likely root cause, and a concrete fix in under "
              "150 words. Consider QNX specifics (message passing, priority inheritance, "
              "_NTO_CHF_FIXED_PRIORITY, abilities/procmgr_ability, dumper cores).\n" + json.dumps(report))
    body = json.dumps({"model": os.environ.get("QNXRAY_LLM_MODEL", "gpt-4o-mini"),
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(url, body, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return "[ai] " + json.load(r)["choices"][0]["message"]["content"]
    except Exception as e:  # network/auth errors must not break CI
        return offline(report) + f" (AI explainer unavailable: {type(e).__name__})"
