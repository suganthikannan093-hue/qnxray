# Milestones (all dates IST; hard deadline 16 Dec 2026 00:30 IST - target submit 14 Dec)
| # | Dates | Deliverable |
|---|---|---|
| M0 | 4 Nov | Rules read, scaffold, mock mode, tests (DONE) |
| M1 | 5-8 Nov | User approves sign-ups; myQNX account + licence; install QSC, SDP 8.0, QEMU QSTI on box (Ubuntu-type host, QEMU>=8; check KVM) ; Devpost join |
| M2 | 8-14 Nov | Real target: `mkqnximage --run`, ssh backend vs real pidin output, fix parser with captured fixtures; qcc build+deploy of examples/crashy; attend 10 Nov VS Code build session (9:30 PM IST) |
| M3 | 14-24 Nov | qnxray-agent compiled with qcc, resource manager /dev/qnxray; tracelogger capture + .kev parsing (traceparser lib) for real context-switch timeline; priority-inversion detector on a priority-inversion demo app |
| M4 | 24 Nov-2 Dec | AI explainer on real dumper cores (+ gdb backtrace via ntox86_64-gdb); polished webview (timeline, CPU lanes, findings panel); CI mode exit codes; packaged .vsix |
| M5 | 2-7 Dec | Codelab: "Find a priority inversion on QNX 8.0 in QEMU with tracelogger" (standalone tutorial, GitHub Pages) |
| M6 | 7-11 Dec | Demo video <3 min (screen-record on box: real QEMU target, live dashboard, inversion found, crash explained), upload YouTube |
| M7 | 11-14 Dec | README with QNX-evidence section pointing to files/output, Devpost text, submit; buffer 15 Dec |
