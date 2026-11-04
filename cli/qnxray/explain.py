"""AI root-cause explainer for QNX crashes and priority inversions.

Online mode (OpenAI-compatible chat completions):
  key   : QNXRAY_LLM_KEY, else OPENAI_API_KEY   (environment only - never written to reports/config/logs)
  url   : QNXRAY_LLM_URL   (default https://api.openai.com/v1/chat/completions)
  model : QNXRAY_LLM_MODEL (default gpt-5.4-mini)
  off   : QNXRAY_LLM=off forces the offline explainer.
The model receives *structured evidence* (signal, backtrace, source lines around the fault, thread
states; for inversions the waiter -> blocker -> preemptor chain and a tracelogger timeline) and must
return JSON {summary, root_cause, evidence[], qnx_fix, patch, confidence}. Output is validated; on any
error (no key, network, bad JSON) the rule-based offline explanation is returned so CI never breaks.
"""
import json, os, re, urllib.request

DEFAULT_MODEL = "gpt-5.4-mini"
RULES = {"SIGSEGV": "Invalid memory access. On QNX, SEGV_MAPERR at 0x0 usually means a NULL pointer dereference.",
         "SIGBUS": "Misaligned or unmapped physical access; common with mmap_device_memory() misuse in drivers.",
         "SIGABRT": "abort() called, often a failed assert().",
         "SIGFPE": "Arithmetic fault, e.g. integer divide by zero.",
         "SIGILL": "Illegal instruction: corrupted code pointer or wrong -V target variant."}
FIELDS = {"summary": str, "root_cause": str, "evidence": list, "qnx_fix": str, "patch": str, "confidence": str}

SYSTEM = ("You are a senior QNX Neutrino 8.0 real-time systems engineer. You receive structured evidence captured "
          "from a live QNX 8.0 target by the QNXray tool. Diagnose ONLY from the evidence. Use QNX specifics where "
          "relevant: message passing (MsgSend/MsgReceive/MsgReply, REPLY/SEND/RECEIVE-blocked states), channel flags "
          "such as _NTO_CHF_FIXED_PRIORITY (disables client-driven priority inheritance), PTHREAD_PRIO_INHERIT / "
          "PTHREAD_PRIO_PROTECT (priority ceiling) mutexes, SCHED_FIFO/RR priorities, dumper cores, SEGV_MAPERR. "
          "Reply with a single JSON object with exactly these keys: summary (one sentence), root_cause (2-3 sentences), "
          "evidence (array of 2-5 short strings each citing a concrete value from the input), qnx_fix (the specific QNX "
          "fix), patch (a minimal unified diff or code snippet against the given source; empty string if no source), "
          "confidence (high|medium|low).")

_SECRET = re.compile(r"(?i)(sk-[A-Za-z0-9_\-]{10,}|bearer\s+\S+|(?:api[_-]?key|token|password|secret)\s*[=:]\s*\S+)")

def redact(obj):
    """Strip anything secret-looking from evidence before it leaves the host."""
    if isinstance(obj, str): return _SECRET.sub("[REDACTED]", obj)
    if isinstance(obj, list): return [redact(x) for x in obj]
    if isinstance(obj, dict): return {k: redact(v) for k, v in obj.items() if not re.search(r"(?i)key|token|secret|password", k)}
    return obj

def source_context(backtrace, radius=6, roots=(".",)):
    """Find `at file:line` in the backtrace and return the surrounding source lines (host copy)."""
    for fr in backtrace or []:
        m = re.search(r" at (\S+?):(\d+)", fr)
        if not m: continue
        path, line = m.group(1), int(m.group(2))
        cands = [path] + [os.path.join(r, path.lstrip("/")) for r in roots] + \
                [os.path.join(r, *path.split("/")[-3:]) for r in roots]
        for c in cands:
            if os.path.isfile(c):
                src = open(c, errors="replace").read().splitlines()
                lo, hi = max(1, line - radius), min(len(src), line + radius)
                return {"file": path, "fault_line": line,
                        "lines": [f"{n}{'>' if n == line else ' '} {src[n-1]}" for n in range(lo, hi + 1)]}
    return None

def crash_evidence(rep):
    ev = {"kind": "crash", "os": "QNX 8.0", "binary": rep.get("binary"), "signal": rep.get("signal"),
          "signal_desc": rep.get("signal_desc"), "pc": rep.get("pc"), "backtrace": rep.get("backtrace"),
          "exit_code": rep.get("exit_code"), "stderr": (rep.get("stderr") or "")[-800:],
          "core": rep.get("core")}
    root = os.environ.get("QNXRAY_SRC_ROOT", os.path.join(os.path.dirname(__file__), "..", ".."))
    src = source_context(rep.get("backtrace"), roots=(root, "."))
    if src: ev["source"] = src
    return ev

