import argparse, json, os, shutil, subprocess, sys, time
from .mock import MockTarget
from .analyze import priority_inversions
from .explain import explain

def get_target(a):
    if a.target == "mock":
        return MockTarget(seed=a.seed)
    from .target import SshTarget
    return SshTarget(a.target, source=a.source)

def sdp_env_check():
    if "QNX_TARGET" not in os.environ:
        sys.exit("QNX SDP env not sourced: run `source ~/qnx800/qnxsdp-env.sh` first.")

def cmd_build(a):
    sdp_env_check()
    out = os.path.splitext(a.source)[0] if os.path.isfile(a.source) else os.path.join(a.source, os.path.basename(a.source.rstrip("/")))
    src = a.source if os.path.isfile(a.source) else os.path.join(a.source, "main.c")
    subprocess.run(["qcc", "-Vgcc_ntox86_64", "-g", "-o", out, src], check=True)
    print(out)

def timeline_from_kev(kev, match=None):
    from .trace import parse_traceprinter, build_timeline
    tp = os.environ.get("QNXRAY_TRACEPRINTER") or shutil.which("traceprinter")
    if not tp and os.environ.get("QNX_HOST"):
        tp = shutil.which("traceprinter", path=os.path.join(os.environ["QNX_HOST"], "usr/bin"))
    if not tp:
        sys.exit("traceprinter not found: source qnxsdp-env.sh (it ships in $QNX_HOST/usr/bin)")
    text = subprocess.run([tp, "-f", kev], capture_output=True, text=True, check=True).stdout
    h, ev, names = parse_traceprinter(text)
    pids = {p for p, n in names.items() if match in n} if match else None
    return build_timeline(h, ev, names, pids)

def cmd_timeline(a, t):
    from .trace import render_text
    kev = a.kev or t.capture_trace(a.seconds, during=a.run)
    tl = timeline_from_kev(kev, a.match)
    print(json.dumps(tl) if a.json else render_text(tl))

def cmd_ci(a, t):
    """CI gate: exit 1 on crash, 2 on priority inversion, 3 on both; JSON report to --report/stdout."""
    rep = {"target": a.target, "time": time.time(), "crashes": [], "inversions": [], "snapshots": 0}
    for b in a.run or []:
        rb = t.deploy(b) if hasattr(t, "deploy") else b
        if hasattr(t, "run_and_capture"):
            r = t.run_and_capture(rb, a.args)
        else:
            r = dict(t.crash_report(), crashed=True)
        if r.get("crashed"):
            r["explanation"] = explain(r); rep["crashes"].append(r)
    for b in a.background or []:     # "BIN [args...]": a workload that must not invert
        import shlex
        parts = shlex.split(b)
        rb = t.deploy(parts[0]) if hasattr(t, "deploy") else parts[0]
        extra = " ".join(shlex.quote(x) for x in parts[1:]) or str(a.seconds + 2)
        t._ssh(f"(sudo -n {rb} {extra} >/dev/null 2>&1 &)") if hasattr(t, "_ssh") else None
    if a.background: time.sleep(1.5)
    seen = set()
    end = time.time() + a.seconds
    while True:
        rep["snapshots"] += 1
        for i in priority_inversions(t.snapshot()):
            key = (i["waiter"], i["owner_pid"])
            if key not in seen: seen.add(key); i["explanation"] = explain(i); rep["inversions"].append(i)
        if time.time() >= end: break
        time.sleep(a.interval)
    code = (1 if rep["crashes"] else 0) | (2 if rep["inversions"] else 0)
    rep["exit_code"] = code; rep["status"] = "fail" if code else "pass"
    out = json.dumps(rep, indent=2)
    if a.report:
        open(a.report, "w").write(out)
    print(out)
    return code

def main(argv=None):
    p = argparse.ArgumentParser(prog="qnxray")
    p.add_argument("--target", default=os.environ.get("QNXRAY_TARGET", "mock"),
                   help="'mock', an ssh alias (e.g. qnxvm) or [user@]host[:port]")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--source", choices=["pidin", "agent", "resmgr"], default=None,
                   help="snapshot source on an ssh target (env QNXRAY_SOURCE); resmgr reads /dev/qnxray")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("snapshot"); w = sp.add_parser("watch"); w.add_argument("--interval", type=float, default=1.0)
    w.add_argument("--count", type=int, default=0)
    sp.add_parser("inversions")
    ec = sp.add_parser("explain-crash"); ec.add_argument("binary", nargs="?", default=None,
        help="local QNX binary to deploy+run (or remote path with --remote)")
    ec.add_argument("--remote", action="store_true"); ec.add_argument("--json", action="store_true")
    tl = sp.add_parser("timeline", help="tracelogger capture -> per-thread timeline")
    tl.add_argument("--seconds", type=int, default=1); tl.add_argument("--kev", help="decode an existing .kev instead")
    tl.add_argument("--run", help="remote command to run during capture"); tl.add_argument("--match", help="only processes whose name contains this")
    tl.add_argument("--json", action="store_true")
    ci = sp.add_parser("ci", help="exit non-zero on crash (1) / inversion (2); JSON report")
    ci.add_argument("--run", action="append", help="local binary to deploy+run; crash fails the gate")
    ci.add_argument("--args", default="")
    ci.add_argument("--background", action="append", help="'local_binary [args]' started (as root) during the inversion scan; default arg = seconds+2")
    ci.add_argument("--seconds", type=float, default=3); ci.add_argument("--interval", type=float, default=0.5)
    ci.add_argument("--report", help="write JSON report here")
    b = sp.add_parser("build"); b.add_argument("source")
    a = p.parse_args(argv)
    if a.cmd == "build":
        return cmd_build(a)
    t = get_target(a)
    if a.cmd == "snapshot":
        print(json.dumps(t.snapshot().to_dict()))
    elif a.cmd == "watch":   # NDJSON stream consumed by the VS Code extension
        n = 0
        while a.count == 0 or n < a.count:
            snap = t.snapshot(); d = snap.to_dict(); d["inversions"] = priority_inversions(snap)
            print(json.dumps(d), flush=True); n += 1; time.sleep(a.interval)
    elif a.cmd == "inversions":
        print(json.dumps(priority_inversions(t.snapshot()), indent=2))
    elif a.cmd == "timeline":
        if a.target == "mock" and not a.kev: sys.exit("timeline needs a live target or --kev")
        cmd_timeline(a, t)
    elif a.cmd == "ci":
        return cmd_ci(a, t)
    elif a.cmd == "explain-crash":
        if a.binary and hasattr(t, "deploy"):
            rb = a.binary if a.remote else t.deploy(a.binary)
            rep = t.run_and_capture(rb)
        else:
            rep = t.crash_report() if hasattr(t, "crash_report") else {}
        if a.json:
            print(json.dumps(rep, indent=2))
        if rep.get("crashed") is False:
            print(f"{rep['binary']} exited normally (code {rep['exit_code']}).")
        else:
            print(explain(rep))

if __name__ == "__main__":
    sys.exit(main())
