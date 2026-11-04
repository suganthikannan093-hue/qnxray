# CLI reference

```
qnxray [--target TARGET] [--source {pidin,agent,resmgr}] [--seed N] COMMAND [options]
```
Run as `python3 -m qnxray` with `PYTHONPATH=<repo>/cli`, or `pip install ./cli` for a `qnxray` command.
Python 3.9+, standard library only.

## Global options
| Option | Env | Default | Meaning |
|---|---|---|---|
| `--target` | `QNXRAY_TARGET` | `mock` | `mock` (built-in simulated target), an ssh alias (`qnxvm`) or `[user@]host[:port]` |
| `--source` | `QNXRAY_SOURCE` | `pidin` (or `agent` if `QNXRAY_AGENT` is set) | Snapshot source on an ssh target |
| `--seed` | – | – | Seed for the mock target |

### Snapshot sources
| Source | How | Needs |
|---|---|---|
| `pidin` | `pidin -F '%a %b %N %p %J %B'` over ssh | nothing extra (stock image) |
| `agent` | `qnxray-agent` prints JSON from `/proc/<pid>/ctl` + `devctl(DCMD_PROC_INFO / DCMD_PROC_TIDSTATUS)` | binary at `$QNXRAY_AGENT` on the target |
| `resmgr` | `cat /dev/qnxray` - QNXray's resource manager returns a fresh snapshot on every read | `qnxray-resmgr` running (path: `QNXRAY_RESMGR`, default `/dev/qnxray`) |

On an ssh target, commands run through `sudo -n` (`QNXRAY_SUDO=1`, default) because QNX secure procfs only shows
a non-root user their own processes.

## Commands

### `snapshot`
Prints one JSON snapshot: `{"source","timestamp","processes":[{"pid","name","threads":[{"tid","name","priority","policy","state","blocked_on","cpu"}]}]}`.

### `watch [--interval S] [--count N]`
NDJSON stream of snapshots, each with an `inversions` array. The VS Code dashboard consumes this.

### `inversions [--explain] [--trace] [--no-ai]`
Detects priority inversions in the current snapshot. Default output is a JSON array; each item has `waiter`,
`prio`, `state`, `owner`, `owner_pid`, `owner_max_prio`, `owner_states`, `preempted_by`, `severity` and `explanation`.
- `--explain`: human-readable AI root cause instead of JSON.
- `--trace`: capture 1 s of `tracelogger` and add the owner's timeline to the AI evidence.
- `--no-ai`: no `explanation` field (fast, no network).

### `explain-crash [BINARY] [--remote] [--json]`
Deploys `BINARY` (a local QNX binary) to `/tmp`, runs it, collects the `dumper` core, symbolizes it with the target's
gdb and explains it (without BINARY: runs `/tmp/crashy` on an ssh target, or the mock's sample crash). `--remote` treats `BINARY` as a path already on the target. `--json` prints the full report
including `backtrace`, `signal` and `explanation`.

### `timeline [--seconds S] [--run CMD] [--match NAME] [--kev FILE] [--json]`
Runs `tracelogger` on the target (at priority 40r so a CPU hog cannot starve it), copies the `.kev` and decodes it with
host `traceprinter` into per-thread time RUNNING/READY/REPLY. `--run` starts a command during the capture,
`--match` keeps processes whose name contains NAME, `--kev` decodes an existing file offline.
`traceprinter` is found on `PATH`, in `$QNX_HOST/usr/bin`, or at `QNXRAY_TRACEPRINTER`.

### `ci ...`
See [CI.md](CI.md). Options: `--run BIN` (repeatable; crash fails), `--args ARGS` for `--run`,
`--background 'BIN [ARGS]'` (repeatable; workload started as root during the scan, default arg = seconds+2),
`--seconds S` (scan length, default 3), `--interval S` (default 0.5), `--report FILE`, `--fix SOURCE`, `--fix-out FILE`
(default `qnxray-fix.patch`).

### `fix SOURCE [--verify] [--args A] [--patch-out FILE] [--json]`
See [AI.md](AI.md#fix--verify). Exit code 0 when the status is `verified` or `patch-proposed`, else 1.

### `build SOURCE`
`qcc -V$QNXRAY_QCC_VARIANT -g` (default variant `gcc_ntox86_64`) of a `.c` file (output next to it, without
extension) or of `DIR/main.c` (output `DIR/DIR`). Requires the SDP environment.

## Environment variables
| Variable | Used by | Meaning |
|---|---|---|
| `QNXRAY_TARGET`, `QNXRAY_SOURCE` | all | defaults for `--target`, `--source` |
| `QNXRAY_SUDO` | ssh target | `1` (default) run target commands via `sudo -n` |
| `QNXRAY_AGENT` | `agent` source | path of `qnxray-agent` on the target |
| `QNXRAY_RESMGR` | `resmgr` source | device path (default `/dev/qnxray`) |
| `QNXRAY_TRACEPRINTER` | timeline | path to host `traceprinter` |
| `QNXRAY_QCC_VARIANT` | build, fix | qcc `-V` variant (default `gcc_ntox86_64`; `gcc_ntoaarch64le` for aarch64) |
| `QNXRAY_LLM_KEY` / `OPENAI_API_KEY` | AI | API key (environment only) |
| `QNXRAY_LLM_URL`, `QNXRAY_LLM_MODEL`, `QNXRAY_LLM_TIMEOUT`, `QNXRAY_LLM` | AI | see [AI.md](AI.md) |
| `QNXRAY_SRC_ROOT` | crash explainer | where to look for source files named in the backtrace |
