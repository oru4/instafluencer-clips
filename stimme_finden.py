"""Welche Higgsfield-Preset-Stimme steckt in den voice_change-Clips? Sprecher-Embeddings (resemblyzer) vergleichen.
Ziele: Milas und Neles voice_change-Ergebnisse vom 16.11. (Nele als Gegenprobe). Ergebnis: out/stimme_finden.json"""
import json, subprocess, urllib.request
from pathlib import Path
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

B = "https://d8j0ntlcm91z4.cloudfront.net/user_3GtRWXMjLrU3v9GLLgFwO6h9TsQ/"
ZIELE = {
    "mila-18": "hf_20261116_161854_1b59e4b6-8a80-4c97-9535-bc0e6e1e852a",
    "mila-20": "hf_20261116_161433_497ecae3-9d73-4e15-a5aa-1da7f338d75c",
    "mila-22": "hf_20261116_161643_99d34cc4-8298-46ad-9208-904985fd2a45",
    "nele-18": "hf_20261116_161435_9b8f9024-ee0e-4b6d-8406-e6f9a37b4494",
}
T = Path("tmp"); T.mkdir(exist_ok=True)
OUT = Path("out"); OUT.mkdir(exist_ok=True)
enc = VoiceEncoder()

def wav(src, dst):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "16000", str(dst)], check=True)
    return enc.embed_utterance(preprocess_wav(str(dst)))

def lade(url, dst):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    dst.write_bytes(urllib.request.urlopen(req, timeout=60).read())

ziel = {}
for k, v in ZIELE.items():
    lade(B + v + ".mp4", T / f"{k}.mp4")
    ziel[k] = wav(T / f"{k}.mp4", T / f"{k}.wav")

kand = {}
for zeile in Path("stimmen.txt").read_text().split("\n"):
    if not zeile.strip():
        continue
    name, url = zeile.split()
    try:
        lade(url, T / f"v_{name}")
        kand[name] = wav(T / f"v_{name}", T / f"v_{name}.wav")
    except Exception as e:
        print("Fehler", name, e)

erg = {}
for k, e in ziel.items():
    s = sorted(((float(np.dot(e, c)), n) for n, c in kand.items()), reverse=True)
    erg[k] = [[n, round(x, 3)] for x, n in s[:6]]
erg["mila_untereinander"] = round(float(np.dot(ziel["mila-18"], ziel["mila-20"])), 3)
(OUT / "stimme_finden.json").write_text(json.dumps(erg, indent=1), encoding="utf-8")
print(json.dumps(erg, indent=1))
