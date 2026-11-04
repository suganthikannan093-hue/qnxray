# Demo video storyboard / script

Output: `demo/qnxray_demo.mp4` (1920x1080, 25 fps, H.264 + AAC, ~2:34). Rebuild:
`demo/capture.sh` (real live output from the QNX 8.0 QEMU target -> `demo/raw/scenes/`), record `demo/raw/vscode.mp4`
(`QNXRAY_DEMO_HOLD=10 QNXRAY_DEMO_USERDIR=/tmp/vsdemo QNXRAY_SOURCE=resmgr QNXRAY_TARGET=qnxvm QNXRAY_EXPECT_INVERSION=1 node extension/out/test/runTest.js` under `ffmpeg -f x11grab`),
then `python3 demo/render.py`. Narration: **Kokoro-82M** neural TTS (hexgrad/Kokoro-82M, **Apache-2.0** weights; ONNX build via kokoro-onnx, MIT), voice `af_heart`, en-US, speed 1.0; loudness normalized to -16 LUFS (ffmpeg loudnorm). Sample: `demo/voice_sample.wav`. v1 used piper/LJSpeech (public domain). No music, no logos.

| # | Type | Seconds | On-screen caption | Narration |
|---|---|---|---|---|
| 1 | title | 0-15 | The problem | A priority thirty thread asks a server for a half second reply. It waits three point two seconds. Nothing crashed, nothing was logged. On a real-time system, that is a bug you can't see. |
| 2 | title | 15-30 | QNXray | This is Q N X ray: a developer tool that finds priority inversions and crashes on a live Q N X eight target, and explains them, in the terminal, in V S Code, and in C I. |
| 3 | term | 30-39 | Live target: QNX SDP 8.0 on QEMU x86_64, over SSH | Everything you'll see is live. This is Q N X eight point oh, running in QEMU, reached over S S H. |
| 4 | term | 39-53 | Snapshot via /dev/qnxray — our own QNX resource manager | Q N X ray ships its own resource manager. It registers slash dev slash Q N X ray, and every read returns a fresh snapshot of every process and thread. |
| 5 | term | 53-65 | The bug: server 10 READY, hog 20 RUNNING, client 30 REPLY-blocked | Here is the bug in raw pidin. The client at priority thirty is reply-blocked on a server at priority ten, and a priority twenty hog owns the CPU. |
| 6 | term | 65-77 | Wow: QNXray names the inversion — waiter, owner, and who preempts it | Q N X ray follows the message passing chain and names it: the waiter, the server it is blocked on, and the exact thread preempting that server. |
| 7 | term | 77-89 | tracelogger → traceprinter → per-thread timeline | Then it proves it with the kernel tracer. One second of tracelogger: the hog runs the whole time, the server is ready but starved, the client waits in reply. |
| 8 | video | 89-113 | VS Code dashboard: live findings, CPU lanes, trace timeline | The same engine drives a V S Code dashboard. Live findings at the top, what each CPU is running, and the trace timeline, one click away. |
| 9 | term | 113-125 | CI gate: exit 2 = inversion, 0 = clean, 1 = crash | And in C I, it is a gate. Inversion exits two. The fixed build exits zero. A crashing binary exits one, with a JSON report. |
| 10 | term | 125-136 | Crash explained: SIGSEGV, NULL deref in read_sensor, file and line | When something crashes, Q N X ray collects the core and explains it: a null pointer dereference in read sensor, with the file and line. |
| 11 | term | 136-149 | The fix: priority inheritance — 3.20 s → 0.50 s | The fix is one Q N X feature: priority inheritance. Same program, with inherit on. The reply drops from three point two seconds to half a second. |
| 12 | title | 149-156 | Built for QNX SDP 8.0 | Q N X ray. See the invisible real-time bugs, before they ship. |
