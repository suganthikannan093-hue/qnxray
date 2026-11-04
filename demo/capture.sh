#!/bin/bash
# Capture REAL live command output from the QNX 8.0 QEMU target for each demo scene.
# Output: demo/raw/scenes/NN.txt  (first line "$ cmd", then output, last line "[exit N, T s]")
cd "$(dirname "$0")/.." ; export PATH=/tmp/bin:$PATH QNXRAY_SOURCE=resmgr
O=demo/raw/scenes; mkdir -p $O
run() { local f=$1; shift; local t0=$(date +%s%N)
  { echo "\$ $*"; bash -c "$*" 2>&1; rc=$?; echo "[exit $rc, $(python3 -c "print(round(($(date +%s%N)-$t0)/1e9,1))") s]"; } > $O/$f.txt; cat $O/$f.txt; }
ssh qnxvm 'sudo -n slay -f inversion' >/dev/null 2>&1
run 01 "ssh qnxvm 'uname -a; sudo -n pidin info | head -2'"
run 02 "ssh qnxvm 'ls -l /dev/qnxray'; qnxray --target qnxvm snapshot | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d[\"source\"],len(d[\"processes\"]),\"processes\",sum(len(p[\"threads\"]) for p in d[\"processes\"]),\"threads\")'"
ssh qnxvm '(sudo -n /tmp/inversion 40 > /tmp/inv.log 2>&1 &)'; sleep 2
run 03 "ssh qnxvm 'sudo -n pidin | grep -e STATE -e inversion'"
run 04 "qnxray --target qnxvm inversions"
run 05 "qnxray --target qnxvm timeline --seconds 1 --match inversion"
ssh qnxvm 'sudo -n slay -f inversion' >/dev/null 2>&1; sleep 1
run 06 "qnxray --target qnxvm ci --background 'build/inversion 15' --seconds 2 >/dev/null; echo exit=\$?"
sleep 14; ssh qnxvm 'sudo -n slay -f inversion' >/dev/null 2>&1
run 07 "qnxray --target qnxvm ci --background 'build/inversion 15 --inherit' --seconds 2 >/dev/null; echo exit=\$?"
sleep 14; ssh qnxvm 'sudo -n slay -f inversion' >/dev/null 2>&1
run 08 "qnxray --target qnxvm ci --run build/crashy >/dev/null; echo exit=\$?"
run 09 "qnxray --target qnxvm explain-crash build/crashy"
run 10 "ssh qnxvm 'sudo -n /tmp/inversion 3 | grep reply'"
run 11 "ssh qnxvm 'sudo -n /tmp/inversion 3 --inherit | grep reply'"
