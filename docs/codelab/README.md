# Codelab: Catch and fix a priority inversion on QNX 8.0 (in QEMU)

**Duration:** about 45 minutes · **Level:** intermediate · **Target:** QNX SDP 8.0, x86_64 QEMU · **Last updated:** Nov 2026

## What you'll learn
- Boot the QNX 8.0 QEMU quickstart image headless and reach it over SSH.
- Cross-compile a QNX program with `qcc` and run it on the target.
- Why QNX message passing normally *prevents* priority inversion (client-driven priority inheritance), and how `_NTO_CHF_FIXED_PRIORITY` turns that off.
- Spot an inversion by hand with `pidin`, then automatically with QNXray (CLI, `/dev/qnxray` resource manager, kernel trace timeline, CI gate).
- Fix it, and prove the fix with a CI check that fails before and passes after.

## What you'll need
- A Linux x86_64 host with QEMU (`qemu-system-x86_64`), Python 3.10+, and `ssh`.
- A myQNX account with the free QNX Everywhere (non-commercial) licence, QNX SDP 8.0 installed (this codelab assumes `~/qnx800`), and the `com.qnx.qnx800.quickstart.qemu` image.
- This repo: `git clone <repo-url> qnxray && cd qnxray`.

---

## Step 1: Set up the SDK environment
```bash
source ~/qnx800/qnxsdp-env.sh
qcc -V 2>&1 | head -3          # should list gcc_ntox86_64
which traceprinter             # host trace decoder, used in Step 7
```
Every new shell needs `qnxsdp-env.sh` sourced first, because it puts `qcc`, `traceprinter` and the target headers on your path.

## Step 2: Boot QNX 8.0 in QEMU
Unpack the quickstart image to `~/qnx800/images/qemu/qemu/output` (it contains `ifs.bin` and `disk-qemu.vmdk`), then run:
```bash
scripts/boot_qemu.sh           # headless; forwards 127.0.0.1:2222 -> target:22
tail -f ~/qnxvm/qemu.out       # serial console; wait for the login prompt (about 1 min under TCG)
```
The script writes guest changes to a qcow2 overlay, so the original image stays clean. It uses software emulation (TCG) by default. If KVM works on your host, `QNX_KVM=1 scripts/boot_qemu.sh` is much faster.

> **Tip:** If nothing appears on the serial log with KVM, use TCG. Some nested-virt hosts hang silently.

## Step 3: Connect over SSH
The quickstart image ships the user `qnxuser` (password `qnxuser`). Install a key once:
```bash
ssh-keygen -t ed25519 -f ~/.ssh/qnxvm -N ''
ssh-copy-id -i ~/.ssh/qnxvm -p 2222 qnxuser@127.0.0.1
cat >> ~/.ssh/config <<'CFG'
Host qnxvm
  HostName 127.0.0.1
  Port 2222
  User qnxuser
  IdentityFile ~/.ssh/qnxvm
CFG
ssh qnxvm uname -a              # QNX qnxqemu 8.0.0 ... x86_64
```
The image uses **secure procfs**, so a normal user sees only their own processes. Scheduling at FIFO priorities also needs root. QNXray runs its target commands with `sudo -n`, so allow that for `qnxuser`, on a dev VM only:
```bash
ssh -t qnxvm 'echo "qnxuser ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/qnxray'
```

## Step 4: Build and run the buggy program
`examples/inversion/main.c` starts three processes, all pinned to CPU 0:

| role   | prio (FIFO) | does |
|--------|-------------|------|
| server | 10 | `MsgReceive()`, then 0.5 s of work, then `MsgReply()` |
| hog    | 20 | spins on the CPU (unrelated medium-priority work) |
| client | 30 | `MsgSend()` to the server and waits for the reply |

The bug is one flag:
```c
int chid = ChannelCreate(_NTO_CHF_FIXED_PRIORITY);   // disables priority inheritance
```
Build it on the host, then copy it to the target and run it:
```bash
qcc -Vgcc_ntox86_64 -g -o build/inversion examples/inversion/main.c
scp build/inversion qnxvm:/tmp/
ssh qnxvm 'sudo -n /tmp/inversion 3'
```
Output:
```
inversion demo: server=18587678 hog=18591775 client=18591776
client(prio 30): reply after 3.20s (expected 0.5s) -> priority inversion
```
The prio-30 client should have waited 0.5 s. It waited for the whole hog run instead, because a prio-20 thread held up a prio-30 one.

## Step 5: See it by hand with `pidin`
In one terminal, run `ssh qnxvm 'sudo -n /tmp/inversion 20'`. In another, run:
```bash
ssh qnxvm 'sudo -n pidin | grep inversion'
```
```
20500509   1 tmp/inversion   10f READY
20504608   1 tmp/inversion   20f RUNNING
20504609   1 tmp/inversion   30f REPLY          20500509
```
To read this:
- The client (30) is **REPLY-blocked** on pid 20500509, the server.
- The server is still at **10** and only **READY**, because it is runnable but not running.
- The hog (20) is **RUNNING**.

