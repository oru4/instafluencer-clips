"""Sichtprüfung: Bilder verkleinert nach out/bild<k>.jpg."""
import subprocess, sys, urllib.request
from pathlib import Path
B = "https://d8j0ntlcm91z4.cloudfront.net/user_3GtRWXMjLrU3v9GLLgFwO6h9TsQ/"
for k, name in enumerate(sys.argv[1:]):
    p = Path("out") / f"bild{k}.png"
    urllib.request.urlretrieve(B + name, p)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-vf", "scale=360:-1", str(p.with_suffix(".jpg"))], check=True)
print("ok")
