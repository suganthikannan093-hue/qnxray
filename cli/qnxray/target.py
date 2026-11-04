"""Real-target backend over SSH (verified against the QNX SDP 8.0 QEMU quickstart image).

Target spec: "[user@]host[:port]" or an ~/.ssh/config alias (e.g. "qnxvm").
The quickstart image uses secure procfs, so non-root users only see their own
processes; we run pidin / the agent via `sudo -n` when QNXRAY_SUDO=1 (default).
"""
import json, os, re, shlex, subprocess, time
from .pidin import parse
from .model import Snapshot, Process, Thread

class SshTarget:
    def __init__(self, spec, sudo=None, agent=None, source=None):
        self.port = None
        if ":" in spec and not spec.startswith("["):
            spec, self.port = spec.rsplit(":", 1)
        self.dest = spec
        self.sudo = (os.environ.get("QNXRAY_SUDO", "1") == "1") if sudo is None else sudo
        self.agent = agent if agent is not None else os.environ.get("QNXRAY_AGENT")  # path on target
        # source: pidin (default) | agent | resmgr (/dev/qnxray, path via QNXRAY_RESMGR)
        self.source = source or os.environ.get("QNXRAY_SOURCE") or ("agent" if self.agent else "pidin")
        self.resmgr_path = os.environ.get("QNXRAY_RESMGR", "/dev/qnxray")
        if self.source == "agent" and not self.agent:
            self.agent = "/tmp/qnxray-agent"

    def _base(self, tool):
        args = [tool, "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
        if self.port:
            args += ["-p" if tool == "ssh" else "-P", self.port]
        return args

    def _ssh(self, cmd, timeout=60, check=True, root=False):
        if root and self.sudo:
            cmd = "sudo -n " + cmd
        r = subprocess.run(self._base("ssh") + [self.dest, cmd], capture_output=True,
                           text=True, timeout=timeout)
        if check and r.returncode != 0:
            raise RuntimeError(f"ssh failed ({r.returncode}): {cmd}\n{r.stderr.strip()}")
        return r

    def snapshot(self):
        if self.source in ("agent", "resmgr"):
            if self.source == "resmgr":   # served by qnxray-resmgr running as root; no sudo needed
                out = self._ssh(f"cat {shlex.quote(self.resmgr_path)}").stdout
            else:
                out = self._ssh(f"{shlex.quote(self.agent)} 1 1", root=True).stdout
            d = json.loads(out)
            s = Snapshot(timestamp=d.get("timestamp", time.time()), source=self.source)
            for p in d["processes"]:
                s.processes.append(Process(pid=p["pid"], name=p["name"],
                                           threads=[Thread(**t) for t in p["threads"]]))
            return s
        return parse(self._ssh("pidin", root=True).stdout)

    def deploy(self, local, remote="/tmp/"):
        subprocess.run(self._base("scp") + ["-q", local, f"{self.dest}:{remote}"], check=True)
        return remote.rstrip("/") + "/" + os.path.basename(local) if remote.endswith("/") else remote

    def run_and_capture(self, remote_bin, args=""):
        """Run a binary on the target; if it dies on a signal, read the core that
        dumper writes (quickstart: dumper -D cores -> ~/cores/<name>.core) and
        symbolize it with the on-target gdb."""
        name = os.path.basename(remote_bin)
        core = f"~/cores/{name}.core"
        self._ssh(f"rm -f {core}", check=False)
        r = self._ssh(f"cd /tmp && {shlex.quote(remote_bin)} {args}", check=False)
        rep = {"binary": remote_bin, "exit_code": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
        if r.returncode < 128 and "core dumped" not in r.stderr:
            rep["crashed"] = False
            return rep
        for _ in range(20):          # dumper writes asynchronously
            if self._ssh(f"test -s {core}", check=False).returncode == 0:
                break
            time.sleep(0.5)
        g = self._ssh(f"gdb -batch -ex bt -ex 'info registers rip' {shlex.quote(remote_bin)} {core}",
                      check=False, timeout=120).stdout
        return dict(rep, crashed=True, core=core, **parse_gdb(g))

    def crash_report(self, remote_bin="/tmp/crashy"):
        return self.run_and_capture(remote_bin)

    def capture_trace(self, seconds=1, local_kev=None, during=None):
        """Run tracelogger on the target (optionally while `during` runs), copy .kev to host."""
        import tempfile
        local_kev = local_kev or os.path.join(tempfile.gettempdir(), "qnxray-trace.kev")
        remote = "/dev/shmem/qnxray.kev"
        pre = f"(sudo -n {during} >/dev/null 2>&1 &) ; sleep 1.5; " if during else ""
        self._ssh(pre + f"sudo -n on -p 40r tracelogger -s {int(seconds)} -f {remote} >/dev/null 2>&1; "
                  f"sudo -n chmod 644 {remote}", timeout=120)
        subprocess.run(self._base("scp") + ["-q", f"{self.dest}:{remote}", local_kev], check=True)
        return local_kev

    def trace(self, seconds=2, out="/dev/shmem/tracebuffer.kev"):
        # tracelogger -s <sec> time-based mode; requires root
        return self._ssh(f"tracelogger -s {int(seconds)} -f {out} && ls -l {out}", root=True).stdout

def parse_gdb(text):
    m = re.search(r"Program terminated with signal (\w+), (.*?)\.", text)
    frames, seen = [], set()
    for line in text.splitlines():
        f = re.match(r"#(\d+)\s+(?:0x[0-9a-f]+ in )?(.*)", line)
        if f and f.group(1) not in seen:
            seen.add(f.group(1)); frames.append(f.group(2).strip())
    rip = re.search(r"^rip\s+(0x[0-9a-f]+)", text, re.M)
    return {"signal": m.group(1) if m else None, "signal_desc": m.group(2) if m else None,
            "backtrace": frames or ["?"], "pc": rip.group(1) if rip else None}
