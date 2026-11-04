# QNXray - an X-ray for QNX 8.0 scheduling

> **Automatic priority-inversion detection + CI gating + AI root cause - and a fix verified on the target.**
> QNXray watches a live QNX 8.0 target, finds priority inversions by itself by following message-passing
> chains, fails the CI build on them, explains inversions and crashes with an AI model fed real QNX evidence
> (backtrace, source, thread states, tracelogger timeline), and `qnxray fix --verify` applies the AI's patch,
> rebuilds with `qcc`, reruns on the target and measures the result (3.20 s → 0.50 s).
> Host CLI + VS Code extension + on-target agent/resource manager `/dev/qnxray`.

**Category:** Developer Tooling & Host Tools. **Status:** working end-to-end on a live QNX SDP 8.0 QEMU target
(`scripts/smoke_live.sh`: 8/8 PASS). Demo video script: `demo/STORYBOARD.md`.

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

## AI root cause and fix & verify
- Key: `QNXRAY_LLM_KEY`, else `OPENAI_API_KEY` (environment only, never in settings/files). Any OpenAI-compatible
  endpoint: `QNXRAY_LLM_URL`, model `QNXRAY_LLM_MODEL` (default `gpt-5.4-mini`). `QNXRAY_LLM=off` forces offline rules.
- Sent: structured evidence only (signal, backtrace, source lines around the fault; or the waiter/blocker/preemptor
  chain, involved thread states, timeline). Strings that look like keys/tokens are redacted before sending.
- Reply must be JSON (`summary, root_cause, evidence[], qnx_fix, patch, confidence`); invalid replies fall back to
  offline rules, so CI never breaks on the network. Fix patches are applied only if each edit matches the source
  exactly once and the patched source passes a QNX lint (no `_NTO_CHF_FIXED_PRIORITY` reachable on the channel).
```bash
qnxray --target qnxvm explain-crash build/crashy                  # AI crash root cause
qnxray --target qnxvm inversions --explain --trace                 # AI inversion root cause (+ 1 s trace evidence)
qnxray --target qnxvm fix examples/inversion/main.c --verify       # patch -> qcc -> rerun -> before/after
qnxray --target qnxvm ci --background 'build/inversion 15' --fix examples/inversion/main.c --fix-out fix.patch
```
Real captured outputs: `examples/fixtures/ai_crash.json`, `ai_inversion.json|.txt`, `ai_fix_verify.json|.txt`.

## Requirements (tested configuration)
| | |
|---|---|
| QNX version | **QNX SDP 8.0** (QNX Everywhere non-commercial licence), `uname`: `QNX 8.0.0 x86pc x86_64` |
| Target | **QEMU x86_64** QNX 8.0 quick-start image (TCG, 1 vCPU OK) reachable as ssh alias `qnxvm` - see `docs/QEMU_TARGET.md` |
| Toolchain | **`qcc -Vgcc_ntox86_64`** from SDP 8.0 (`source ~/qnx800/qnxsdp-env.sh`); `tracelogger` on target, `traceprinter` on host |
| Host | Linux, Python 3.10+, Node 18+ (extension), ssh |

## Build and run on QNX 8.0
```bash
source ~/qnx800/qnxsdp-env.sh
scripts/boot_qemu.sh                        # boot the QEMU QNX 8.0 target (docs/QEMU_TARGET.md)
mkdir -p build
qcc -Vgcc_ntox86_64 -g -o build/qnxray-agent  agent/qnxray-agent.c
qcc -Vgcc_ntox86_64 -g -DQNXRAY_NO_MAIN -o build/qnxray-resmgr agent/qnxray-resmgr.c agent/qnxray-agent.c
qcc -Vgcc_ntox86_64 -g -o build/inversion examples/inversion/main.c
qcc -Vgcc_ntox86_64 -g -o build/crashy    examples/crashy/main.c
scp build/qnxray-resmgr build/inversion qnxvm:/tmp/ && ssh qnxvm 'sudo -n /tmp/qnxray-resmgr'   # serves /dev/qnxray
export PYTHONPATH=$PWD/cli
python3 -m qnxray --target qnxvm --source resmgr snapshot          # live JSON snapshot
ssh qnxvm '(sudo -n /tmp/inversion 30 &)'                           # start the inversion demo
python3 -m qnxray --target qnxvm inversions                        # names waiter / owner / preemptor
python3 -m qnxray --target qnxvm timeline --match inversion        # tracelogger -> per-thread timeline
python3 -m qnxray --target qnxvm ci --background 'build/inversion 15' --seconds 2; echo $?   # 2
python3 -m qnxray --target qnxvm ci --run build/crashy; echo $?                               # 1
python3 -m qnxray --target qnxvm explain-crash build/crashy        # SIGSEGV in read_sensor, file:line
scripts/smoke_live.sh                                              # all of the above, PASS/FAIL
```
VS Code: `cd extension && npm install && npx tsc -p .`, set `qnxray.target` = `qnxvm` (and optionally
`qnxray.source` = `resmgr`), run **QNXray: Open Dashboard**. Packaged: `npx vsce package`.

Mock mode (no QNX needed): `cd cli && python3 -m unittest discover -s tests && python3 -m qnxray --target mock watch --count 3`.

## Evidence of QNX use
- `agent/qnxray-resmgr.c` - QNX **resource manager** (`resmgr_attach`, `iofunc_*`, `dispatch_*`, extended OCB) serving `/dev/qnxray`.
- `agent/qnxray-agent.c` - `/proc` + `devctl(DCMD_PROC_INFO, DCMD_PROC_TIDSTATUS)`: thread state, priority, policy, blocked-on, last CPU.
- `cli/qnxray/analyze.py` - inversion detection over QNX **message-passing** (REPLY/SEND-blocked chains) and scheduling priorities.
- `cli/qnxray/target.py`, `pidin.py`, `trace.py` - ssh deploy/run, `pidin` parsing, `tracelogger` capture + `traceprinter` decoding, dumper cores.
- `examples/inversion` - `ChannelCreate(_NTO_CHF_FIXED_PRIORITY)` + MsgSend/MsgReceive server/client/hog; `--inherit` restores QNX priority inheritance (3.20 s -> 0.50 s).
- `docs/codelab/README.md` - codelab: write a QNX 8.0 resource manager. `docs/COMPLIANCE.md` - rules checklist.

## Licence
MIT (see `LICENSE`).
