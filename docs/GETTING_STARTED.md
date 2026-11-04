# Getting started

QNXray runs on a Linux host and talks to a QNX SDP 8.0 target over ssh. Tested configuration: QNX SDP 8.0 on the
**QEMU x86_64 quick-start image**. Raspberry Pi 4 notes are at the end.

## 0. Try it without QNX (mock target)
```bash
git clone https://github.com/suganthikannan093-hue/qnxray.git && cd qnxray
export PYTHONPATH=$PWD/cli
python3 -m qnxray --target mock snapshot | head
python3 -m qnxray --target mock inversions --no-ai
python3 -m qnxray --target mock explain-crash
(cd cli && QNXRAY_LLM=off python3 -m unittest discover -s tests)    # 15 tests
```

## 1. Install QNX SDP 8.0
1. Get the free non-commercial QNX SDP 8.0 licence at <https://www.qnx.com/getqnx> and deploy it in your myQNX account.
2. Install the QNX Software Center, then SDP 8.0 (`com.qnx.qnx800`) and the QEMU image (`com.qnx.qnx800.quickstart.qemu`).
   Headless alternative: `scripts/install_sdp.sh` (reads myQNX credentials only from `~/.qnx/myqnx_options`, chmod 600).
3. Load the environment in every shell (then set `PYTHONPATH` **after** it, because the script resets it):
   ```bash
   source ~/qnx800/qnxsdp-env.sh
   export PYTHONPATH=$PWD/cli
   qcc -V                                   # lists gcc_ntox86_64, gcc_ntoaarch64le, ...
   ```

## 2. Boot the QEMU target
`scripts/boot_qemu.sh` boots the quick-start image headless (TCG, 4 vCPU, 4 GB) with a copy-on-write overlay and
forwards `127.0.0.1:2222` → target `:22`. Paths default to this project's setup; override with `QNX_QEMU_IMG`
(the image `output/` directory with `ifs.bin` + `disk-qemu.vmdk`), `VMDIR`, `QNX_SSH_PORT`; `QNX_KVM=1` tries KVM.
Boot takes about 60 s under TCG. Details and caveats: [QEMU_TARGET.md](QEMU_TARGET.md).

Add an ssh alias (key auth recommended) in `~/.ssh/config`:
```
Host qnxvm
  HostName 127.0.0.1
  Port 2222
  User qnxuser
  IdentityFile ~/.ssh/qnxvm
```
QNX secure procfs only shows a non-root user their own processes, so QNXray runs `pidin`/agent with `sudo -n`.
On the target add a NOPASSWD rule for that user (e.g. in `/etc/sudoers.d/qnxray`), or log in as root and set `QNXRAY_SUDO=0`.

```bash
ssh qnxvm uname -a                                  # QNX ... 8.0.0 ... x86_64
python3 -m qnxray --target qnxvm snapshot | head
```

## 3. Build and deploy the on-target pieces
```bash
mkdir -p build
qcc -Vgcc_ntox86_64 -g -o build/qnxray-agent agent/qnxray-agent.c
qcc -Vgcc_ntox86_64 -g -DQNXRAY_NO_MAIN -o build/qnxray-resmgr agent/qnxray-resmgr.c agent/qnxray-agent.c
qcc -Vgcc_ntox86_64 -g -o build/inversion examples/inversion/main.c
qcc -Vgcc_ntox86_64 -g -o build/crashy    examples/crashy/main.c
scp build/qnxray-agent build/qnxray-resmgr build/inversion build/crashy qnxvm:/tmp/
ssh qnxvm 'sudo -n /tmp/qnxray-resmgr'              # serves /dev/qnxray
```

## 4. First session
```bash
export QNXRAY_TARGET=qnxvm
ssh qnxvm '(sudo -n /tmp/inversion 30 &)'          # server 10, hog 20, client 30 REPLY-blocked
python3 -m qnxray --source resmgr inversions --no-ai
python3 -m qnxray timeline --seconds 1 --match inversion
export QNXRAY_LLM_KEY=...                           # optional, see AI.md
python3 -m qnxray inversions --explain --trace
python3 -m qnxray explain-crash build/crashy
python3 -m qnxray fix examples/inversion/main.c --verify
python3 -m qnxray ci --background 'build/inversion 15' --report report.json; echo "exit=$?"   # 2
scripts/smoke_live.sh                                # live end-to-end check (prints PASS per step)
```
Then open VS Code ([VSCODE.md](VSCODE.md)) and wire the gate into CI ([CI.md](CI.md)).
A step-by-step tutorial is in [codelab/README.md](codelab/README.md).

## Raspberry Pi 4 (aarch64) notes
QNXray has been tested on QEMU x86_64 only; nothing in it is x86-specific, but the Pi path is **not yet validated on
hardware** (see the roadmap).
- Image: install `com.qnx.qnx800.quickstart.rpi4` from the QNX Software Center and flash the `.img` to a micro-SD card
  (≥ 32 GB; 8 GB-RAM Pi recommended) - see the official
  [QSTI for Raspberry Pi guide](https://www.qnx.com/developers/docs/qnxeverywhere/com.qnx.doc.target_images/topic/qsti/intro.html)
  and [Installing the QSTI on a board](https://www.qnx.com/developers/docs/qnxeverywhere/com.qnx.doc.target_images/topic/qsti/install.html).
- Network: put the Pi on your LAN and use `--target qnxuser@<pi-ip>` or an ssh alias; set up sudo as above.
- Build for aarch64: use `-Vgcc_ntoaarch64le` for the agent, resource manager and examples, and set
  `QNXRAY_QCC_VARIANT=gcc_ntoaarch64le` so `qnxray build` and `qnxray fix` cross-compile for the Pi.
- Tracing needs an instrumented kernel (`procnto-smp-instr`) and `tracelogger` on the image; crash capture needs `dumper`.

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| `QNX SDP env not sourced` | `source ~/qnx800/qnxsdp-env.sh`, then re-export `PYTHONPATH` |
| `ModuleNotFoundError: qnxray` after sourcing the SDP env | the env script reset `PYTHONPATH`; export it again |
| ssh asks for a password / hangs | use key auth and an ssh alias; QNXray runs ssh non-interactively |
| `sudo: a password is required` | add the NOPASSWD sudoers rule on the target or `QNXRAY_SUDO=0` as root |
| Snapshot missing most processes | sudo not working (secure procfs) |
| `cat: /dev/qnxray: No such file` | start `/tmp/qnxray-resmgr` as root |
| `traceprinter not found` | source the SDP env or set `QNXRAY_TRACEPRINTER` |
| Empty timeline | the target kernel must be the instrumented `procnto-smp-instr`; run as root |
| `explain-crash` finds no core | `dumper` must run on the target (quick-start: `~/cores/<name>.core`) |
| AI shows `mode: offline` | no key, `QNXRAY_LLM=off`, or a network/JSON error (`ai_error` in the JSON) |
| `fix` status `no-inversion` | the program did not invert during the scan; check it runs as root and pins to one CPU like `examples/inversion` |
| QEMU boot hangs with KVM | use TCG (default) |
