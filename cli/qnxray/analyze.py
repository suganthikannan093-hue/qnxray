"""Scheduling heuristics over snapshots (pure functions, unit tested)."""
from .model import Snapshot

def priority_inversions(s: Snapshot):
    """Flag high-priority threads blocked (MUTEX/SEND/REPLY) on a process whose
    threads all run at lower priority. Heuristic; on real targets confirm with
    tracelogger .kev data."""
    by_pid = {p.pid: p for p in s.processes}
    out = []
    for p in s.processes:
        for t in p.threads:
            if t.state in ("MUTEX", "SEND", "REPLY") and t.blocked_on and t.blocked_on.isdigit():
                owner = by_pid.get(int(t.blocked_on))
                if owner and owner.threads and max(x.priority for x in owner.threads) < t.priority:
                    out.append({"waiter": f"{p.name}/{t.tid}", "prio": t.priority, "state": t.state,
                                "owner": owner.name, "owner_max_prio": max(x.priority for x in owner.threads)})
    return out
