"""Sichtprüfung: Varianten des Einschnitts als Bildraster (je 4 fps)."""
import subprocess, sys, urllib.request
from pathlib import Path
B = "https://d8j0ntlcm91z4.cloudfront.net/user_3GtRWXMjLrU3v9GLLgFwO6h9TsQ/"
OUT = Path("out")
for k, name in enumerate(sys.argv[1:]):
    p = OUT / f"var{k}.mp4"
    urllib.request.urlretrieve(B + name, p)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-map", "0:v:0", "-vf", "fps=4,scale=180:-1,tile=8x2",
                    "-frames:v", "1", str(OUT / f"var{k}.jpg")], check=True)
print("ok")
