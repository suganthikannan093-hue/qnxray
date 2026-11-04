import argparse, json, os, subprocess, sys, time
from .mock import MockTarget
from .analyze import priority_inversions
from .explain import explain

def get_target(a):
    if a.target == "mock":
        return MockTarget(seed=a.seed)
    from .target import SshTarget
    return SshTarget(a.target)

def cmd_build(a):
    if "QNX_TARGET" not in os.environ:
        sys.exit("QNX SDP env not sourced: run `source ~/qnx800/qnxsdp-env.sh` first.")
    # qcc is the QNX compiler driver; -V selects target, e.g. gcc_ntox86_64
    out = os.path.splitext(a.source)[0]
    subprocess.run(["qcc", "-Vgcc_ntox86_64", "-g", "-o", out, a.source], check=True)
    print(out)

def main(argv=None):
    p = argparse.ArgumentParser(prog="qnxray")
    p.add_argument("--target", default=os.environ.get("QNXRAY_TARGET", "mock"), help="'mock' or target IP")
    p.add_argument("--seed", type=int, default=None)
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("snapshot"); w = sp.add_parser("watch"); w.add_argument("--interval", type=float, default=1.0)
    w.add_argument("--count", type=int, default=0)
    sp.add_parser("inversions"); sp.add_parser("explain-crash")
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
            print(json.dumps(t.snapshot().to_dict()), flush=True); n += 1; time.sleep(a.interval)
    elif a.cmd == "inversions":
        print(json.dumps(priority_inversions(t.snapshot()), indent=2))
    elif a.cmd == "explain-crash":
        rep = t.crash_report() if hasattr(t, "crash_report") else {}
        print(explain(rep))

if __name__ == "__main__":
    main()
