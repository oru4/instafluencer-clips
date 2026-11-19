"""Zusatzclip mila-2026-11-24-01 (Posting 23.11.): Stimmkandidaten gegen Milas bisherige Clips prüfen,
den besten Kandidaten wie in job8.py fertigschneiden (Whisper → Untertitel → Hook) und als Release-Anhang ablegen."""
import difflib, json, re, subprocess, urllib.request
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel
from resemblyzer import VoiceEncoder, preprocess_wav

B = "https://d8j0ntlcm91z4.cloudfront.net/user_3GtRWXMjLrU3v9GLLgFwO6h9TsQ/"
OUT, T = Path("out"), Path("tmp")
OUT.mkdir(exist_ok=True); T.mkdir(exist_ok=True)
REF = ["hf_20261116_161854_1b59e4b6-8a80-4c97-9535-bc0e6e1e852a", "hf_20261116_161433_497ecae3-9d73-4e15-a5aa-1da7f338d75c",
       "hf_20261116_161643_99d34cc4-8298-46ad-9208-904985fd2a45"]
KAND = json.loads(Path("b5_kandidaten.json").read_text(encoding="utf-8"))
C = json.loads(Path("b5_sprech.json").read_text(encoding="utf-8"))
enc = VoiceEncoder()

def run(*a):
    subprocess.run(list(a), check=True)

def lade(name):
    p = T / f"{name}.mp4"
    if not p.exists():
        urllib.request.urlretrieve(B + name + ".mp4", p)
    return p

def emb(p):
    w = p.with_suffix(".wav")
    run("ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-ac", "1", "-ar", "16000", str(w))
    return enc.embed_utterance(preprocess_wav(str(w)))

ref = [emb(lade(r)) for r in REF]
bericht = {"kandidaten": {}}
for stimme, video in KAND.items():
    e = emb(lade(video))
    bericht["kandidaten"][stimme] = round(float(np.mean([np.dot(e, r) for r in ref])), 3)
best = max(bericht["kandidaten"], key=bericht["kandidaten"].get)
bericht["gewählt"] = best
print(json.dumps(bericht, indent=1))

cid, skript = C["cid"], C["skript"]
roh = OUT / f"{cid}_roh.mp4"
roh.write_bytes(lade(KAND[best]).read_bytes())
pcm = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(roh), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                                   capture_output=True, check=True).stdout, np.int16).astype(np.float32) / 32768
model = WhisperModel("medium", device="cpu", compute_type="int8")
segs, _ = model.transcribe(pcm, language="de", word_timestamps=True, initial_prompt=skript)
words = [{"word": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)} for s in segs for w in s.words]
roh.with_suffix(".words.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
norm = lambda t: "".join(re.findall(r"[a-zäöüß0-9]+", t.lower()))
a, b = [norm(x) for x in skript.split()], [norm(w["word"]) for w in words]
sm = difflib.SequenceMatcher(None, a, b)
bericht["whisper"] = {"quote": round(sm.ratio() * 100), "gehört": " ".join(w["word"] for w in words)}
run("python3", "fertigschnitt.py", str(roh), "--figur", "mila", "--hook", C["hook"], "--key", C["key"], "--hook-bis", "2.5",
    "--hook-y", "0.40", "--skript", skript, "--out", str(OUT / f"{cid}.mp4"))
f = OUT / f"{cid}.mp4"
d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)], capture_output=True, text=True).stdout)
run("ffmpeg", "-y", "-loglevel", "error", "-i", str(f), "-vf", f"fps={8 / d:.4f},scale=180:-1,tile=8x1", "-frames:v", "1", str(OUT / f"{cid}_t.jpg"))
bericht["dauer_s"] = round(d, 1)
(OUT / "job9.json").write_text(json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(bericht, ensure_ascii=False, indent=1))
