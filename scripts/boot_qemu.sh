#!/bin/bash
# Boot the QNX SDP 8.0 QEMU quickstart image headless.
# SSH: ssh -p 2222 qnxuser@localhost   (serial log: $VMDIR/qemu.out)
set -e
IMG=${QNX_QEMU_IMG:-/home/box/qnx800/images/qemu/qemu/output}
VMDIR=${VMDIR:-/home/box/qnxvm}
PORT=${QNX_SSH_PORT:-2222}
mkdir -p "$VMDIR"
# copy-on-write overlay so the 50 GB base disk is never modified
[ -f "$VMDIR/overlay.qcow2" ] || qemu-img create -f qcow2 -F vmdk -b "$IMG/disk-qemu.vmdk" "$VMDIR/overlay.qcow2" >/dev/null
# KVM hangs on this host (nested virt); default to TCG. Set QNX_KVM=1 to try KVM.
KVM="-cpu max"
if [ "$QNX_KVM" = 1 ] && sg pulse-access -c 'test -w /dev/kvm'; then KVM="-enable-kvm -cpu host"; fi
CMD="qemu-system-x86_64 $KVM -smp 4 -m 4G \
 -drive file=$VMDIR/overlay.qcow2,if=ide,id=drv0 \
 -netdev user,id=net0,hostfwd=tcp:127.0.0.1:$PORT-:22 -device virtio-net-pci,netdev=net0,mac=52:54:00:cf:bf:ed \
 -object rng-random,filename=/dev/urandom,id=rng0 -device virtio-rng-pci,rng=rng0 \
 -kernel $IMG/ifs.bin -display none -serial file:$VMDIR/qemu.out -monitor unix:$VMDIR/mon.sock,server,nowait \
 -pidfile $VMDIR/qemu.pid -daemonize"
sg pulse-access -c "$CMD" </dev/null >/dev/null 2>&1
echo "QNX VM started (pid $(cat $VMDIR/qemu.pid)); ssh -p $PORT qnxuser@localhost"
