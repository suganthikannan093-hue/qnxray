"""tracelogger (.kev) -> scheduling timeline.

Capture: `tracelogger -s N -f file.kev` on the target (root). Decode: the SDP host tool
`traceprinter -f file.kev` (from $QNX_HOST); this module parses traceprinter's text output
into per-CPU run segments and per-thread state-time totals. Pure functions, unit tested.
"""
import re
from collections import defaultdict

EV = re.compile(r"^t:0x([0-9a-f]+) CPU:(\d+) (\w+)\s+:(\w+)\s*(.*)$")
KV = re.compile(r"(\w+):(\S+)")

def parse_traceprinter(text):
    """Return (header, events, names). events: dicts with t (cycles), cpu, cls, ev, pid, tid."""
    header, events, names = {}, [], {}
    pending = None
    for line in text.splitlines():
        if "::" in line and not line.startswith("t:"):
            k, _, v = line.partition("::"); header[k.strip()] = v.strip(); continue
        m = EV.match(line)
        if m:
            kv = dict(KV.findall(m.group(5)))
            e = {"t": int(m.group(1), 16), "cpu": int(m.group(2)), "cls": m.group(3), "ev": m.group(4)}
            if "pid" in kv and kv["pid"].isdigit(): e["pid"] = int(kv["pid"])
            if "tid" in kv and kv["tid"].isdigit(): e["tid"] = int(kv["tid"])
            events.append(e)
            pending = {} if e["ev"] in ("PROCCREATE_NAME", "PROCTHREAD_NAME") else None
            continue
        if pending is not None:          # continuation lines: "   pid:123" / "   name:tmp/foo"
            kv = dict(KV.findall(line))
            pending.update(kv)
            if "pid" in pending and "name" in pending:
                names.setdefault(int(pending["pid"]), pending["name"]); pending = None
    return header, events, names

def build_timeline(header, events, names, pid_filter=None):
    cps = int(header.get("TRACE_CYCLES_PER_SEC", "1") or 1)
    th = [e for e in events if e["cls"] == "THREAD" and e["ev"].startswith("TH") and "pid" in e]
    if not th:
        return {"duration_s": 0, "cpus": {}, "threads": {}}
    t0, t1 = th[0]["t"], max(e["t"] for e in th)
    sec = lambda c: (c - t0) / cps
    cur_state, cpu_run = {}, {}
    states = defaultdict(lambda: defaultdict(float))
    segs = defaultdict(list)
    def close_run(cpu, t):
        if cpu in cpu_run:
            k, start = cpu_run.pop(cpu)
            segs[cpu].append({"start": round(sec(start), 6), "end": round(sec(t), 6), "thread": k})
    for e in th:
        k = f"{e['pid']}/{e.get('tid', 0)}"
        st = e["ev"][2:]                         # THRUNNING -> RUNNING
        if k in cur_state:
            pst, pt = cur_state[k]; states[k][pst] += (e["t"] - pt) / cps
        cur_state[k] = (st, e["t"])
        if st == "RUNNING":
            close_run(e["cpu"], e["t"]); cpu_run[e["cpu"]] = (k, e["t"])
        else:
            for c, (rk, _) in list(cpu_run.items()):
                if rk == k: close_run(c, e["t"])
    for k, (st, t) in cur_state.items():
        states[k][st] += (t1 - t) / cps
    for c in list(cpu_run): close_run(c, t1)
    keep = lambda k: pid_filter is None or int(k.split("/")[0]) in pid_filter
    threads = {k: {"name": names.get(int(k.split("/")[0]), "?"),
                   "states_s": {s: round(v, 6) for s, v in sorted(d.items(), key=lambda x: -x[1])}}
               for k, d in states.items() if keep(k)}
    return {"duration_s": round(sec(t1), 6), "cycles_per_sec": cps,
            "cpus": {str(c): [s for s in v if keep(s["thread"])] for c, v in sorted(segs.items())},
            "threads": threads}

def render_text(tl, width=60, match=None):
    """ASCII lanes: one row per thread, '#' running, '.' ready, '-' blocked."""
    d = tl["duration_s"] or 1
    rows = []
    for k, info in tl["threads"].items():
        if match and match not in info["name"]: continue
        lane = [" "] * width
        for c, ss in tl["cpus"].items():
            for s in ss:
                if s["thread"] == k:
                    for i in range(int(s["start"] / d * width), max(int(s["end"] / d * width), int(s["start"] / d * width) + 1)):
                        if i < width: lane[i] = "#"
        top = ", ".join(f"{s}={v:.3f}s" for s, v in list(info["states_s"].items())[:3])
        rows.append(f"{k:>14} {info['name'][-22:]:<22} |{''.join(lane)}| {top}")
    return f"timeline {d:.3f}s ('#' = on CPU)\n" + "\n".join(rows)