def inversion_evidence(inv, snapshot=None, timeline=None):
    ev = {"kind": "priority_inversion", "os": "QNX 8.0",
          "chain": {"waiter": inv.get("waiter"), "waiter_prio": inv.get("prio"), "waiter_state": inv.get("state"),
                    "blocker": f"{inv.get('owner')}[{inv.get('owner_pid')}]", "blocker_max_prio": inv.get("owner_max_prio"),
                    "blocker_states": inv.get("owner_states"), "preempted_by": inv.get("preempted_by")},
          "severity": inv.get("severity")}
    if snapshot:   # thread table of every process in the chain
        pids = {inv.get("owner_pid")} | {int(m) for s in [inv.get("waiter", "")] + (inv.get("preempted_by") or [])
                                         for m in re.findall(r"\[(\d+)\]", s)}
        ev["threads"] = [{"pid": p["pid"], "name": p["name"], "tid": t["tid"], "prio": f"{t['priority']}{t['policy']}",
                          "state": t["state"], "blocked_on": t.get("blocked_on"), "cpu": t.get("cpu")}
                         for p in snapshot.get("processes", []) if p["pid"] in pids for t in p["threads"]]
    if timeline:
        th = timeline.get("threads", {})
        items = th.items() if isinstance(th, dict) else enumerate(th)
        ev["timeline"] = {"window_s": timeline.get("duration_s"),
                          "threads": {str(k): v for k, v in list(items)[:8]}}
    src = inv.get("source_file")
    if src and os.path.isfile(src):
        ev["source"] = {"file": src, "lines": open(src, errors="replace").read().splitlines()[:80]}
    return ev

def offline(report: dict) -> str:
    if "waiter" in report:
        return (f"[offline] Priority inversion: {report['waiter']} (prio {report['prio']}, {report['state']}) waits on "
                f"{report['owner']}[{report.get('owner_pid')}] running at prio {report['owner_max_prio']}"
                + (f", which is preempted by {', '.join(report['preempted_by'])}" if report.get("preempted_by") else "")
                + ". Fix: let the server inherit client priority (don't use _NTO_CHF_FIXED_PRIORITY), or use a "
                  "PTHREAD_PRIO_INHERIT mutex.")
    return f"[offline] {RULES.get(report.get('signal'), 'Unknown signal')} Top frame: {(report.get('backtrace') or ['?'])[0]}"

def validate(obj):
    if not isinstance(obj, dict): raise ValueError("not an object")
    out = {}
    for k, typ in FIELDS.items():
        v = obj.get(k, "" if typ is str else [])
        if not isinstance(v, typ): raise ValueError(f"bad field {k}")
        out[k] = [str(x)[:400] for x in v][:6] if typ is list else v[:4000]
    if not out["summary"] or not out["root_cause"] or not out["qnx_fix"]: raise ValueError("missing required text")
    if out["confidence"] not in ("high", "medium", "low"): out["confidence"] = "medium"
    return out

def _key():
    if os.environ.get("QNXRAY_LLM", "").lower() == "off": return None
    return os.environ.get("QNXRAY_LLM_KEY") or os.environ.get("OPENAI_API_KEY")

