"""Shared snapshot model. Field names follow pidin/procfs terminology
(pid, tid, priority, scheduling policy, thread state)."""
from dataclasses import dataclass, field, asdict
from typing import List, Optional

# Thread states as printed by pidin (QNX 8.0 Utilities Reference, pidin).
THREAD_STATES = ["RUNNING", "READY", "RECEIVE", "REPLY", "SEND", "CONDVAR",
                 "MUTEX", "NANOSLEEP", "SIGWAITINFO", "INTR", "SEM", "JOIN", "DEAD", "STOPPED"]

@dataclass
class Thread:
    tid: int
    name: str
    priority: int
    policy: str          # 'f' FIFO, 'r' round-robin, 'o' other, 's' sporadic (pidin suffix)
    state: str
    blocked_on: Optional[str] = None
    cpu: Optional[int] = None

@dataclass
class Process:
    pid: int
    name: str
    threads: List[Thread] = field(default_factory=list)

@dataclass
class Snapshot:
    timestamp: float
    source: str          # "mock" | "ssh-pidin" | "agent"
    processes: List[Process] = field(default_factory=list)
    def to_dict(self):
        return asdict(self)
