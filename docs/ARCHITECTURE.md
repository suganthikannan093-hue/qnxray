# QNXray architecture

```
VS Code extension (TypeScript)  --spawn-->  qnxray CLI (Python, stdlib only)  --backend-->  target
  webview dashboard  <--NDJSON snapshots--        |  mock      : MockTarget (no QNX needed)
  commands: build / dashboard / explain           |  ssh-pidin : ssh root@<ip> pidin  (works on stock QSTI)
                                                  |  agent     : qnxray-agent on target (/proc + devctl)
                                                  |  trace     : tracelogger -> .kev -> host analysis
```

## Target-side data sources (all QNX 8.0 docs)
| Data | Interface | Doc |
|---|---|---|
| process/thread list, prio+policy, state, blocked-on | `pidin` | https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/p/pidin.html |
| per-process info | `/proc/<pid>/ctl` + `devctl(DCMD_PROC_INFO)` | https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.prog/topic/process_DCMD_PROC_INFO.html |
| per-thread status | `devctl(DCMD_PROC_TIDSTATUS)` | https://qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.prog/topic/process_proc_filesystem.html |
| kernel events (context switches, IPC) | `tracelogger` -> `/dev/shmem/tracebuffer.kev` (root, instrumented procnto) | https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/t/tracelogger.html |
| crashes | `dumper` (`-b` slogs backtrace, `DCMD_DUMPER_NOTIFYEVENT`) | https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/d/dumper.html |
| QEMU target lifecycle | `mkqnximage --type=qemu --run/--getip/--stop` | https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/m/mkqnximage.html |
| build | `qcc -Vgcc_ntox86_64` after `source qnxsdp-env.sh` | QNX SDP 8.0 Quick Start |

Caveat from the /proc doc: /proc is a debugging interface, not for production monitoring;
QNXray is positioned as a dev-time tool, which matches that.

## Differentiation vs official QNX Toolkit for VS Code
The official toolkit already has remote run/debug, QEMU target management, live CPU/process
monitoring and a System Profiler for .kev traces. QNXray must NOT just duplicate that. Its
distinct value: (1) **schedulability insights** - automatic priority-inversion / blocked-chain
detection over pidin + .kev data, with plain-English findings; (2) **AI crash explainer** over
dumper cores + backtrace with QNX-specific context; (3) **headless CLI** usable in CI
(`qnxray inversions` exit codes); (4) target agent exposed as a QNX resource manager.
