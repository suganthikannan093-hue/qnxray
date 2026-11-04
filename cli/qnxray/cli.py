import argparse, json, os, shutil, subprocess, sys, time
from .mock import MockTarget
from .analyze import priority_inversions
from .fix import diff_path
from .explain import explain, analyze, format_text, inversion_evidence, propose_fix

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
    subprocess.run(["qcc", "-V" + os.environ.get("QNXRAY_QCC_VARIANT", "gcc_ntox86_64"), "-g", "-o", out, src], check=True)
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
            r["explanation"] = analyze(r); rep["crashes"].append(r)
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
        snap = t.snapshot()
        for i in priority_inversions(snap):
            key = (i["waiter"], i["owner_pid"])
            if key not in seen:
                seen.add(key); sd = snap.to_dict(); i["explanation"] = analyze(i, snapshot=sd); rep["inversions"].append(i)
                if a.fix and "fix" not in rep:
                    import difflib
                    src = open(a.fix).read(); ev = inversion_evidence(i, sd); ev["source"] = {"file": a.fix}
                    fx = propose_fix(ev, src); new = src
                    for e in fx["edits"]: new = new.replace(e["find"], e["replace"], 1)
                    diff = "".join(difflib.unified_diff(src.splitlines(True), new.splitlines(True), "a/" + diff_path(a.fix), "b/" + diff_path(a.fix)))
                    rep["fix"] = dict(fx, patch=diff, patch_file=a.fix_out)
                    open(a.fix_out, "w").write(diff)
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
    iv = sp.add_parser("inversions"); iv.add_argument("--explain", action="store_true", help="human-readable AI root cause")
    iv.add_argument("--trace", action="store_true", help="add a 1 s tracelogger timeline to the AI evidence")
    iv.add_argument("--no-ai", action="store_true", help="skip the explanation field")
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
    ci.add_argument("--fix", metavar="SOURCE", help="on inversion, ask the AI for a QNX fix to SOURCE and write a unified diff")
    ci.add_argument("--fix-out", default="qnxray-fix.patch", help="where --fix writes the patch (default qnxray-fix.patch)")
    fx = sp.add_parser("fix", help="AI-proposed QNX fix for a live inversion: patch, qcc rebuild, verify on target")
    fx.add_argument("source"); fx.add_argument("--args", default="3", help="program args for the latency run")
    fx.add_argument("--verify", action="store_true", help="rebuild, rerun on the target and compare latency")
    fx.add_argument("--patch-out", default=None); fx.add_argument("--json", action="store_true")
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
        snap = t.snapshot(); invs = priority_inversions(snap)
        tl = None
        if invs and a.trace and a.target != "mock":
            try: tl = timeline_from_kev(t.capture_trace(1), os.path.basename(invs[0]["owner"]))
            except (Exception, SystemExit): tl = None
        for i in invs:
            if not a.no_ai: i["explanation"] = analyze(i, snapshot=snap.to_dict(), timeline=tl)
        if a.explain:
            for i in invs: print(f"INVERSION {i['waiter']} (prio {i['prio']}) -> {i['owner']}[{i['owner_pid']}] @{i['owner_max_prio']}, "
                                 f"preempted by {', '.join(i['preempted_by'])}\n" + format_text(i["explanation"]))
            if not invs: print("no priority inversion")
        else:
            print(json.dumps(invs, indent=2))
    elif a.cmd == "fix":
        sdp_env_check()
        from . import fix as fixmod
        r = fixmod.run(t, a.source, a.args, verify=a.verify, patch_out=a.patch_out, log=(lambda *x: None) if a.json else print)
        if a.json: print(json.dumps(r, indent=2))
        return 0 if r.get("status") in ("verified", "patch-proposed") else 1
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
        if rep.get("crashed") is False:
            print(f"{rep['binary']} exited normally (code {rep['exit_code']}).")
        else:
            rep["explanation"] = analyze(rep)
            print(json.dumps(rep, indent=2) if a.json else
                  f"CRASH {rep.get('binary')}: {rep.get('signal')} ({rep.get('signal_desc')}) at {(rep.get('backtrace') or ['?'])[0]}\n"
                  + format_text(rep["explanation"]))

if __name__ == "__main__":
    sys.exit(main())
