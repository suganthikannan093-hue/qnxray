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
