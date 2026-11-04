#!/usr/bin/env bash
# Installs QNX SDP 8.0 + QEMU quickstart image via qnxsoftwarecenter_clt.
# Credentials come ONLY from an options file (QNX-documented @file form), never argv/history:
#   ~/.qnx/myqnx_options  (chmod 600), 4 lines: -myqnx.user / <email> / -myqnx.password / <password>
set -euo pipefail
CLT=$HOME/qnx/qnxsoftwarecenter/qnxsoftwarecenter_clt
OPT=$HOME/.qnx/myqnx_options
DEST=$HOME/qnx800
[ -f "$OPT" ] || { echo "missing $OPT"; exit 1; }
chmod 600 "$OPT"
"$CLT" @"$OPT" -syncLicenseKeys -activateAll -listLicenseKeys
"$CLT" @"$OPT" -listQuery qnx800 | grep -Ei 'sdp|quickstart|qemu' | head -40   # confirm IDs
"$CLT" @"$OPT" -installBaseline com.qnx.qnx800 -destination "$DEST"
"$CLT" @"$OPT" -destination "$DEST" -installPackage com.qnx.qnx800.quickstart.qemu
ls "$DEST"/images/qemu || true
