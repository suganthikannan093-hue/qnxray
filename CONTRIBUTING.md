# Contributing

Thanks for helping. QNXray is small on purpose: stdlib-only Python, one C agent/resmgr, one VS Code extension.

## Setup
```bash
export PYTHONPATH=$PWD/cli                          # after sourcing qnxsdp-env.sh, if you use QNX
cd cli && QNXRAY_LLM=off python3 -m unittest discover -s tests   # must stay green, offline, no target needed
```
Live target (optional): see [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md), then `QNXRAY_TARGET=qnxvm scripts/smoke_live.sh`.

Extension:
```bash
cd extension && npm install
node scripts/bundle-cli.js && npx tsc -p .           # bundle the CLI + typecheck
node out/test/runTest.js                              # VS Code integration test (mock target)
```

## Guidelines
- Python 3.9+ compatible, standard library only (no f-strings that need 3.12 quote rules).
- New detection logic needs a unit test using `MockTarget` or a fixture in `examples/fixtures/` captured from a real QNX 8.0 target.
- Cite the QNX 8.0 doc page for any new target-side interface.
- AI changes: keep the output contract and the offline fallback; never send more than the documented data ([docs/AI.md](docs/AI.md)).
- **Never commit API keys, credentials, cores from real products, or personal data.** Keys come from the environment only.
- Commits: short imperative subject (`fix: ...`, `docs: ...`, `feat: ...`), body explains why. Update [CHANGELOG.md](CHANGELOG.md).

## Pull requests
Describe the change, how you tested it (mock and/or live), and attach before/after output for behaviour changes.