def call_llm(evidence, key, transport=None, system=SYSTEM, check=None):
    """transport(url, headers, body)->dict lets tests mock the HTTP call."""
    url = os.environ.get("QNXRAY_LLM_URL", "https://api.openai.com/v1/chat/completions")
    model = os.environ.get("QNXRAY_LLM_MODEL", DEFAULT_MODEL)
    body = {"model": model, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": "Evidence:\n" + json.dumps(redact(evidence), indent=1)}]}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if transport: resp = transport(url, headers, body)
    else:
        req = urllib.request.Request(url, json.dumps(body).encode(), headers)
        with urllib.request.urlopen(req, timeout=float(os.environ.get("QNXRAY_LLM_TIMEOUT", "90"))) as r:
            resp = json.load(r)
    return model, (check or validate)(json.loads(resp["choices"][0]["message"]["content"]))

def analyze(report: dict, snapshot=None, timeline=None, transport=None) -> dict:
    """Structured explanation: {mode: ai|offline, text, ...fields}. Never raises."""
    ev = inversion_evidence(report, snapshot, timeline) if "waiter" in report else crash_evidence(report)
    key = _key()
    if key:
        try:
            model, ai = call_llm(ev, key, transport)
            return dict(ai, mode="ai", model=model, text=f"[ai:{model}] {ai['summary']} Fix: {ai['qnx_fix']}")
        except Exception as e:   # network/auth/validation errors must not break CI
            off = offline(report)
            return {"mode": "offline", "text": off, "ai_error": type(e).__name__}
    return {"mode": "offline", "text": offline(report)}

def explain(report: dict, **kw) -> str:
    return analyze(report, **kw)["text"]

def format_text(a: dict) -> str:
    if a.get("mode") != "ai": return a["text"] + (f" (AI explainer unavailable: {a['ai_error']})" if a.get("ai_error") else "")
    out = [f"AI root cause ({a['model']}, confidence {a['confidence']}):", "  " + a["summary"], "", "Why:", "  " + a["root_cause"],
           "", "Evidence:"] + [f"  - {e}" for e in a["evidence"]] + ["", "QNX fix:", "  " + a["qnx_fix"]]
    if a.get("patch"): out += ["", "Patch:"] + ["  " + l for l in a["patch"].splitlines()]
    return "\n".join(out)

FIX_SYSTEM = ("You are a senior QNX Neutrino 8.0 engineer. Given evidence of a priority inversion captured live and the "
              "full C source of the program, propose the smallest QNX-correct fix (e.g. let the server channel inherit "
              "client priority by not using _NTO_CHF_FIXED_PRIORITY, PTHREAD_PRIO_INHERIT mutex, or a priority ceiling). "
              "Do NOT change command-line behaviour, timings or the workload. The patched program must be free of the inversion "
              "in every mode/flag combination (e.g. never leave _NTO_CHF_FIXED_PRIORITY reachable on the server channel). Reply with one JSON object: "
              "{\"qnx_fix\": str, \"rationale\": str, \"edits\": [{\"find\": exact substring of the source (must occur once), "
              "\"replace\": str}]} with 1-3 edits.")

def _check_fix(obj):
    if not isinstance(obj, dict) or not isinstance(obj.get("edits"), list) or not obj["edits"]: raise ValueError("no edits")
    for e in obj["edits"]:
        if not isinstance(e, dict) or not isinstance(e.get("find"), str) or not isinstance(e.get("replace"), str) or not e["find"]:
            raise ValueError("bad edit")
    return {"qnx_fix": str(obj.get("qnx_fix", ""))[:800], "rationale": str(obj.get("rationale", ""))[:1500], "edits": obj["edits"][:3]}

def lint(source):
    """QNX rule check on the patched source: a server channel with _NTO_CHF_FIXED_PRIORITY reachable."""
    for m in re.finditer(r"ChannelCreate(?:_r)?\(([^;]*?)\)\s*;", source):
        if "_NTO_CHF_FIXED_PRIORITY" in m.group(1): return m.group(0)
    return ""

def offline_fix(source):
    """Rule: the classic QNX message-passing inversion is a channel created with _NTO_CHF_FIXED_PRIORITY."""
    m = re.search(r"ChannelCreate\(([^;]*?)\)", source)
    if not m or "_NTO_CHF_FIXED_PRIORITY" not in m.group(1): raise ValueError("no offline rule applies")
    return {"qnx_fix": "Create the server channel without _NTO_CHF_FIXED_PRIORITY so the server inherits the "
                       "priority of the client it is serving (QNX default priority inheritance).",
            "rationale": "[offline rule]", "edits": [{"find": m.group(0), "replace": "ChannelCreate(0)"}]}

def propose_fix(evidence, source, transport=None):
    key = _key()
    if key:
        try:
            ev = dict(evidence, source={"file": evidence.get("source", {}).get("file", "main.c"), "text": source})
            model, fx = call_llm(ev, key, transport, system=FIX_SYSTEM, check=_check_fix)
            new = source
            for e in fx["edits"]:
                if new.count(e["find"]) != 1: raise ValueError("edit does not match source exactly once")
                new = new.replace(e["find"], e["replace"], 1)
            if lint(new): raise ValueError("patched source still inverts: " + lint(new))
            return dict(fx, mode="ai", model=model)
        except Exception as e:
            return dict(offline_fix(source), mode="offline", ai_error=type(e).__name__)
    return dict(offline_fix(source), mode="offline")
