"""mila-19: Einschnitte Regal ohne Rückwand (wackelt) und mit Rückwand (steht) in den Sprechclip, Stimme läuft durch."""
import shutil, subprocess, urllib.request
from pathlib import Path
B = "https://d8j0ntlcm91z4.cloudfront.net/user_3GtRWXMjLrU3v9GLLgFwO6h9TsQ/"
OUT = Path("out")
cid = "mila-2026-10-19-01"
EIN = [("A", "hf_20261026_001821_91cf80d5-2e48-4d0e-ba13-9454ac0c6dbe.mp4", 3.2, 6.15), ("B", "hf_20261025_235025_52e0142a-85c6-453c-97f9-0618b9c59426.mp4", 6.25, 9.0)]
def run(*a): subprocess.run(list(a), check=True)
roh = OUT / f"{cid}_roh.mp4"
w, h = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(roh)],
                      capture_output=True, text=True, check=True).stdout.strip().split(",")
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(roh)]
fc, last = [], "0:v"
for n, (k, url, s, e) in enumerate(EIN, 1):
    p = OUT / f"{cid}_einschnitt_{k}.mp4"
    urllib.request.urlretrieve(B + url, p)
    cmd += ["-i", str(p)]
    tempo = 0.74 if k == "A" else 1.0  # Kling-Clip 4 s auf 2,95 s raffen, damit das Verziehen ganz drin ist
    fc.append(f"[{n}:v]setpts=(PTS-STARTPTS)*{tempo},trim=0:{e - s:.2f},setpts=PTS-STARTPTS+{s}/TB,scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}[e{n}]")
    fc.append(f"[{last}][e{n}]overlay=0:0:eof_action=pass:enable='between(t,{s},{e})'[v{n}]")
    last = f"v{n}"
roh2 = OUT / f"{cid}_roh2.mp4"
run(*cmd, "-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "0:a", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", str(roh2))
shutil.copy(OUT / f"{cid}_roh.words.json", OUT / f"{cid}_roh2.words.json")
skript = "Dein erstes Regal wackelt? Meins auch. Rate mal, warum. Keine Rückwand. Eine dünne Platte hinten drauf, und es steht. Wackelt deins auch?"
fertig = OUT / f"{cid}.mp4"
run("python3", "fertigschnitt.py", str(roh2), "--figur", "mila", "--hook", "Dein Regal wackelt?", "--key", "wackelt?", "--hook-bis", "2.5",
    "--hook-y", "0.40", "--skript", skript, "--out", str(fertig))
for k, t in enumerate([1.0, 3.6, 4.6, 5.6, 6.6, 7.6, 8.6, 9.8]):
    run("ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(fertig), "-frames:v", "1", "-vf", "scale=200:-1", str(OUT / f"{cid}_r{k}.jpg"))
print("ok", fertig)
