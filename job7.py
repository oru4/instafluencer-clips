"""Batch 3 (24.–28.10.): B-Rolls (Video + Off-Stimme + Bildtext + Musik) und Sprechclips (voice_change → Whisper → Untertitel).
Pro Clip ein Bildraster out/<clip>_t.jpg zur Sichtprüfung, Whisper-Bericht in out/whisper_b3.json."""
import difflib, json, re, subprocess, sys, urllib.request
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel

B = "https://d8j0ntlcm91z4.cloudfront.net/user_3GtRWXMjLrU3v9GLLgFwO6h9TsQ/"
OUT = Path("out"); OUT.mkdir(exist_ok=True)
BROLL = json.loads(Path("b3_broll.json").read_text(encoding="utf-8"))
SPRECH = json.loads(Path("b3_sprech.json").read_text(encoding="utf-8"))
nur = set(sys.argv[1:])

def run(*a):
    subprocess.run(list(a), check=True)

def pcm(p):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(p), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def dauer(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout)

def raster(cid):
    f = OUT / f"{cid}.mp4"
    run("ffmpeg", "-y", "-loglevel", "error", "-i", str(f), "-vf", f"fps={8 / dauer(f):.4f},scale=180:-1,tile=8x1", "-frames:v", "1", str(OUT / f"{cid}_t.jpg"))

norm = lambda t: "".join(re.findall(r"[a-zäöüß0-9]+", t.lower()))
model = WhisperModel("medium", device="cpu", compute_type="int8")
bericht = {}

for c in BROLL:
    cid = c["cid"]
    if nur and cid not in nur:
        continue
    roh, offd = OUT / f"{cid}_video.mp4", OUT / f"{cid}_off.mp3"
    urllib.request.urlretrieve(B + c["video"] + ".mp4", roh)
    urllib.request.urlretrieve(B + c["off"] + ".mp3", offd)
    has_a = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(roh)],
                           capture_output=True, text=True).stdout.strip() != ""
    a_in = ["-i", str(roh)] if has_a else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    # Quellen in anderem Format (z.B. 3:4) mittig auf unscharfen 9:16-Hintergrund setzen
    v = ("[0:v:0]split[a][b];[a]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,boxblur=20:2[bg];"
         "[b]scale=720:-2[fg];[bg][fg]overlay=0:(H-h)/2,setsar=1[v]") if c.get("pad") else "[0:v:0]null[v]"
    fc = v + ";[1:a]volume=0.5[amb];[2:a]adelay=300|300,volume=1.6[off];[amb][off]amix=inputs=2:duration=first:normalize=0[a]"
    base = OUT / f"{cid}_base.mp4"
    run("ffmpeg", "-y", "-loglevel", "error", "-i", str(roh), *a_in, "-i", str(offd), "-filter_complex", fc,
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(base))
    run("python3", "fertigschnitt.py", str(base), "--figur", c["figur"], "--hook", c["hook"], "--key", c["key"], "--hook-bis", "2.5",
        "--hook-y", "0.12", "--text2", c["text2"], "--text2-ab", "2.6", "--text2-y", "0.12", "--musik", "--out", str(OUT / f"{cid}.mp4"))
    segs, _ = model.transcribe(pcm(offd), language="de")
    bericht[cid] = {"gehört": " ".join(s.text.strip() for s in segs)}
    base.unlink(); roh.unlink()
    raster(cid)

for c in SPRECH:
    cid = c["cid"]
    if nur and cid not in nur:
        continue
    skript = c["skript"]
    roh = OUT / f"{cid}_roh.mp4"
    urllib.request.urlretrieve(B + c["video"] + ".mp4", roh)
    segs, _ = model.transcribe(pcm(roh), language="de", word_timestamps=True, initial_prompt=skript)
    words = [{"word": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)} for s in segs for w in s.words]
    roh.with_suffix(".words.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    a, b = [norm(x) for x in skript.split()], [norm(w["word"]) for w in words]
    sm = difflib.SequenceMatcher(None, a, b)
    bericht[cid] = {"quote": round(sm.ratio() * 100), "gehört": " ".join(w["word"] for w in words),
                    "abweichungen": [(" ".join(skript.split()[i1:i2]), " ".join(w["word"] for w in words[j1:j2]))
                                     for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]}
    run("python3", "fertigschnitt.py", str(roh), "--figur", c["figur"], "--hook", c["hook"], "--key", c["key"], "--hook-bis", "2.5",
        "--hook-y", "0.40", "--skript", skript, "--out", str(OUT / f"{cid}.mp4"))
    raster(cid)

alt = OUT / "whisper_b3.json"
gesamt = json.loads(alt.read_text(encoding="utf-8")) if alt.exists() else {}
gesamt.update(bericht)
alt.write_text(json.dumps(gesamt, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(bericht, ensure_ascii=False, indent=1))
