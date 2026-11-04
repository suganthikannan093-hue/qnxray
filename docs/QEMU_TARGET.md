# Live QNX 8.0 target (QEMU quickstart image)

Image: SDP 8.0 QEMU quickstart (x86_64), unpacked at
`/home/box/qnx800/images/qemu/qemu/output` (`ifs.bin` + `disk-qemu.vmdk`).

## Boot (headless)
    scripts/boot_qemu.sh          # daemonizes; serial log in /home/box/qnxvm/qemu.out
- Writes go to a qcow2 overlay (`/home/box/qnxvm/overlay.qcow2`); the 50 GB base disk is untouched.
  Delete the overlay to reset the target.
- Networking: QEMU user-mode NAT, host `127.0.0.1:2222` -> target `:22` (no bridge/root needed;
  `mkqnximage --run` expects a host bridge, which this box doesn't have).
- Uses TCG (software emulation). KVM (`QNX_KVM=1`, via the `pulse-access` group) hangs at
  start on this box, presumably nested virtualization. Boot to login takes about 60 s.
- Stop: `kill $(cat /home/box/qnxvm/qemu.pid)`.

## Access
- User `qnxuser` (image default password `qnxuser`; member of `sudo`). Host key-auth via
  `~/.ssh/qnxvm` and the `Host qnxvm` alias in `~/.ssh/config`.
- Secure procfs: non-root sees only its own processes, so QNXray runs `pidin`/agent through
  `sudo -n`. A NOPASSWD rule was added in the overlay at `/etc/sudoers.d/qnxray`.

## Use
    export PYTHONPATH=cli
    python3 -m qnxray --target qnxvm snapshot                     # pidin backend
    QNXRAY_AGENT=/tmp/qnxray-agent python3 -m qnxray --target qnxvm snapshot   # C agent
    python3 -m qnxray --target qnxvm explain-crash build/crashy --json         # deploy, run, core, gdb
    scripts/smoke_live.sh

Crash capture: the image's `dumper -D cores` writes `~/cores/<name>.core`, and the target's own
`/system/bin/gdb` symbolizes it.

## M3/M4: inversion, timeline, CI, extension

- Demo: `examples/inversion` (build: `python3 -m qnxray build ../examples/inversion`, run as root: `/tmp/inversion [secs]`).
  Server prio 10 on a `_NTO_CHF_FIXED_PRIORITY` channel (no priority inheritance), hog prio 20, client prio 30 REPLY-blocked; all pinned to CPU0.
- `qnxray --target qnxvm inversions` reports waiter/owner/preempted_by/severity.
- `qnxray --target qnxvm timeline --run /tmp/inversion --match inversion [--json]` runs `tracelogger` (at prio 40r so the hog cannot starve it), copies the .kev and parses host `traceprinter` output. Offline: `--kev file.kev`. Set `QNXRAY_TRACEPRINTER` if it is not on PATH.
- `qnxray --target qnxvm ci [--run BIN]... [--background BIN]... --seconds N --report out.json`: exit 0 clean, 1 crash, 2 inversion, 3 both.
- AI explanations: set `QNXRAY_LLM_KEY` (optional `QNXRAY_LLM_URL`, `QNXRAY_LLM_MODEL`); otherwise offline rules.
- Extension: `cd extension && npm install && npm run package` -> `qnxray-0.1.0.vsix` (bundles the CLI).
  Live integration test: `QNXRAY_TARGET=qnxvm QNXRAY_EXPECT_INVERSION=1 xvfb-run -a node out/test/runTest.js` with the demo running.
- `scripts/smoke_live.sh qnxvm` covers snapshot, agent, ci inversion, timeline, ci crash, crash capture.

## /dev/qnxray resource manager
`agent/qnxray-resmgr.c` (build with `-DQNXRAY_NO_MAIN` together with `qnxray-agent.c`) registers `/dev/qnxray`. Each open() builds a fresh JSON snapshot, and read() streams it. Start it on the target with `sudo -n /tmp/qnxray-resmgr` (it daemonizes; `-n` keeps it in the foreground, `-p PATH` changes the path). Use it with `qnxray --source resmgr ...` or `QNXRAY_SOURCE=resmgr`. Note: the node is mode 0444 and the resmgr runs as root, so any local user can read the process list through it.

Codelab: docs/codelab/README.md
