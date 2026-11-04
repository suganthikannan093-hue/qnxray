# QNXray - an X-ray for QNX 8.0 scheduling

> VS Code extension + host CLI that builds QNX 8.0 apps, deploys them to a QEMU QNX target,
> shows live process/thread scheduling, flags priority inversions, and explains crashes with AI.

**Status:** pre-alpha scaffold. Mock mode works; real-target backends are written against QNX 8.0 docs but **not yet tested on QNX**.

## Quick start (mock, no QNX needed)
```bash
cd cli && python3 -m unittest discover -s tests
python3 -m qnxray.cli --target mock watch --count 3
python3 -m qnxray.cli inversions
cd ../extension && npm install && npx tsc -p .   # then F5 in VS Code
```
## Real target (planned)
- QNX SDP 8.0 (QNX Everywhere non-commercial licence), host Ubuntu, target QEMU x86_64 QSTI
- `source ~/qnx800/qnxsdp-env.sh && mkqnximage --run`, then `qnxray --target $(mkqnximage --getip) watch`
- Toolchain: `qcc -Vgcc_ntox86_64`

## Evidence of QNX use
- `agent/qnxray-agent.c` - /proc + devctl(DCMD_PROC_INFO, DCMD_PROC_TIDSTATUS)
- `cli/qnxray/pidin.py`, `target.py` - pidin parsing, tracelogger capture
- see docs/ARCHITECTURE.md

## Licence
MIT
