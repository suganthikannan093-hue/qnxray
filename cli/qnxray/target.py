"""Real-target backends. SSH backend runs `pidin` on the QNX QEMU target
(QSTI images ship sshd; verify user/IP via `mkqnximage --getip`)."""
import subprocess
from .pidin import parse

class SshTarget:
    def __init__(self, host, user="root"):
        self.host, self.user = host, user
    def _ssh(self, cmd):
        return subprocess.run(["ssh", "-o", "BatchMode=yes", f"{self.user}@{self.host}", cmd],
                              capture_output=True, text=True, timeout=20, check=True).stdout
    def snapshot(self):
        return parse(self._ssh("pidin"))
    def deploy(self, local, remote="/tmp/"):
        subprocess.run(["scp", local, f"{self.user}@{self.host}:{remote}"], check=True)
    def trace(self, seconds=2, out="/dev/shmem/tracebuffer.kev"):
        # tracelogger -s <sec> time-based mode; requires root (QNX 8.0 tracelogger docs)
        return self._ssh(f"tracelogger -s {int(seconds)} -f {out} && ls -l {out}")
