"""Scheduling heuristics over snapshots (pure functions, unit tested)."""
from .model import Snapshot

BLOCKING = ("MUTEX", "SEND", "REPLY")

def priority_inversions(s: Snapshot):
    """Flag high-priority threads blocked (MUTEX/SEND/REPLY) on a process whose threads all
    run at a lower priority (i.e. no priority inheritance happened). If some third thread with
    a priority between the two is RUNNING/READY, it is reported as `preempted_by` - the
    classic unbounded inversion. Heuristic; confirm with the tracelogger timeline."""
    by_pid = {p.pid: p for p in s.processes}
    out = []
    for p in s.processes:
        for t in p.threads:
            if t.state not in BLOCKING or not t.blocked_on or not str(t.blocked_on).isdigit():
                continue
            owner = by_pid.get(int(t.blocked_on))
            if not owner or not owner.threads or owner.pid == p.pid:
                continue
            omax = max(x.priority for x in owner.threads)
            if omax >= t.priority:
                continue
            mids = [f"{q.name}[{q.pid}]/{x.tid}@{x.priority}" for q in s.processes if q.pid not in (p.pid, owner.pid)
                    for x in q.threads if omax < x.priority < t.priority and x.state in ("RUNNING", "READY")]
            out.append({"waiter": f"{p.name}[{p.pid}]/{t.tid}", "prio": t.priority, "state": t.state,
                        "owner": owner.name, "owner_pid": owner.pid, "owner_max_prio": omax,
                        "owner_states": sorted({x.state for x in owner.threads}),
                        "preempted_by": mids,
                        "severity": "high" if mids else "medium"})
    return out
