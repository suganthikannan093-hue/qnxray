# Compliance checklist - QNX Global Hackathon (re-read 2026-11-04 IST from qnx.devpost.com/rules + docs/RULES_NOTES.md)

Legend: **Met** = satisfied in this repo now. **Gap** = still to do (owner listed). Deadline: 15 Dec 2026 2:00 PM ET = **16 Dec 2026 12:30 AM IST**.

| # | Requirement (rules) | Status | Evidence / action |
|---|---|---|---|
| 1 | Category: one category selected - **Developer Tooling & Host Tools** (tools that build/test/analyze/debug software for QNX, host or target) | Met | Host CLI (`cli/`), VS Code extension (`extension/`), on-target agent + resmgr (`agent/`); select this category on the form |
| 2 | Required tech: genuinely builds for / runs on **QNX 8.0** (not just named) | Met | `qcc -Vgcc_ntox86_64` builds of `agent/*.c`, `examples/*`; live target `uname`: `QNX 8.0.0 x86_64` (`demo/raw/scenes/01.txt`); `scripts/smoke_live.sh` 8/8 PASS |
| 3 | Build/run instructions naming QNX version, target (HW or QEMU), toolchain | Met (fixed) | `README.md` "Requirements" + "Build and run on QNX 8.0" (SDP 8.0, QEMU x86_64, `qcc -Vgcc_ntox86_64`); `docs/QEMU_TARGET.md`. README previously said "not yet tested on QNX" - corrected |
| 4 | Evidence of QNX use - identify files/functions/output | Met (fixed) | README "Evidence of QNX use"; `docs/SUBMISSION.md` draft lists files, functions (`resmgr_attach`, `devctl(DCMD_PROC_TIDSTATUS)`, `ChannelCreate(_NTO_CHF_FIXED_PRIORITY)`, `MsgSend`, `tracelogger`) and captured output |
| 5 | Public repo on GitHub/GitLab/Bitbucket with all source + instructions | **Gap** | Repo exists but is **private** by owner decision. Make public at submission time **with owner approval** |
| 6 | OSI licence file, detectable in the repo "About" section | Met / **Gap** | `LICENSE` = MIT (GitHub detects it). Visible in About only once the repo is public (#5) |
| 7 | Text description of features/functionality | **Gap** (draft ready) | `docs/SUBMISSION.md` draft; owner pastes into Devpost |
| 8 | Video < 3 minutes | Met | `demo/qnxray_demo.mp4` 2:34, 1920x1080 H.264/AAC MP4 |
| 9 | Video shows project functioning on the device it was built for | Met | All terminal scenes are real captured output from the live QNX 8.0 QEMU target (`demo/capture.sh` -> `demo/raw/scenes/*.txt`); VS Code scene is a real screen recording against the live target |
| 10 | Video uploaded publicly to YouTube, link on form | **Gap** | Owner uploads (not uploaded by the bot, per instruction) |
| 11 | Video: no third-party trademarks / copyrighted music or material without permission | Met (note) | No music; narration = Kokoro-82M TTS voice af_heart (Apache-2.0); no logos. Product names (QNX, VS Code) appear only as text naming what the tool targets (nominative use); VS Code UI is visible in the dashboard scene |
| 12 | English | Met | All docs, UI, narration in English |
| 13 | New work within 2 Nov - 15 Dec 2026 | Met | First commit 2026-11-04 (git history); codelab written 2026-11-04 |
| 14 | Original work; OSS deps only under their licences; enhances them | Met | Own code; deps: Python stdlib, VS Code extension API / `@vscode/test-electron` (MIT), TypeScript (Apache-2.0). `.vscode-test/` and `node_modules/` gitignored; QNX SDP not redistributed (only used under the non-commercial licence) |
| 15 | Third-party APIs/SDKs used with authorization | Met (note) | Optional AI explainer calls an LLM API only if the user sets `QNXRAY_LLM_KEY` (env only, never stored); default is offline rules. User must follow the provider's terms |
| 16 | Free access for judges to test | Met once #5 | MIT, mock mode needs no QNX; live mode needs SDP 8.0 + QEMU (documented) |
| 17 | Eligibility: 18+, not in an excluded country, not an employee/agent/family of the Sponsor/Administrator/judges, no conflict of interest | **Gap - owner self-attests** | Cannot be verified by code; owner confirms on the form |
| 18 | No financial/preferential support or commercial licence from the Sponsor/Administrator | **Gap - owner self-attests** | Built with the free non-commercial QNX Everywhere licence |
| 19 | Bonus: Best Codelab/Tutorial - URL of a codelab authored in the period teaching a QNX 8.0 task | Met / **Gap (URL)** | `docs/codelab/README.md` (write a QNX 8.0 resource manager, `/dev/qnxray`); needs a public URL (public repo link or a separate post) |
| 20 | Bonus: Best Use of QNX-specific Tech (message passing, resource managers, microkernel, real-time services) | Met | Resource manager `agent/qnxray-resmgr.c`; message-passing chain analysis `cli/qnxray/analyze.py`; priority inheritance fix `examples/inversion` (`_NTO_CHF_FIXED_PRIORITY`); kernel trace via `tracelogger` |
| 21 | Judging: Technological Implementation / Design / Potential Impact / Innovation & AI Creativity | Addressed | Live target + resmgr + traces (impl.); CLI/IDE/CI surfaces (design); real-time bug class invisible to debuggers (impact); AI crash explainer with offline fallback (AI) |

## Gaps that need the owner (cannot be fixed in code)
1. Approve making the repo public (then check the MIT licence shows in About).
2. Upload `demo/qnxray_demo.mp4` to YouTube (public) and paste the link.
3. Paste `docs/SUBMISSION.md` into Devpost, choose Developer Tooling & Host Tools, add the codelab URL.
4. Self-attest eligibility and no Sponsor support.

## AI explainer data handling
- Optional; enabled only when `QNXRAY_LLM_KEY` / `OPENAI_API_KEY` is set in the environment (`QNXRAY_LLM=off` disables it). The key is never written to files, settings, logs or the repo.
- Sends only structured debugging evidence (signal, backtrace, a few source lines, thread states/priorities, inversion chain, trace timeline) to the configured OpenAI-compatible endpoint (`QNXRAY_LLM_URL`, model `QNXRAY_LLM_MODEL`, default `gpt-5.4-mini`); key/token-like strings are redacted first.
- Replies are JSON-schema checked; patches are applied only to a copy under `build/fix/` after exact-match and lint checks. Offline rules are used when the key is absent or the reply is invalid.
- Fixtures in `examples/fixtures/ai_*` are real captured replies from the demo programs (no personal data, no secrets).
