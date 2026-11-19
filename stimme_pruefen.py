"""Gleiche Sprache, gleicher Anbieter: Sprechclips (voice_change) gegen die deutschen Off-Stimmen der B-Rolls (text2speech, Stimme bekannt)."""
import json, subprocess, urllib.request
from pathlib import Path
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

B = "https://d8j0ntlcm91z4.cloudfront.net/user_3GtRWXMjLrU3v9GLLgFwO6h9TsQ/"
T = Path("tmp"); T.mkdir(exist_ok=True); Path("out").mkdir(exist_ok=True)
enc = VoiceEncoder()
OFF = {  # Off-Stimmen mit gespeicherter Stimme
 "Nadine": ["hf_20261116_160703_cf6e137d-add4-4392-8869-438a54feec64.mp3", "hf_20261107_121056_8f732c84-c592-4ff7-a41a-f1386610cca5.mp3", "hf_20261025_231032_80749898-863f-4081-b909-f721d1787cc1.mp3"],
 "Skye": ["hf_20261116_162649_dc1adb20-414a-4a4e-a93e-b0ff606ddf63.mp3", "hf_20261116_161305_aaa286c4-903f-4045-8b2e-a52aff7f9741.mp3", "hf_20261025_231032_503b3c4e-e383-4c72-8fed-30fb9d10af4e.mp3"],
 "Petra": ["hf_20261116_160704_5346d824-bdb5-47f5-9a50-7fa5fcc2b9d2.mp3", "hf_20261107_121056_b964440a-f754-42f4-a666-9939b15a4446.mp3", "hf_20261025_231032_06a1c4a4-00e3-4f90-bbcb-ba18d5af9831.mp3"],
}
SPRECH = {
 "mila-18": "hf_20261116_161854_1b59e4b6-8a80-4c97-9535-bc0e6e1e852a.mp4",
 "mila-20": "hf_20261116_161433_497ecae3-9d73-4e15-a5aa-1da7f338d75c.mp4",
 "mila-22": "hf_20261116_161643_99d34cc4-8298-46ad-9208-904985fd2a45.mp4",
 "nele-18": "hf_20261116_161435_9b8f9024-ee0e-4b6d-8406-e6f9a37b4494.mp4",
 "nele-20": "hf_20261116_161437_36ae4408-8136-41a3-83f9-530eb7e624f2.mp4",
 "nele-22": "hf_20261116_161439_13c7c711-99fc-45d2-8344-f0514210254b.mp4",
 "hilde-18": "hf_20261116_161646_e5584fad-baf0-4bfa-b5d6-7e4a248fa2eb.mp4",
 "hilde-20": "hf_20261116_161648_59e1cf65-2db5-4750-91ee-9c62a4532b68.mp4",
 "kontrolle-naomi": "hf_20261119_110202_4dfccac1-f03f-45e4-9aa0-422960cc883f.mp4",
}
def emb(name):
    p = T / name
    if not p.exists():
        urllib.request.urlretrieve(B + name, p)
    w = p.with_suffix(".x.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-ac", "1", "-ar", "16000", str(w)], check=True)
    return enc.embed_utterance(preprocess_wav(str(w)))
off = {k: np.mean([emb(f) for f in v], axis=0) for k, v in OFF.items()}
off = {k: v / np.linalg.norm(v) for k, v in off.items()}
erg = {k: {s: round(float(np.dot(emb(f), e)), 3) for s, e in off.items()} for k, f in SPRECH.items()}
Path("out/stimme_pruefen.json").write_text(json.dumps(erg, indent=1), encoding="utf-8")
print(json.dumps(erg, indent=1))
