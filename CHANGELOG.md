# Changelog

All notable changes. Format based on [Keep a Changelog](https://keepachangelog.com/); versions follow SemVer.

## [0.1.0] - 2026-11-05
### Added
- CLI: `snapshot`, `watch`, `inversions` (`--trace`, `--explain`), `timeline` (tracelogger → traceprinter), `explain-crash` (dumper core + gdb), `build`, `ci` gate with JSON report and exit codes 0/1/2/3.
- `fix --verify`: AI-proposed patch, `qcc` rebuild, rerun on target, measured before/after latency and rescan; `ci --fix` writes a patch.
- AI explainer for inversions and crashes (OpenAI-compatible, redacted evidence, validated JSON, offline fallback).
- `/dev/qnxray` resource manager and `qnxray-agent` (`DCMD_PROC_INFO` / `DCMD_PROC_TIDSTATUS`).
- VS Code extension: live scheduling dashboard, AI root-cause and Fix & verify cards, trace timeline, CI gate.
- Mock target, 15 unit tests, live smoke test, examples and fixtures from QNX 8.0 on QEMU.
- Documentation: README, getting started (QEMU + Raspberry Pi 4 notes), architecture, CLI, VS Code, CI, AI, codelab.
- `QNXRAY_QCC_VARIANT` to select the `qcc` target (e.g. `gcc_ntoaarch64le`).

### Fixed
- Process names were shown as `tmp/inversion_before` (pidin truncated the path column); now read with `pidin -F` as clean basenames.
- `fix`/`ci --fix` diff headers contained absolute paths (`a//workspace/...`); now repo-relative.
- Dashboard CPU lanes rendered a literal `<br>`.
