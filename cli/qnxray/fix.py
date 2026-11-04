"""`qnxray fix`: AI-proposed QNX fix for a live priority inversion, applied as a patch, rebuilt with qcc,
re-run on the target and verified (before/after reply latency + inversion re-scan)."""
import difflib, os, re, shutil, subprocess, time
from .analyze import priority_inversions
from .explain import inversion_evidence, propose_fix

LAT = re.compile(r"reply after ([\d.]+)s")

def qcc(src, out):
    exe = shutil.which("qcc") or os.path.join(os.environ.get("QNX_HOST", ""), "usr", "bin", "qcc")
    subprocess.run([exe, "-V" + os.environ.get("QNXRAY_QCC_VARIANT", "gcc_ntox86_64"), "-g", "-o", out, src], check=True)

def measure(t, remote_bin, args):
    r = t._ssh(f"sudo -n {remote_bin} {args}", check=False, timeout=120)
    m = LAT.search(r.stdout); return (float(m.group(1)) if m else None), r.stdout.strip()

def scan(t, remote_bin, args, seconds=2.0):
    t._ssh(f"(sudo -n {remote_bin} {args} >/dev/null 2>&1 &)"); time.sleep(1.5)
    found, end = [], time.time() + seconds
    while time.time() < end and not found:
        snap = t.snapshot(); found = [(i, snap) for i in priority_inversions(snap) if os.path.basename(remote_bin) in i["waiter"]]
        time.sleep(0.4)
    t._ssh(f"sudo -n slay -f {os.path.basename(remote_bin)}", check=False); time.sleep(0.5)
    return found

def diff_path(source):
    """Path for a/ b/ diff headers: relative to the enclosing git repo (or cwd), never absolute."""
    src = os.path.abspath(source); d = os.path.dirname(src)
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, ".git")): return os.path.relpath(src, d)
        d = os.path.dirname(d)
    r = os.path.relpath(src)
    return os.path.basename(src) if r.startswith("..") else r


def run(t, source, args="3", verify=True, out_dir="build/fix", patch_out=None, log=print):
    os.makedirs(out_dir, exist_ok=True)
    name = os.path.basename(os.path.dirname(os.path.abspath(source))) or "app"
    before_bin = os.path.join(out_dir, f"{name}_before"); after_bin = os.path.join(out_dir, f"{name}_fixed")
    res = {"source": source, "args": args}
    qcc(source, before_bin); rb = t.deploy(before_bin)
    log(f"[1/5] built {before_bin} with qcc -V{os.environ.get('QNXRAY_QCC_VARIANT', 'gcc_ntox86_64')}, deployed to {rb}")
    found = scan(t, rb, "8")
    if not found:
        res.update(status="no-inversion"); log("no priority inversion detected"); return res
    inv, snap = found[0]; res["inversion"] = inv
    log(f"[2/5] inversion: {inv['waiter']} prio {inv['prio']} REPLY-blocked on {inv['owner']}[{inv['owner_pid']}] "
        f"@{inv['owner_max_prio']}, preempted by {', '.join(inv['preempted_by'])}")
    src = open(source).read()
    ev = inversion_evidence(inv, snap.to_dict()); ev["source"] = {"file": source}
    fx = propose_fix(ev, src); res["fix"] = fx
    log(f"[3/5] {'AI (' + fx['model'] + ')' if fx['mode'] == 'ai' else 'offline rule'} fix: {fx['qnx_fix']}")
    new = src
    for e in fx["edits"]: new = new.replace(e["find"], e["replace"], 1)
    rel = diff_path(source)
    diff = "".join(difflib.unified_diff(src.splitlines(True), new.splitlines(True), f"a/{rel}", f"b/{rel}"))
    res["patch"] = diff
    if patch_out: open(patch_out, "w").write(diff)
    patched = os.path.join(out_dir, os.path.basename(source)); open(patched, "w").write(new)
    log(diff.rstrip())
    if not verify:
        res["status"] = "patch-proposed"; return res
    qcc(patched, after_bin); ra = t.deploy(after_bin)
    log(f"[4/5] rebuilt patched source with qcc -> {ra}")
    b, bo = measure(t, rb, args); a, ao = measure(t, ra, args)
    still = scan(t, ra, "8")
    res.update(before_s=b, after_s=a, before_out=bo, after_out=ao, inversion_after=bool(still),
               status="verified" if (a is not None and b is not None and a < b and not still) else "not-verified")
    log(f"[5/5] verify on target: client reply {b:.2f}s -> {a:.2f}s; inversion after fix: {'YES' if still else 'none'} => {res['status'].upper()}")
    return res
