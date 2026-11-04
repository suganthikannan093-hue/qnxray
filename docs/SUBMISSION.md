# Devpost submission draft (owner to review and paste)

**Name:** QNXray - an X-ray for QNX 8.0 scheduling
**Category:** Developer Tooling & Host Tools
**Bonus entries:** Best Use of QNX-specific Tech; Best Codelab/Tutorial (URL: `<public repo>/blob/main/docs/codelab/README.md`)
**Video:** `<YouTube link>`   **Repo:** `<public GitHub link>`

## What it does
A priority-30 thread asks a server for a 0.5 s reply and waits 3.2 s. Nothing crashes, nothing is logged.
QNXray makes this class of real-time bug visible on a live QNX 8.0 target:
- **Live snapshot** of every process/thread (state, priority, policy, blocked-on, CPU) through our own
  resource manager `/dev/qnxray`, or `pidin`.
- **Priority-inversion detection** by following message-passing chains: names the waiter, the server it is
  REPLY-blocked on, and the thread preempting that server.
- **Kernel-trace proof**: `tracelogger` capture decoded into a per-thread timeline.
- **VS Code dashboard**: live findings, per-CPU lanes, timeline, buttons for trace / crash / CI.
- **CI gate**: exit 2 on inversion, 1 on crash, 0 clean, JSON report.
- **Crash explainer**: collects the dumper core and explains it (offline rules; optional LLM).
- The fix demonstrated: priority inheritance (`--inherit`) drops the reply from 3.20 s to 0.50 s.

## Evidence of QNX use
QNX SDP 8.0, QEMU x86_64 target, `qcc -Vgcc_ntox86_64`.
- `agent/qnxray-resmgr.c` - resource manager (`resmgr_attach`, `iofunc_*`, `dispatch_*`, extended OCB).
- `agent/qnxray-agent.c` - `devctl(DCMD_PROC_INFO / DCMD_PROC_TIDSTATUS)` over `/proc`.
- `cli/qnxray/analyze.py` - inversion analysis on QNX thread states (REPLY/SEND/RECEIVE) and priorities.
- `cli/qnxray/trace.py`, `target.py` - `tracelogger` + `traceprinter`, ssh deploy, dumper cores.
- `examples/inversion/main.c` - `ChannelCreate(_NTO_CHF_FIXED_PRIORITY)`, `MsgSend`/`MsgReceive`.
- Output: `demo/raw/scenes/*.txt` (real target captures), `scripts/smoke_live.sh` (8/8 PASS).

## How it was built
New project, started 4 Nov 2026 during the submission period. Python host CLI, TypeScript VS Code
extension, C on-target agent/resource manager.
