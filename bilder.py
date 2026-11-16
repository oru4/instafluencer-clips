"""Startbilder herunterladen und verkleinert als nn_<id>.jpg ablegen (Reihenfolge = Liste)."""
import json, sys, urllib.request, subprocess
from pathlib import Path
B = "https://d8j0ntlcm91z4.cloudfront.net/user_3GtRWXMjLrU3v9GLLgFwO6h9TsQ/"
OUT = Path("out"); OUT.mkdir(exist_ok=True)
for i, name in enumerate(json.loads(Path(sys.argv[1]).read_text()), 1):
    p = OUT / "tmp.png"
    urllib.request.urlretrieve(B + name + ".png", p)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-vf", "scale=360:-2", str(OUT / f"{i:02d}_{name.split('_')[-1][:8]}.jpg")], check=True)
    p.unlink()
