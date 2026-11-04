# Demo video storyboard / script

Output: `demo/qnxray_demo.mp4` (1920x1080, 25 fps, H.264 + AAC, ~2:47). Rebuild:
`demo/capture.sh` (real live output from the QNX 8.0 QEMU target -> `demo/raw/scenes/`), record `demo/raw/vscode.mp4`
(`QNXRAY_FIX_SOURCE=$PWD/examples/inversion/main.c QNXRAY_DEMO_HOLD=8 QNXRAY_DEMO_USERDIR=/tmp/vsdemo QNXRAY_SOURCE=resmgr QNXRAY_TARGET=qnxvm QNXRAY_EXPECT_INVERSION=1 node extension/out/test/runTest.js` under `ffmpeg -f x11grab`),
then `python3 demo/render.py`. AI outputs on screen are real model replies captured live (scenes 5, 6, 8, 10, 11); scene 9 is the 'Only QNXray does this' card; scene 10 (`qnxray fix --verify`) is the climax. Narration: **Kokoro-82M** neural TTS (hexgrad/Kokoro-82M, **Apache-2.0** weights; ONNX build via kokoro-onnx, MIT), voice `af_heart`, en-US, speed 1.0; loudness normalized to -16 LUFS (ffmpeg loudnorm). Sample: `demo/voice_sample.wav`. v1 used piper/LJSpeech (public domain). No music, no logos.

| # | Type | Seconds | On-screen caption | Narration |
|---|---|---|---|---|
| 1 | title | 0-11 | The problem | A priority thirty thread asks a server for a half second reply. It waits three point two seconds. Nothing crashed, nothing was logged. |
| 2 | title | 11-26 | QNXray for QNX 8.0 | This is Q N X ray. It detects priority inversions automatically on a live Q N X eight target, gates them in C I, explains the root cause with A I, and verifies the fix. |
| 3 | term | 26-39 | Live target: QNX SDP 8.0 on QEMU, snapshots via our /dev/qnxray resource manager | Everything here is live: Q N X eight on QEMU, over S S H. Our own resource manager, slash dev slash Q N X ray, returns every thread on each read. |
| 4 | term | 39-51 | The bug in raw pidin: server 10 READY, hog 20 RUNNING, client 30 REPLY-blocked | In raw pidin, the bug is hard to see. The client at thirty is reply-blocked, the server at ten is ready, a hog at twenty owns the CPU. |
| 5 | term | 51-72 | Automatic detection + AI root cause from live evidence (chain, thread states, trace) | Q N X ray finds the inversion by itself, captures a kernel trace, and sends that evidence to the model. The A I names the root cause, and the Q N X fix: a fixed-priority channel blocks priority inheritance. |
| 6 | video | 72-86 | VS Code dashboard: live finding, AI root cause, trace timeline | The same engine drives the V S Code dashboard: the live finding, the A I root cause card, and the trace timeline. |
| 7 | term | 86-98 | CI gate: exit 2 = inversion, 0 = clean, 1 = crash; --fix writes the patch | In C I it's a gate. Inversion exits two, clean exits zero, a crash exits one. With dash dash fix, C I also writes the proposed patch. |
| 8 | term | 98-113 | Crash: core collected on target, AI explains the NULL deref with file, line, patch | Crashes too. Q N X ray pulls the core from the target, and the A I explains the null dereference in read sensor, with a patch. |
| 9 | card | 113-125 | Only QNXray does this | Here is what only Q N X ray does: automatic inversion detection, a C I gate, A I root cause from real evidence, and a fix verified on the target. |
| 10 | term | 125-147 | qnxray fix --verify: AI patch → qcc rebuild → rerun on target → 3.20 s → 0.50 s | And the climax. Q N X ray fix, verify. The A I proposes the patch, Q N X ray applies it, rebuilds with Q C C, reruns on the target, and measures: three point two seconds down to half a second. Verified. |
| 11 | video | 147-161 | Fix & verify button in VS Code: the diff and the measured result | One click in V S Code does the same: the diff, and the measured before and after. |
| 12 | title | 161-167 | Built for QNX SDP 8.0 | Q N X ray. Find it, gate it, explain it, and prove the fix. |