That combination is the signature of a priority inversion: a blocked high-priority waiter, an owner below the waiter's priority, and a mid-priority thread holding the CPU.

## Step 6: Detect it automatically with QNXray
```bash
pip install -e cli            # or: export PYTHONPATH=$PWD/cli
python3 -m qnxray --target qnxvm inversions
```
```json
[{"waiter": "/tmp/inversion[20504609]/1", "prio": 30, "state": "REPLY",
  "owner": "/tmp/inversion", "owner_pid": 20500509, "owner_max_prio": 10,
  "owner_states": ["READY"], "preempted_by": ["/tmp/inversion[20504608]/1@20"],
  "severity": "high"}]
```
**Optional: use a QNX resource manager as the data source.** `agent/qnxray-resmgr.c` registers `/dev/qnxray` with `resmgr_attach()`. Every `open()` takes a fresh snapshot of all processes and threads, which it collects through `devctl(DCMD_PROC_INFO / DCMD_PROC_TIDSTATUS)`, and `read()` streams it back as JSON:
```bash
qcc -Vgcc_ntox86_64 -DQNXRAY_NO_MAIN -o build/qnxray-resmgr agent/qnxray-resmgr.c agent/qnxray-agent.c
scp build/qnxray-resmgr qnxvm:/tmp/ && ssh qnxvm 'sudo -n /tmp/qnxray-resmgr'
ssh qnxvm 'cat /dev/qnxray | head -c 120'
python3 -m qnxray --target qnxvm --source resmgr inversions
```
The resource manager is an ordinary user-space process that takes ownership of a pathname. This is the same mechanism QNX drivers use.

## Step 7: Watch it on a kernel-trace timeline
```bash
python3 -m qnxray --target qnxvm timeline --run /tmp/inversion --match inversion
```
```
timeline 1.000s ('#' = on CPU)
  .../1 tmp/inversion |                                    | READY=0.999s     <- server, starved
  .../1 tmp/inversion |####################################| RUNNING=0.999s   <- hog
  .../1 tmp/inversion |                                    | REPLY=0.999s     <- client, waiting
```
Behind the scenes, QNXray:
- runs `tracelogger -s 1` on the target, at priority 40 so that the hog cannot starve the logger itself;
- copies the `.kev` file back to the host;
- decodes it with the SDP's `traceprinter`;
- turns the thread-state events into per-thread time spent in each state.

## Step 8: Fail the build on it (CI gate)
```bash
python3 -m qnxray --target qnxvm ci --background "build/inversion 6" --seconds 2 --report ci.json; echo "exit=$?"
# exit=2  (0 clean, 1 crash, 2 inversion, 3 both); ci.json holds the findings and explanations
```

## Step 9: Fix it with priority inheritance
By default, QNX makes the receiving server thread run at the **priority of the highest-priority client it is serving**. This is client-driven priority inheritance. So the fix is to stop turning it off:
```c
int chid = ChannelCreate(0);      // default: server inherits client priority
```
The demo has this fix behind a flag, so you can compare the two cases:
```bash
ssh qnxvm 'sudo -n /tmp/inversion 3 --inherit'
# client(prio 30): reply after 0.50s (expected 0.5s) -> OK, server inherited prio 30
python3 -m qnxray --target qnxvm ci --background "build/inversion 6 --inherit" --seconds 2; echo "exit=$?"
# exit=0
```
While it serves the prio-30 client, the server runs at 30, ahead of the prio-20 hog, so the inversion disappears.

> **Other places this bites:** mutexes default to priority inheritance on QNX (`PTHREAD_PRIO_INHERIT`). If you use `PTHREAD_PRIO_NONE`, or a semaphore or condition variable without an owner, the kernel has nobody to boost. For those, use a priority-ceiling mutex (`PTHREAD_PRIO_PROTECT`) or design the problem away.

## Step 10: Clean up
```bash
ssh qnxvm 'sudo -n slay -f inversion; sudo -n slay -f qnxray-resmgr'
kill "$(cat ~/qnxvm/qemu.pid)"       # stop the VM; delete ~/qnxvm/overlay.qcow2 to reset it
```

## Recap
- You booted QNX 8.0 in QEMU and cross-compiled for it with `qcc`.
- You reproduced a priority inversion that a single channel flag had introduced.
- You detected it with `pidin`, the QNXray detector, a `/dev/qnxray` resource manager and a kernel-trace timeline.
- You gated CI on it, then fixed it by restoring QNX's message-passing priority inheritance.

## Troubleshooting
- **`sched_setscheduler: Operation not permitted`**: run the demo with `sudo`.
- **pidin shows only your own processes**: this is secure procfs. Use `sudo -n pidin`.
- **`tracelogger: Resource busy`**: an earlier trace is still active. Run `sudo slay -f tracelogger` and retry.
- **SSH is sluggish while the demo runs**: the prio-20 hog owns CPU 0 under TCG. Use short durations, or give the VM more vCPUs.
