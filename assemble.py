"""Mux voice-over + soft pad + burned-in English subtitles → connect_suggests_pitch.mp4 (1920x1080) and .srt"""
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
VO = os.path.join(HERE, "vo")
tl = json.load(open(os.path.join(HERE, "timeline.json")))
meta = json.load(open(os.path.join(VO, "durations.json")))
dur, subs = meta["durations"], {x["id"]: x["sub"] for x in meta["lines"]}
END = tl["_end"]


def chunks(text, maxlen=74):
    """Split a subtitle line into readable chunks at sentence / clause boundaries."""
    parts = re.split(r"(?<=[.?!])\s+", text)
    out = []
    for p in parts:
        while len(p) > maxlen:
            cut = max(p.rfind(", ", 0, maxlen), p.rfind(": ", 0, maxlen))
            if cut < 25:
                cut = p.rfind(" ", 0, maxlen)
            out.append(p[:cut + 1].strip())
            p = p[cut + 1:].strip()
        if p:
            out.append(p)
    # merge very short chunks with the previous one
    merged = []
    for c in out:
        if merged and len(c) < 22 and len(merged[-1]) + len(c) < maxlen + 10:
            merged[-1] += " " + c
        else:
            merged.append(c)
    return merged


def ts(t, srt=False):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    if srt:
        return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


events = []
for lid, start in tl.items():
    if lid.startswith("_"):
        continue
    cs = chunks(subs[lid])
    total = sum(len(c) for c in cs)
    t = start
    for c in cs:
        d = dur[lid] * len(c) / total
        events.append((t, t + d + 0.15, c))
        t += d
# no overlaps
for i in range(len(events) - 1):
    if events[i][1] > events[i + 1][0]:
        events[i] = (events[i][0], events[i + 1][0] - 0.02, events[i][2])

with open(os.path.join(HERE, "connect_suggests_pitch.srt"), "w", encoding="utf-8") as f:
    for i, (a, b, c) in enumerate(events, 1):
        f.write(f"{i}\n{ts(a, True)} --> {ts(b, True)}\n{c}\n\n")

ass = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "WrapStyle: 0", "",
       "[V4+ Styles]",
       "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
       "Style: Sub,Inter,44,&H00FFFFFF,&H00FFFFFF,&H00161E1A,&H50161E1A,1,0,0,0,100,100,0,0,3,14,0,2,200,200,46,1",
       "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
for a, b, c in events:
    ass.append(f"Dialogue: 0,{ts(a)},{ts(b)},Sub,,0,0,0,,{c}")
open(os.path.join(HERE, "subs.ass"), "w", encoding="utf-8").write("\n".join(ass) + "\n")

# ---- audio: voice clips at their timeline positions ----
ids = [k for k in tl if not k.startswith("_")]
inputs, filt = [], []
for n, lid in enumerate(ids):
    inputs += ["-i", os.path.join(VO, f"{lid}.wav")]
    ms = int(tl[lid] * 1000)
    filt.append(f"[{n}:a]aresample=48000,adelay={ms}|{ms}[v{n}]")
filt.append("".join(f"[v{n}]" for n in range(len(ids))) + f"amix=inputs={len(ids)}:normalize=0,apad,atrim=0:{END:.2f},loudnorm=I=-16:TP=-1.5:LRA=7[voice]")
# soft warm pad (C maj9) with slow movement, very low under the voice
pad = ("aevalsrc='0.22*(sin(2*PI*130.81*t)+0.8*sin(2*PI*196*t)+0.6*sin(2*PI*246.94*t)+0.5*sin(2*PI*293.66*t)+0.35*sin(2*PI*329.63*t))"
       f"*(0.75+0.25*sin(2*PI*0.08*t))':s=48000:d={END:.2f}")
filt.append(f"{pad},lowpass=f=900,volume=0.05,afade=t=in:d=2.5,afade=t=out:st={END - 3.5:.2f}:d=3.5[pad]")
filt.append("[voice][pad]amix=inputs=2:normalize=0:weights=1 1,alimiter=limit=0.95[a]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt), "-map", "[a]",
                "-c:a", "pcm_s16le", os.path.join(HERE, "mix.wav")], check=True)

subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(HERE, "film_raw.webm"), "-i", os.path.join(HERE, "mix.wav"),
                "-vf", f"scale=1920:1080:flags=lanczos,ass={os.path.join(HERE, 'subs.ass')}", "-c:v", "libx264", "-preset", "medium",
                "-crf", "19", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                os.path.join(HERE, "connect_suggests_pitch.mp4")], check=True)
# version without burned subtitles (for platforms with their own captions)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(HERE, "film_raw.webm"), "-i", os.path.join(HERE, "mix.wav"),
                "-vf", "scale=1920:1080:flags=lanczos", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                "-r", "30", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                os.path.join(HERE, "connect_suggests_pitch_nosubs.mp4")], check=True)
print(len(events), "subtitle events; done")
