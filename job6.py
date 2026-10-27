"""Sichtprüfung: Startbilder als Raster out/raster.jpg (Reihenfolge = Argumente, 5 pro Zeile)."""
import subprocess, sys, urllib.request
from pathlib import Path
B = "https://d8j0ntlcm91z4.cloudfront.net/user_3GtRWXMjLrU3v9GLLgFwO6h9TsQ/"
tmp = Path("tmp"); tmp.mkdir(exist_ok=True)
ein = []
for k, name in enumerate(sys.argv[1:]):
    p = tmp / f"{k:02d}.png"
    urllib.request.urlretrieve(B + name, p)
    q = tmp / f"{k:02d}.jpg"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-vf", "scale=300:533,setsar=1", str(q)], check=True)
    ein.append(q)
n = len(ein)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "1", "-i", str(tmp / "%02d.jpg"), "-vf", f"tile=5x{(n + 4) // 5}",
                "-frames:v", "1", "out/raster.jpg"], check=True)
print("ok")
