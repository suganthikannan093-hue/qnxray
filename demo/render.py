#!/usr/bin/env python3
"""Render demo/qnxray_demo.mp4 from REAL captured output (demo/raw/scenes/*.txt, from capture.sh)
and the real VS Code screen recording (demo/raw/vscode.mp4). Narration: Kokoro-82M TTS, voice af_heart (Apache-2.0).
No music. Usage: python3 demo/render.py"""
import os, re, subprocess, wave, json
from PIL import Image, ImageDraw, ImageFont
D = os.path.dirname(os.path.abspath(__file__)); RAW = f"{D}/raw"; B = f"{RAW}/build"; os.makedirs(B, exist_ok=True)
W, H, FPS = 1920, 1080, 25
VOICE = os.environ.get("PIPER_VOICE", "/home/box/piper/en_US-ljspeech-high.onnx")
F = "/usr/share/fonts/truetype/dejavu/"
font = lambda n, s: ImageFont.truetype(F + n, s)
BG, FG, ACC, DIM, RED, GRN = (13, 17, 23), (230, 237, 243), (88, 166, 255), (139, 148, 158), (248, 81, 73), (63, 185, 80)

def scene_txt(*ids):
    return "\n".join(open(f"{RAW}/scenes/{i}.txt").read().rstrip() for i in ids)

# (kind, payload, caption, narration)
SCENES = [
 ("title", ("A priority-30 thread asked for a 0.5 s reply.", "It waited 3.2 s. Nothing crashed. Nothing logged."),
  "The problem", "A priority thirty thread asks a server for a half second reply. It waits three point two seconds. Nothing crashed, nothing was logged."),
 ("title", ("QNXray", "Automatic inversion detection · CI gating · AI root cause · verified fixes"),
  "QNXray for QNX 8.0", "This is Q N X ray. It detects priority inversions automatically on a live Q N X eight target, gates them in C I, explains the root cause with A I, and verifies the fix."),
 ("term", scene_txt("01", "02"), "Live target: QNX SDP 8.0 on QEMU, snapshots via our /dev/qnxray resource manager",
  "Everything here is live: Q N X eight on QEMU, over S S H. Our own resource manager, slash dev slash Q N X ray, returns every thread on each read."),
 ("term", scene_txt("03"), "The bug in raw pidin: server 10 READY, hog 20 RUNNING, client 30 REPLY-blocked",
  "In raw pidin, the bug is hard to see. The client at thirty is reply-blocked, the server at ten is ready, a hog at twenty owns the CPU."),
 ("term", scene_txt("04"), "Automatic detection + AI root cause from live evidence (chain, thread states, trace)",
  "Q N X ray finds the inversion by itself, captures a kernel trace, and sends that evidence to the model. The A I names the root cause, and the Q N X fix: a fixed-priority channel blocks priority inheritance."),
 ("video", (5, 40), "VS Code dashboard: live finding, AI root cause, trace timeline",
  "The same engine drives the V S Code dashboard: the live finding, the A I root cause card, and the trace timeline."),
 ("term", scene_txt("06", "07", "08", "12"), "CI gate: exit 2 = inversion, 0 = clean, 1 = crash; --fix writes the patch",
  "In C I it's a gate. Inversion exits two, clean exits zero, a crash exits one. With dash dash fix, C I also writes the proposed patch."),
 ("term", scene_txt("09"), "Crash: core collected on target, AI explains the NULL deref with file, line, patch",
  "Crashes too. Q N X ray pulls the core from the target, and the A I explains the null dereference in read sensor, with a patch."),
 ("card", [("Finds priority inversions automatically", "follows the MsgSend / REPLY chain on a live target — no manual trace reading"),
           ("Fails the CI build on an inversion", "exit codes + JSON report, headless, over SSH"),
           ("AI root cause from real QNX evidence", "backtrace, source, thread states, tracelogger timeline"),
           ("Fix & verify on the target", "patch → qcc rebuild → rerun → measured before / after")],
  "Only QNXray does this", "Here is what only Q N X ray does: automatic inversion detection, a C I gate, A I root cause from real evidence, and a fix verified on the target."),
 ("term", scene_txt("10"), "qnxray fix --verify: AI patch → qcc rebuild → rerun on target → 3.20 s → 0.50 s",
  "And the climax. Q N X ray fix, verify. The A I proposes the patch, Q N X ray applies it, rebuilds with Q C C, reruns on the target, and measures: three point two seconds down to half a second. Verified."),
 ("video", (40, 67), "Fix & verify button in VS Code: the diff and the measured result",
  "One click in V S Code does the same: the diff, and the measured before and after."),
 ("title", ("QNXray", "detect · gate · explain · fix & verify — on a live QNX 8.0 target"),
  "Built for QNX SDP 8.0", "Q N X ray. Find it, gate it, explain it, and prove the fix."),
]

