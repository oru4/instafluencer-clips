"""B-Rolls 20./22.10.: Video + Off-Stimme + Bildtext + Musik, dazu Whisper-Prüfung und Standbilder."""
import json, subprocess, urllib.request
from pathlib import Path

B = "https://d8j0ntlcm91z4.cloudfront.net/user_3GtRWXMjLrU3v9GLLgFwO6h9TsQ/"
OUT = Path("out"); OUT.mkdir(exist_ok=True)
CLIPS = [
    ("mila-2026-10-20-01", "mila", "hf_20261025_231030_6bee1fb1-db72-45da-9b1a-295c310d0b48", "hf_20261025_231031_1bc35ea1-e30e-4d44-a23c-7a4dd9f06814",
     "Dieses Brett ist krumm.", "krumm.", "Vor dem Kauf an der Kante entlangschauen"),
    ("mila-2026-10-22-01", "mila", "hf_20261025_231030_e8024d47-9e9a-4c64-bef5-5f9ccc8639cf", "hf_20261025_231032_80749898-863f-4081-b909-f721d1787cc1",
     "Die Zahl auf dem Schleifpapier", "Zahl", "80 grob · 120 mittel · 180 fein"),
    ("nele-2026-10-20-01", "nele", "hf_20261025_231029_1e1355cc-645c-45c9-8e15-abad3d8ce5e8", "hf_20261025_231032_e7d570e7-d3f4-4deb-a1a9-fd43a7aa8e9a",
     "Hampelmann ohne Springen", "ohne Springen", "30 Sek · Schritt zur Seite · Arme hoch"),
    ("nele-2026-10-22-01", "nele", "hf_20261025_231045_f2b5df87-da80-4c5f-a323-31482a9d869f", "hf_20261025_231032_503b3c4e-e383-4c72-8fed-30fb9d10af4e",
     "Plank: erst mal 20 Sek.", "20 Sek.", "Ellbogen unter den Schultern · Po nicht hoch"),
    ("hilde-2026-10-20-01", "hilde", "hf_20261025_231030_19d45d0c-63fe-4f1e-91f2-098bd85abb4c", "hf_20261025_231032_06e7cd00-d1d3-477e-a7bb-0e290037d65f",
     "Ein Abo kennst du nicht mehr.", "nicht mehr.", "Einmal im Monat: alle Abos durchgehen"),
    ("hilde-2026-10-22-01", "hilde", "hf_20261025_231030_1a9dea5a-1df3-4218-9072-36d005ee5e76", "hf_20261025_231032_06a1c4a4-00e3-4f90-bbcb-ba18d5af9831",
     "Nie hungrig einkaufen.", "hungrig", "Erst essen · dann Zettel · dann Laden"),
]

def run(*a):
    subprocess.run(list(a), check=True)

from faster_whisper import WhisperModel
whisper = WhisperModel("medium", device="cpu", compute_type="int8")
bericht = {}
for cid, figur, vid, off, hook, key, text2 in CLIPS:
    roh, offd = OUT / f"{cid}_video.mp4", OUT / f"{cid}_off.mp3"
    urllib.request.urlretrieve(B + vid + ".mp4", roh)
    urllib.request.urlretrieve(B + off + ".mp3", offd)
    # Grok-MP4 hat zwei Videospuren → nur die erste; fehlende Tonspur durch Stille ersetzen
    base = OUT / f"{cid}_base.mp4"
    has_a = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(roh)],
                           capture_output=True, text=True).stdout.strip() != ""
    a_in = ["-i", str(roh)] if has_a else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    fc = ("[1:a]volume=0.5[amb];[2:a]adelay=300|300,volume=1.6[off];[amb][off]amix=inputs=2:duration=first:normalize=0[a]")
    run("ffmpeg", "-y", "-loglevel", "error", "-i", str(roh), *a_in, "-i", str(offd), "-filter_complex", fc,
        "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(base))
    fertig = OUT / f"{cid}.mp4"
    run("python3", "fertigschnitt.py", str(base), "--figur", figur, "--hook", hook, "--key", key, "--hook-bis", "2.5",
        "--hook-y", "0.12", "--text2", text2, "--text2-ab", "2.5", "--text2-y", "0.12", "--musik", "--out", str(fertig))
    segs, info = whisper.transcribe(str(offd), language="de")
    bericht[cid] = " ".join(s.text.strip() for s in segs)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(fertig)],
                               capture_output=True, text=True).stdout)
    for n, t in enumerate([0.3, dur / 2, dur - 0.3]):
        run("ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(fertig), "-frames:v", "1", "-vf", "scale=270:-1", str(OUT / f"{cid}_f{n}.jpg"))
    base.unlink()
(OUT / "whisper_brolls.json").write_text(json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(bericht, ensure_ascii=False, indent=1))
