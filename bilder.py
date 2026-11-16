"""Startbilder herunterladen und als Kontaktbogen (verkleinert) ablegen."""
import json, sys, urllib.request, subprocess
from pathlib import Path
B = "https://d8j0ntlcm91z4.cloudfront.net/user_3GtRWXMjLrU3v9GLLgFwO6h9TsQ/"
OUT = Path("out"); OUT.mkdir(exist_ok=True)
for name in json.loads(Path(sys.argv[1]).read_text()):
    p = OUT / f"{name[-8:]}.png"
    urllib.request.urlretrieve(B + name + ".png", p)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-vf", "scale=360:-2", str(OUT / f"{name.split('_')[-1][:8]}.jpg")], check=True)
    p.unlink()
