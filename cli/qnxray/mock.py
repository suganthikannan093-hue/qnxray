"""Mock target: synthesises realistic QNX-like process/thread churn so the UI
can be developed without QNX SDP. Includes a deliberate priority-inversion
scenario and a crash event for the AI explainer."""
import random, time
from .model import Snapshot, Process, Thread

BASE = [
    (1, "procnto-smp-instr", [(1, 255, "f", "READY"), (2, 255, "f", "RUNNING"), (3, 10, "r", "RECEIVE")]),
    (4100, "devc-pty", [(1, 10, "r", "RECEIVE")]),
    (8200, "io-sock", [(1, 21, "r", "RECEIVE"), (2, 21, "r", "RECEIVE")]),
    (12300, "slogger2", [(1, 10, "r", "RECEIVE")]),
    (20500, "sensor_fusion", [(1, 40, "f", "RUNNING"), (2, 40, "f", "MUTEX")]),
    (20501, "logger_lowprio", [(1, 8, "r", "READY")]),
]

class MockTarget:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.tick = 0
    def snapshot(self) -> Snapshot:
        self.tick += 1
        s = Snapshot(timestamp=time.time(), source="mock")
        for pid, name, ths in BASE:
            p = Process(pid=pid, name=name)
            for tid, prio, pol, st in ths:
                if st in ("READY", "RUNNING", "RECEIVE") and self.rng.random() < 0.3:
                    st = self.rng.choice(["READY", "RUNNING", "RECEIVE", "REPLY"])
                blocked = "20501" if (name == "sensor_fusion" and st == "MUTEX") else None
                p.threads.append(Thread(tid, name, prio, pol, st, blocked, cpu=self.rng.randrange(4)))
            s.processes.append(p)
        return s
    def crash_report(self):
        return {"program": "crashy", "pid": 24601, "signal": "SIGSEGV", "code": "SEGV_MAPERR",
                "fault_addr": "0x0", "backtrace": ["crashy:read_sensor+0x1c (main.c:42)", "crashy:main+0x40 (main.c:77)"],
                "note": "synthetic report shaped like dumper -b slog backtrace; replace with real core analysis"}
