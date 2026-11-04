# QNXray - an X-ray for QNX 8.0 scheduling

> Host CLI + VS Code extension + on-target agent/resource manager that shows live process/thread
> scheduling on a QNX 8.0 target, flags priority inversions by following message-passing chains,
> captures kernel traces (tracelogger), gates CI, and explains crashes (offline rules, optional LLM).

**Category:** Developer Tooling & Host Tools. **Status:** working end-to-end on a live QNX SDP 8.0 QEMU target
(`scripts/smoke_live.sh`: 8/8 PASS). Demo video script: `demo/STORYBOARD.md`.

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
