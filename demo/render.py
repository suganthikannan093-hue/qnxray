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
  "The problem", "A priority thirty thread asks a server for a half second reply. It waits three point two seconds. Nothing crashed, nothing was logged. On a real-time system, that is a bug you can't see."),
 ("title", ("QNXray", "X-ray vision for QNX 8.0: live threads, priority inversions, traces, crashes"),
  "QNXray", "This is Q N X ray: a developer tool that finds priority inversions and crashes on a live Q N X eight target, and explains them, in the terminal, in V S Code, and in C I."),
 ("term", scene_txt("01"), "Live target: QNX SDP 8.0 on QEMU x86_64, over SSH",
  "Everything you'll see is live. This is Q N X eight point oh, running in QEMU, reached over S S H."),
 ("term", scene_txt("02"), "Snapshot via /dev/qnxray — our own QNX resource manager",
  "Q N X ray ships its own resource manager. It registers slash dev slash Q N X ray, and every read returns a fresh snapshot of every process and thread."),
 ("term", scene_txt("03"), "The bug: server 10 READY, hog 20 RUNNING, client 30 REPLY-blocked",
  "Here is the bug in raw pidin. The client at priority thirty is reply-blocked on a server at priority ten, and a priority twenty hog owns the CPU."),
 ("term", scene_txt("04"), "Wow: QNXray names the inversion — waiter, owner, and who preempts it",
  "Q N X ray follows the message passing chain and names it: the waiter, the server it is blocked on, and the exact thread preempting that server."),
 ("term", scene_txt("05"), "tracelogger → traceprinter → per-thread timeline",
  "Then it proves it with the kernel tracer. One second of tracelogger: the hog runs the whole time, the server is ready but starved, the client waits in reply."),
 ("video", (4.5, 28.5), "VS Code dashboard: live findings, CPU lanes, trace timeline",
  "The same engine drives a V S Code dashboard. Live findings at the top, what each CPU is running, and the trace timeline, one click away."),
 ("term", scene_txt("06", "07", "08"), "CI gate: exit 2 = inversion, 0 = clean, 1 = crash",
  "And in C I, it is a gate. Inversion exits two. The fixed build exits zero. A crashing binary exits one, with a JSON report."),
 ("term", scene_txt("09"), "Crash explained: SIGSEGV, NULL deref in read_sensor, file and line",
  "When something crashes, Q N X ray collects the core and explains it: a null pointer dereference in read sensor, with the file and line."),
 ("term", scene_txt("10", "11"), "The fix: priority inheritance — 3.20 s → 0.50 s",
  "The fix is one Q N X feature: priority inheritance. Same program, with inherit on. The reply drops from three point two seconds to half a second."),
 ("title", ("QNXray", "resource manager · message-passing analysis · tracelogger · VS Code · CI"),
  "Built for QNX SDP 8.0", "Q N X ray. See the invisible real-time bugs, before they ship."),
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

def color(line):
    if line.startswith("$"): return ACC
    if re.search(r"exit=2|REPLY|inversion\b.*3\.20|priority inversion|SEGV|NULL|\"severity\"", line): return RED
    if re.search(r"exit=0|OK, server|RUNNING|#{5}", line): return GRN
    if line.startswith("[exit"): return DIM
    return FG

def term_frames(txt, cap, n, dur):
    lines = txt.splitlines(); wrapped = []
    longest = max(len(l) for l in lines)
    size = max(18, min(34, int((W - 160) / (0.602 * max(longest, 60))), int((H - 300) / (1.35 * len(lines)))))
    mono = font("DejaVuSansMono.ttf", size); maxc = int((W - 160) / (0.602 * size))
    for l in lines:
        while len(l) > maxc: wrapped.append(l[:maxc]); l = "  " + l[maxc:]
        wrapped.append(l)
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
                    d.text((80, top + j * lh), wrapped[j], font=mono, fill=color(wrapped[j]))
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
    wav, sec = tts(i, narr); dur = round(sec + 2.5, 2)
    if kind == "video": dur = max(dur, 24)
    if kind == "title": img = title_frame(*payload, cap, i + 1).tobytes(); frames = (img for _ in range(int(dur * FPS)))
    elif kind == "term": frames = term_frames(payload, cap, i + 1, dur)
    parts.append(encode(i, frames if kind != "video" else None, dur=dur, audio=wav, video=f"{RAW}/vscode.mp4" if kind == "video" else None) if kind == "video"
                 else encode(i, frames, dur=dur, audio=wav))
    script.append((i + 1, kind, cap, narr, dur)); print(f"scene {i+1}: {dur:.1f}s {cap}")
open(f"{B}/list.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{B}/list.txt", "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", f"{D}/qnxray_demo.mp4"], check=True)
print("total", sum(s[4] for s in script)); json.dump(script, open(f"{B}/timing.json", "w"), indent=1)
