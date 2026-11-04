# AI explainer and fix & verify

QNXray explains crashes and priority inversions with any OpenAI-compatible chat-completions API, and can turn
the explanation into a patch that it rebuilds and verifies on the target. Everything works without a key
(rule-based offline mode), so CI never depends on the network.

## Configuration
| Variable | Default | Purpose |
|---|---|---|
| `QNXRAY_LLM_KEY` | – | API key; falls back to `OPENAI_API_KEY`. Read from the environment only. |
| `QNXRAY_LLM_URL` | `https://api.openai.com/v1/chat/completions` | Any OpenAI-compatible endpoint (hosted or local) |
| `QNXRAY_LLM_MODEL` | `gpt-5.4-mini` | Model name (VS Code: `qnxray.llmModel`) |
| `QNXRAY_LLM_TIMEOUT` | `90` | Request timeout in seconds |
| `QNXRAY_LLM=off` | – | Force offline mode even if a key is set |

```bash
export QNXRAY_LLM_KEY=...            # never put it in settings.json, scripts or the repo
qnxray --target qnxvm inversions --explain --trace
qnxray --target qnxvm explain-crash build/crashy
```

## What is sent (data & privacy)
| Use | Evidence |
|---|---|
| Crash | binary path, signal + description, PC, backtrace, exit code, last 800 bytes of stderr, core path, ±6 source lines around the faulting line (if the source is found on the host) |
| Inversion | waiter, prio and state; blocker name/pid, max prio and states; preempting threads; severity; thread table of the processes in the chain; with `--trace` up to 8 timeline entries |
| Fix | the inversion evidence above **plus the full text of the source file** being fixed |

Before sending, `redact()` removes dictionary fields whose name contains *key/token/secret/password* and replaces
strings matching `sk-…`, `Bearer …`, `api_key=…`, `token=…`, `password=…`, `secret=…` with `[REDACTED]`
(`cli/qnxray/explain.py`, tested in `cli/tests/test_ai.py`). The key is sent only in the `Authorization` header and is
never written to reports, settings, logs or fixtures. Review your provider's data-retention policy before sending
proprietary source; use `QNXRAY_LLM_URL` to point at a self-hosted model if needed.

## Output contract
The model must return one JSON object:
```json
{ "summary": "...", "root_cause": "...", "evidence": ["..."], "qnx_fix": "...", "patch": "...", "confidence": "high|medium|low" }
```
QNXray validates types, requires `summary`, `root_cause` and `qnx_fix`, truncates long fields (evidence ≤ 6 items),
and adds `mode` (`ai`/`offline`), `model` and a formatted `text`. Any failure (no key, HTTP/network error, invalid
JSON) returns the offline explanation with `ai_error` set. The explanation appears in `inversions` (JSON
`explanation` or `--explain`), `explain-crash`, every finding in the `ci` report, and the dashboard's
**AI root cause** card.

Real captured outputs (gpt-5.4-mini, live QNX 8.0 target): `examples/fixtures/ai_crash.json`,
`ai_inversion.json`, `ai_inversion.txt`.

## Fix & verify
```bash
qnxray --target qnxvm fix examples/inversion/main.c --verify [--args 3] [--patch-out fix.patch] [--json]
```
1. **Build** the original with `qcc -V$QNXRAY_QCC_VARIANT` → `build/fix/<name>_before`, deploy to `/tmp/<name>_before`, run it.
2. **Detect** the inversion in live snapshots.
3. **Propose**: the AI returns `{qnx_fix, rationale, edits:[{find, replace}]}` (max 3 edits). Safety checks: each
   `find` must occur in the source **exactly once**, and the patched source must pass `lint()` (no
   `ChannelCreate(...)` that can still pass `_NTO_CHF_FIXED_PRIORITY`). Otherwise the offline rule
   (`ChannelCreate(0)`) is used and `ai_error` is recorded.
4. **Diff**: unified diff with repo-relative `a/`/`b/` paths (printed; written to `--patch-out`).
5. **Rebuild** the patched copy (`build/fix/<file>`; your source is never modified) → `/tmp/<name>_fixed`.
6. **Verify**: run both versions, parse the client's `reply after X s`, rescan for inversions →
   `status: verified` when the latency improved and no inversion remains, else `not-verified`.

Without `--verify` it stops after step 4 (`status: patch-proposed`). If no inversion is seen in step 2 the status is `no-inversion`. Exit code 0 for `verified`/`patch-proposed`, otherwise 1.
Latency measurement currently targets programs that print `reply after <seconds>s` like `examples/inversion`.

Real run (`examples/fixtures/ai_fix_verify.txt`): **client reply 3.20 s → 0.50 s; inversion after fix: none → VERIFIED.**

In CI, `qnxray ci --fix SOURCE --fix-out qnxray-fix.patch` proposes (does not verify) the patch for the first
inversion and stores it in the report under `fix`. In VS Code: the **Fix & verify** button / command.
