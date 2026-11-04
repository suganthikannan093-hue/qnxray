"""Parser for default `pidin` output on QNX 8.0.

Default columns: pid tid name prio STATE Blocked
e.g.   "  4100   1 proc/boot/devc-pty 10r RECEIVE     1"
Prio is a number followed by a policy letter (f/r/o/s).
NOTE: validate against real QNX 8.0 output once SDP access exists; fixtures in
examples/fixtures are hand-written to match the documented format, not captured.
"""
import re, time
from .model import Snapshot, Process, Thread

LINE = re.compile(r"^\s*(\d+)?\s+(\d+)\s+(\S+)?\s+(\d+)([froso]?)\s+(\S+)\s*(.*)$")

def parse(text: str, source="ssh-pidin") -> Snapshot:
    snap = Snapshot(timestamp=time.time(), source=source)
    cur = None
    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith("pid"):
            continue
        parts = raw.split()
        # A process' first line has pid; continuation lines omit pid and name.
        if len(parts) >= 5 and parts[0].isdigit() and parts[1].isdigit():
            pid, tid, name, prio, state = int(parts[0]), int(parts[1]), parts[2], parts[3], parts[4]
            blocked = parts[5] if len(parts) > 5 else None
            if cur is None or cur.pid != pid:  # pidin repeats pid on each thread line
                cur = Process(pid=pid, name=name)
                snap.processes.append(cur)
        elif len(parts) >= 3 and parts[0].isdigit() and cur is not None:
            tid, prio, state = int(parts[0]), parts[1], parts[2]
            blocked = parts[3] if len(parts) > 3 else None
            name = cur.name
        else:
            continue
        m = re.match(r"(\d+)([a-z]?)", prio)
        cur.threads.append(Thread(tid=tid, name=name, priority=int(m.group(1)) if m else -1,
                                  policy=(m.group(2) if m else "?"), state=state, blocked_on=blocked))
    return snap
