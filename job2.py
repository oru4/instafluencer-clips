"""Sprechclips 19./21./23.10.: voice_change-Video → Whisper-Wörter → Fertigschnitt mit Hook + Untertiteln; dazu nele-20 neu."""
import difflib, json, re, subprocess, urllib.request
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel

B = "https://d8j0ntlcm91z4.cloudfront.net/user_3GtRWXMjLrU3v9GLLgFwO6h9TsQ/"
OUT = Path("out"); OUT.mkdir(exist_ok=True)
S = [
 ("mila-2026-10-19-01", "mila", "hf_20261025_232525_dc0adce6-47aa-4599-b0dc-2cc7e33bd31f", "Dein Regal wackelt?", "wackelt?",
  "Dein erstes Regal wackelt? Meins auch. Rate mal, warum. Keine Rückwand. Eine dünne Platte hinten drauf, und es steht. Wackelt deins auch?"),
 ("mila-2026-10-21-01", "mila", "hf_20261025_232528_d3e831bb-81da-4e20-a6d8-d56305de5723", "Angst vorm Akkuschrauber?", "Angst",
  "Du hast Respekt vorm Akkuschrauber? Ich hatte richtig Angst. Kleinste Stufe, ein Restbrett, zehn Schrauben. Heute ist er mein Lieblingswerkzeug. Wovor hattest du Respekt?"),
 ("mila-2026-10-23-01", "mila", "hf_20261025_232530_d611fa42-efc3-467f-8209-8f5d89b31e8d", "Zweimal gemessen. Trotzdem falsch.", "Trotzdem falsch.",
  "Du misst zweimal, und es passt trotzdem nicht? Kenn ich. Die Säge frisst ein paar Millimeter. Säg neben dem Strich, auf der Abfallseite."),
 ("nele-2026-10-19-01", "nele", "hf_20261025_232532_5fc86d2b-00f7-4b7e-a4d4-2060d8fe723c", "Keine Matte? Teppich.", "Teppich.",
  "Du hast keine Matte? Du hast einen Teppich. Ich hab drei Monate auf einem Badetuch trainiert. Worauf trainierst du?"),
 ("nele-2026-10-21-01", "nele", "hf_20261025_232535_cc9a316a-5fb2-449d-9cfb-75156fc66d8f", "Meeting vorbei. Matte raus.", "Matte raus.",
  "Dein letztes Meeting ist vorbei? Laptop zu. Zwanzig Minuten Boden, bevor du aufs Sofa fällst. Wann trainierst du?"),
 ("nele-2026-10-23-01", "nele", "hf_20261025_232537_de389b16-f828-42e2-8170-a9942721532b", "Zu müde? 5 Minuten.", "5 Minuten.",
  "Du bist zu müde für zwanzig Minuten? Dann mach fünf. Fünf sind mehr als null. Und meistens werden's zehn."),
 ("hilde-2026-10-19-01", "hilde", "hf_20261025_232539_92058dc1-d25f-4cce-9864-3954b54954c4", "Budget-App? Bleistift.", "Bleistift.",
  "Kind, du hast drei Budget-Apps? Und weisst trotzdem nicht, wo das Geld hin ist? Ich hab einen Bleistift. Und ich weiss es auf den Euro genau. App oder Papier, was nimmst du?"),
 ("hilde-2026-10-21-01", "hilde", "hf_20261025_232541_6249e854-01ff-4f6e-add6-07ea75cb96a2", "4,50 € für einen Kaffee.", "4,50 €",
  "Kind, vier Euro fünfzig. Für einen Kaffee. Im Pappbecher. Dafür hab ich früher ein Pfund Kaffee gekauft. Was zahlst du für deinen?"),
 ("hilde-2026-10-23-01", "hilde", "hf_20261025_232544_74ddbd14-47a2-4103-852c-89e294fa507a", "Am Monatsende fehlt Geld?", "fehlt Geld?",
  "Kind, dir fehlt am Monatsende Geld? Am Monatsende ist nicht zu wenig Geld da. Am Anfang war zu wenig Plan da. Schreib dir am Ersten auf, was weggeht."),
]

def run(*a):
    subprocess.run(list(a), check=True)

def pcm(p):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(p), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

norm = lambda t: "".join(re.findall(r"[a-zäöüß0-9]+", t.lower()))
model = WhisperModel("medium", device="cpu", compute_type="int8")
bericht = {}
for cid, figur, h, hook, key, skript in S:
    roh = OUT / f"{cid}_roh.mp4"
    if not roh.exists():
        urllib.request.urlretrieve(B + h + ".mp4", roh)
    segs, _ = model.transcribe(pcm(roh), language="de", word_timestamps=True, initial_prompt=skript)
    words = [{"word": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)} for s in segs for w in s.words]
    roh.with_suffix(".words.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    gehört = " ".join(w["word"] for w in words)
    a, b = [norm(x) for x in skript.split()], [norm(w["word"]) for w in words]
    bericht[cid] = {"quote": round(difflib.SequenceMatcher(None, a, b).ratio() * 100), "gehört": gehört,
                    "abweichungen": [(" ".join(skript.split()[i1:i2]), " ".join(w["word"] for w in words[j1:j2]))
                                     for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes() if op != "equal"]}
    fertig = OUT / f"{cid}.mp4"
    run("python3", "fertigschnitt.py", str(roh), "--figur", figur, "--hook", hook, "--key", key, "--hook-bis", "2.5",
        "--hook-y", "0.40", "--skript", skript, "--out", str(fertig))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(fertig)], capture_output=True, text=True).stdout)
    for n, t in enumerate([0.4, 1.5, dur / 2, dur - 0.5]):
        run("ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(fertig), "-frames:v", "1", "-vf", "scale=220:-1", str(OUT / f"{cid}_f{n}.jpg"))

# nele-20 neu (Grok, nur ein Fuss bewegt sich)
cid = "nele-2026-10-20-01"
neu = OUT / f"{cid}_video.mp4"
urllib.request.urlretrieve(B + "hf_20261025_232102_315e2c58-244c-4ebf-98ab-d14699a64da1.mp4", neu)
base = OUT / f"{cid}_base.mp4"
fc = "[1:a]volume=0.5[amb];[2:a]adelay=300|300,volume=1.6[off];[amb][off]amix=inputs=2:duration=first:normalize=0[a]"
has_a = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(neu)], capture_output=True, text=True).stdout.strip() != ""
a_in = ["-i", str(neu)] if has_a else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
run("ffmpeg", "-y", "-loglevel", "error", "-i", str(neu), *a_in, "-i", str(OUT / f"{cid}_off.mp3"), "-filter_complex", fc,
    "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(base))
run("python3", "fertigschnitt.py", str(base), "--figur", "nele", "--hook", "Hampelmann ohne Springen", "--key", "ohne Springen", "--hook-bis", "2.5",
    "--hook-y", "0.12", "--text2", "30 Sek · Schritt zur Seite · Arme hoch", "--text2-ab", "2.6", "--text2-y", "0.12", "--musik", "--out", str(OUT / f"{cid}.mp4"))
base.unlink()
for k in range(8):
    run("ffmpeg", "-y", "-loglevel", "error", "-ss", f"{k * 0.75:.2f}", "-i", str(OUT / f"{cid}.mp4"), "-frames:v", "1", "-vf", "scale=200:-1", str(OUT / f"{cid}_s{k}.jpg"))
(OUT / "whisper_sprech.json").write_text(json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: (v["quote"], v["abweichungen"]) for k, v in bericht.items()}, ensure_ascii=False, indent=1))
