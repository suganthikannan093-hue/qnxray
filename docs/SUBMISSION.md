# Devpost submission draft (owner to review and paste)

**Name:** QNXray - an X-ray for QNX 8.0 scheduling
**Category:** Developer Tooling & Host Tools
**Bonus entries:** Best Use of QNX-specific Tech; Best Codelab/Tutorial (URL: `<public repo>/blob/main/docs/codelab/README.md`)
**Video:** `<YouTube link>`   **Repo:** `<public GitHub link>`

## What it does
**Automatic priority-inversion detection + CI gating + AI root cause - with the fix verified on the target.**
A priority-30 thread asks a server for a 0.5 s reply and waits 3.2 s. Nothing crashes, nothing is logged.
QNXray finds this by itself on a live QNX 8.0 target, fails the CI build on it, has an AI model explain the
root cause from real QNX evidence, and `qnxray fix --verify` applies the AI's patch, rebuilds with `qcc`,
reruns it on the target and measures 3.20 s → 0.50 s.
- **AI root cause** for inversions and crashes (OpenAI-compatible, JSON-validated, secrets redacted, offline fallback);
  shown in the CLI, in CI JSON reports and in the VS Code dashboard.
- **Fix & verify** (`qnxray fix --verify`, dashboard button, `ci --fix` writes the patch).
- **Live snapshot** of every process/thread (state, priority, policy, blocked-on, CPU) through our own
  resource manager `/dev/qnxray`, or `pidin`.
- **Priority-inversion detection** by following message-passing chains: names the waiter, the server it is
  REPLY-blocked on, and the thread preempting that server.
- **Kernel-trace proof**: `tracelogger` capture decoded into a per-thread timeline.
- **VS Code dashboard**: live findings, per-CPU lanes, timeline, buttons for trace / crash / CI.
- **CI gate**: exit 2 on inversion, 1 on crash, 0 clean, JSON report.
- **Crash explainer**: collects the dumper core; AI explains it with file, line and patch.
- The fix demonstrated: priority inheritance (`--inherit`) drops the reply from 3.20 s to 0.50 s.

## Why not just use the QNX Momentics/VS Code toolkit?
The official tools are excellent for interactive debugging and trace viewing; QNXray adds the automated
layer on top. Every "official" cell below is taken from the linked QNX SDP 8.0 documentation.

| Need | QNX Momentics IDE / QNX Toolkit for VS Code (official docs) | QNXray |
|---|---|---|
| Find a priority inversion | Manual: capture a `.kev` trace, filter the Timeline to the threads you suspect, zoom to the slow interval "to within a few milliseconds", search events and read the sequence yourself ([Momentics: Detecting priority inversion](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.ide.userguide/topic/detecting_priority_inversion.html)) | **Automatic**: follows the `MsgSend`/REPLY chain on every live snapshot and names waiter, blocked server and preempting thread (`qnxray inversions`) |
| Trace analysis in VS Code | System Profiler views (Event Table, Timeline, Event Density, CPU Usage) for viewing/filtering a trace ([Toolkit: Using the System Profiler](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.qnxtoolkit.user_guide/topic/using_the_system_profiler.html)); the Toolkit's own transition guide lists "limited functionality for viewing results" ([Transitioning from Momentics IDE](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.qnxtoolkit.user_guide/topic/transition_guide_for_momentics_ide.html)) | tracelogger capture decoded into a per-thread timeline and attached as **evidence** to the finding |
| Fail a CI build on an inversion | No pass/fail inversion check is described in the docs above (analysis is interactive) | `qnxray ci`: exit 2 = inversion, 1 = crash, 0 = clean, JSON report; headless over ssh |
| Crash post-mortem in VS Code | Postmortem core-file debugging "isn't supported" in the Toolkit; a manual `launch.json` workaround is documented ([Toolkit: Launching an application](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.qnxtoolkit.user_guide/topic/launching_an_application.html)). Momentics can download and open the core in GDB ([Momentics: Debugging a core file](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.ide.userguide/topic/debugging_postmortem.html)) | Runs the binary, collects the dumper core, extracts the backtrace and explains it (one command, also in CI) |
| Root-cause explanation | Not described in the docs above (you interpret the trace / debugger state) | **AI root cause** from structured evidence (backtrace + source lines, thread states, inversion chain, timeline), JSON-validated, with QNX-specific fix; offline rules when no key |
| Fix and prove it | Not described in the docs above | **`qnxray fix --verify`**: AI patch → `qcc` rebuild → rerun on the target → measured before/after (3.20 s → 0.50 s) + unified diff; "Fix & verify" button; `ci --fix` writes the patch |

QNXray complements the official tools: use Momentics/System Profiler for deep manual dives; use QNXray to
catch, explain and fix the inversion automatically, and to keep it from coming back in CI.

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