_K = None
def tts(i, text):
    """Kokoro-82M (Apache-2.0), voice af_heart. Model files: github.com/thewh1teagle/kokoro-onnx releases (KOKORO_DIR)."""
    global _K
    from kokoro_onnx import Kokoro; import soundfile as sf
    kd = os.environ.get("KOKORO_DIR", "/home/box/kokoro")
    _K = _K or Kokoro(f"{kd}/kokoro-v1.0.onnx", f"{kd}/voices-v1.0.bin")
    a, sr = _K.create(text, voice=os.environ.get("KOKORO_VOICE", "af_heart"), speed=1.0, lang="en-us")
    out = f"{B}/n{i:02}.wav"; sf.write(out, a, sr); return out, len(a) / sr

def caption(img, text, n):
    d = ImageDraw.Draw(img); d.rectangle([0, H - 110, W, H], fill=(0, 0, 0))
    d.text((60, H - 80), text, font=font("DejaVuSans-Bold.ttf", 34), fill=FG)
    d.text((W - 230, H - 72), f"{n}/{len(SCENES)}  QNXray", font=font("DejaVuSans.ttf", 26), fill=DIM)

def title_frame(a, b, cap, n):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    big = font("DejaVuSans-Bold.ttf", 110 if len(a) < 12 else 64)
    d.text((W // 2, 400), a, font=big, fill=ACC if len(a) < 12 else FG, anchor="mm")
    d.text((W // 2, 540), b, font=font("DejaVuSans.ttf", 46 if len(b) < 60 else 36), fill=RED if "3.2" in b else DIM, anchor="mm")
    caption(img, cap, n); return img

def card_frame(lines, cap, n):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    d.text((W // 2, 170), "Only QNXray does this", font=font("DejaVuSans-Bold.ttf", 80), fill=ACC, anchor="mm")
    for k, (head, sub) in enumerate(lines):
        y = 330 + k * 150
        d.text((260, y), "✓", font=font("DejaVuSans-Bold.ttf", 60), fill=GRN, anchor="lm")
        d.text((350, y - 22), head, font=font("DejaVuSans-Bold.ttf", 46), fill=FG, anchor="lm")
        d.text((350, y + 30), sub, font=font("DejaVuSans.ttf", 30), fill=DIM, anchor="lm")
    caption(img, cap, n); return img

def color(line):
    if line.startswith("$"): return ACC
    if re.match(r"\+(?!\+\+)", line) or "VERIFIED" in line or line.startswith("AI root cause") or line.startswith("[3/5]"): return GRN
    if re.match(r"-(?!--)", line): return RED
    if re.search(r"exit=2|REPLY|inversion\b.*3\.20|priority inversion|SEGV|NULL|\"severity\"", line): return RED
    if re.search(r"exit=0|OK, server|RUNNING|#{5}", line): return GRN
    if line.startswith("[exit"): return DIM
    return FG

def term_frames(txt, cap, n, dur):
    import textwrap
    lines = txt.splitlines()
    for size in range(34, 13, -1):   # largest mono size whose word-wrapped text fits the terminal box
        maxc = int((W - 160) / (0.602 * size)); wrapped = []; colors = []
        for l in lines:
            ind = len(l) - len(l.lstrip())
            parts = (textwrap.wrap(l, maxc, subsequent_indent=" " * (ind + 2)) or [""]) if len(l) > maxc else [l]
            c = FG if len(l) > 110 and not l.startswith(("[5/5]", "$")) else color(l)   # AI prose stays neutral
            wrapped += parts; colors += [c] * len(parts)
        if int(size * 1.35) * len(wrapped) <= H - 290: break
    mono = font("DejaVuSansMono.ttf", size)
    lh = int(size * 1.35); top = max(110, (H - 110 - lh * len(wrapped)) // 2 - 20)
    cmds = [i for i, l in enumerate(wrapped) if l.startswith("$")]
    # timeline: each command types for 0.8 s, then its output appears; spread commands over the first 60% of dur
    slot = dur * 0.6 / max(1, len(cmds)); total = int(dur * FPS)
    def draw(t):
        img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
        d.rounded_rectangle([50, 40, W - 50, H - 130], 14, fill=(22, 27, 34), outline=(48, 54, 61))
        d.text((80, 58), "host$ ~/qnxray   (live session against QNX 8.0 target qnxvm)", font=font("DejaVuSans.ttf", 22), fill=DIM)
        for k, ci in enumerate(cmds):
            t0 = k * slot; end = cmds[k + 1] if k + 1 < len(cmds) else len(wrapped)
            if t < t0: break
            frac = min(1, (t - t0) / 0.8); c = wrapped[ci]
            d.text((80, top + ci * lh), c[:max(2, int(len(c) * frac))], font=mono, fill=ACC)
            if frac >= 1:
                for j in range(ci + 1, end):
                    d.text((80, top + j * lh), wrapped[j], font=mono, fill=colors[j])
        caption(img, cap, n); return img
    prev = None
    for f in range(total):
        t = f / FPS; key = tuple(min(1, max(0, (t - k * slot) / 0.8)) for k in range(len(cmds)))
        if key != prev: cur = draw(t).tobytes(); prev = key
        yield cur

def encode(i, frames=None, still=None, dur=0, audio=None, video=None):
    out = f"{B}/s{i:02}.mp4"; a = ["-i", audio, "-af", f"apad=whole_dur={dur}", "-c:a", "aac", "-b:a", "160k", "-ar", "48000"]
    v = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), "-t", f"{dur:.2f}"]
    if video:
        s, e = SCENES[i][1]; cap, n = SCENES[i][2], i + 1
        bar = f"{B}/cap{i:02}.png"; img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); caption(img, cap, n); img.save(bar)
        speed = (e - s) / dur
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(s), "-t", str(e - s), "-i", video, "-i", bar, *a[:1], audio,
            "-filter_complex", f"[0:v]setpts=PTS/{speed:.4f},scale={W}:{H}[v];[v][1:v]overlay[o]", "-map", "[o]", "-map", "2:a",
            "-af", f"apad=whole_dur={dur}", "-c:a", "aac", "-ar", "48000", *v, out], check=True)
        return out
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-", *a, *v, out], stdin=subprocess.PIPE)
    for fr in frames: p.stdin.write(fr)
    p.stdin.close(); assert p.wait() == 0; return out

parts, script = [], []
for i, (kind, payload, cap, narr) in enumerate(SCENES):
    wav, sec = tts(i, narr); dur = round(sec + 2.5 + (4 if kind == "term" and "AI" in cap else 0), 2)
    if kind == "video": dur = max(dur, 14)
    if kind == "card": dur = max(dur, 10)
    if kind in ("title", "card"):
        img = (title_frame(*payload, cap, i + 1) if kind == "title" else card_frame(payload, cap, i + 1)).tobytes()
        frames = (img for _ in range(int(dur * FPS)))
    elif kind == "term": frames = term_frames(payload, cap, i + 1, dur)
    parts.append(encode(i, frames if kind != "video" else None, dur=dur, audio=wav, video=f"{RAW}/vscode.mp4" if kind == "video" else None) if kind == "video"
                 else encode(i, frames, dur=dur, audio=wav))
    script.append((i + 1, kind, cap, narr, dur)); print(f"scene {i+1}: {dur:.1f}s {cap}")
open(f"{B}/list.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{B}/list.txt", "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", f"{D}/qnxray_demo.mp4"], check=True)
print("total", sum(s[4] for s in script)); json.dump(script, open(f"{B}/timing.json", "w"), indent=1)
