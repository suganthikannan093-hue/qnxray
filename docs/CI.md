# CI gate

`qnxray ci` runs headless over ssh and turns real-time bugs into a failing build.

```bash
qnxray --target qnxvm ci \
  --background 'build/inversion 15' \   # workload that must not invert (started as root)
  --run build/crashy \                  # binary that must not crash
  --seconds 5 --report qnxray-report.json \
  --fix examples/inversion/main.c --fix-out qnxray-fix.patch
```

## Exit codes
| Code | Meaning |
|---|---|
| `0` | pass: no crash, no inversion |
| `1` | a `--run` binary crashed |
| `2` | at least one priority inversion was observed during `--seconds` |
| `3` | crash and inversion |

## Report (`--report` and stdout)
```json
{ "target": "qnxvm", "time": 1793000000.0, "snapshots": 6,
  "crashes":    [{ "binary": "...", "signal": "SIGSEGV", "backtrace": [...], "explanation": {...} }],
  "inversions": [{ "waiter": "...", "owner": "...", "preempted_by": [...], "severity": "high", "explanation": {...} }],
  "fix": { "mode": "ai", "qnx_fix": "...", "edits": [...], "patch": "--- a/...", "patch_file": "qnxray-fix.patch" },
  "exit_code": 2, "status": "fail" }
```
`explanation` has `mode` (`ai` or `offline`), `summary`, `root_cause`, `evidence`, `qnx_fix`, `patch`, `confidence`
(and `ai_error` if the AI call failed and offline rules were used). `fix` is present only with `--fix` and an inversion.

## GitHub Actions (self-hosted runner with SDP + target access)
```yaml
jobs:
  qnxray:
    runs-on: [self-hosted, qnx]
    steps:
      - uses: actions/checkout@v4
      - name: Build and gate
        env:
          QNXRAY_TARGET: qnxvm
          QNXRAY_LLM_KEY: ${{ secrets.QNXRAY_LLM_KEY }}   # optional
        run: |
          source ~/qnx800/qnxsdp-env.sh
          export PYTHONPATH=$PWD/cli
          mkdir -p build && qcc -Vgcc_ntox86_64 -g -o build/app examples/inversion/main.c
          python3 -m qnxray ci --background 'build/app 15' --seconds 5 \
            --report qnxray-report.json --fix examples/inversion/main.c
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: qnxray, path: "qnxray-report.json\nqnxray-fix.patch" }
```
Without a key the gate still works (offline explanations). The step fails with the exit code above.

## GitLab CI
```yaml
qnxray:
  tags: [qnx]
  script:
    - source ~/qnx800/qnxsdp-env.sh && export PYTHONPATH=$PWD/cli
    - python3 -m qnxray --target qnxvm ci --background 'build/app 15' --report qnxray-report.json
  artifacts: { when: always, paths: [qnxray-report.json] }
```

Live example (from `demo/capture.sh`): the buggy demo exits `2`, the same program with `--inherit` exits `0`,
`build/crashy` exits `1`.
