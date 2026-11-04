#!/bin/bash
# Live-target smoke test: build with qcc, deploy, snapshot (pidin + agent), crash capture.
# Prereq: scripts/boot_qemu.sh running and `ssh qnxvm` working (see docs/QEMU_TARGET.md).
set -euo pipefail
T=${QNXRAY_TARGET:-qnxvm}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
source ${QNX_SDP:-/home/box/qnx800}/qnxsdp-env.sh >/dev/null
mkdir -p "$ROOT/build"
qcc -Vgcc_ntox86_64 -g -Wall -o "$ROOT/build/qnxray-agent" "$ROOT/agent/qnxray-agent.c"
qcc -Vgcc_ntox86_64 -g -o "$ROOT/build/crashy" "$ROOT/examples/crashy/main.c"
scp -q "$ROOT/build/qnxray-agent" "$T:/tmp/"
export PYTHONPATH="$ROOT/cli"
q() { python3 -m qnxray --target "$T" "$@"; }
n=$(q snapshot | python3 -c 'import json,sys;print(len(json.load(sys.stdin)["processes"]))')
[ "$n" -gt 10 ] && echo "PASS pidin snapshot: $n processes" || { echo "FAIL pidin snapshot ($n)"; exit 1; }
n=$(QNXRAY_AGENT=/tmp/qnxray-agent q snapshot | python3 -c 'import json,sys;d=json.load(sys.stdin);assert d["source"]=="agent";print(len(d["processes"]))')
[ "$n" -gt 10 ] && echo "PASS agent snapshot: $n processes" || { echo "FAIL agent snapshot"; exit 1; }
q inversions >/dev/null && echo "PASS inversions"
out=$(q explain-crash "$ROOT/build/crashy" --json)
echo "$out" | grep -q '"signal": "SIGSEGV"' && echo "$out" | grep -q read_sensor \
  && echo "PASS crash capture (SIGSEGV in read_sensor)" || { echo "FAIL crash capture"; echo "$out"; exit 1; }
