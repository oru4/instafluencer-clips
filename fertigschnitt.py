"""Fertigschnitt eines Clips: Hook-Text, optional Bildtext 2 und Untertitel im Stil laut figuren/look_*.md.

Aufruf:
  python fertigschnitt.py <clip.mp4> --figur mila --hook "Vor 1 Jahr: Excel. Heute: das." --key "das."
      [--hook-bis 3] [--hook-y 0.15] [--text2 "sonst siehst du jeden Kratzer" --text2-ab 2.5 --text2-y 0.62]
      [--skript "Gesprochener Text"] [--musik] [--out fertig.mp4]
--skript: Untertitel-Text aus dem Skript, Timing aus <clip>.words.json (vorher transkribieren.py laufen lassen).
--musik: eigene Figurenmusik unterlegen (musik.py), für B-Rolls; bei Off-Stimme automatisch leiser.
--hook-bis: Sekunden, bis zu denen der Hook steht (0 = ganzer Clip). "|" im Text erzwingt einen Zeilenumbruch.
"""
import argparse
import difflib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import musik

# Segoe UI Black (Windows); in der Cloud-Session Ersatz mit ähnlich fetter Schrift
FONT = next((p for p in ("C:/Windows/Fonts/seguibl.ttf", "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
                         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if Path(p).exists()), "seguibl.ttf")
STIL = {
    "mila": {"farbe": "#FFFFFF", "kontur": "#000000", "key": "#E08A3C"},
    "nele": {"farbe": "#FFFFFF", "kontur": "#000000", "key": "#8FBF9F"},
    "hilde": {"farbe": "#FFF6E5", "kontur": "#2A1A12", "key": "#B23A48", "key_kontur": "#FFF6E5"},
}


def probe(clip):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
         "-of", "json", str(clip)], capture_output=True, check=True, text=True).stdout
    j = json.loads(out)
    return j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"])


def umbrechen(text, font, max_w, draw):
    """Bricht nach Breite um; "|" erzwingt einen Zeilenumbruch."""
    if "|" in text:
        return [z for teil in text.split("|") for z in umbrechen(teil.strip(), font, max_w, draw)]
    zeilen, akt = [], ""
    for wort in text.split():
        test = f"{akt} {wort}".strip()
        if draw.textlength(test, font=font) <= max_w or not akt:
            akt = test
        else:
            zeilen.append(akt)
            akt = wort
    return zeilen + [akt]


def text_png(pfad, text, w, h, y_rel, groesse_rel, stil, key=None):
    """Transparentes PNG in Videogrösse mit zentriertem Text; Wörter aus `key` in Akzentfarbe."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    gr = int(h * groesse_rel)
    font = ImageFont.truetype(FONT, gr)
    zeilen = umbrechen(text, font, int(w * 0.88), d)
    max_zeilen = max(2, text.count("|") + 1)
    zu_breit = lambda: any(d.textlength(z, font=font) > w * 0.92 for z in zeilen)
    while (len(zeilen) > max_zeilen or zu_breit()) and gr > 20:
        gr = int(gr * 0.9)
        font = ImageFont.truetype(FONT, gr)
        zeilen = umbrechen(text, font, int(w * 0.88), d)
    key_woerter = set(key.lower().split()) if key else set()
    kontur = max(2, gr // 12)
    y = int(h * y_rel)
    for zeile in zeilen:
        x = (w - d.textlength(zeile, font=font)) / 2
        for i, wort in enumerate(zeile.split()):
            teil = wort if i == 0 else " " + wort
            ist_key = wort.lower() in key_woerter
            farbe = stil["key"] if ist_key else stil["farbe"]
            rand = stil.get("key_kontur", stil["kontur"]) if ist_key else stil["kontur"]
            d.text((x, y), teil, font=font, fill=farbe, stroke_width=kontur, stroke_fill=rand)
            x += d.textlength(teil, font=font)
        y += int(gr * 1.2)
    img.save(pfad)


def untertitel_bloecke(skript, words):
    """Skriptwörter (Originalschreibweise) mit Whisper-Zeitstempeln, Blöcke à max. 3 Wörter."""
    soll = skript.split()
    norm = lambda t: "".join(re.findall(r"[a-zäöüß0-9]+", t.lower()))
    a, b = [norm(t) for t in soll], [norm(w["word"]) for w in words]
    zeit = [None] * len(soll)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if op in ("equal", "replace"):
            for k in range(i2 - i1):
                j = min(j1 + k, j2 - 1)
                zeit[i1 + k] = (words[j]["start"], words[j]["end"])
    # Lücken (nicht erkannte Skriptwörter) aus Nachbarn füllen
    for i in range(len(zeit)):
        if zeit[i] is None:
            vor = next((zeit[k] for k in range(i - 1, -1, -1) if zeit[k]), (words[0]["start"],) * 2)
            nach = next((zeit[k] for k in range(i + 1, len(zeit)) if zeit[k]), (words[-1]["end"],) * 2)
            zeit[i] = (vor[1], nach[0])
    # Blöcke à max. 3 Wörter, nach Satzende/Komma immer neuer Block
    bloecke, akt = [], []
    for i, wort in enumerate(soll):
        akt.append(i)
        if len(akt) == 3 or wort[-1] in ".!?," or i == len(soll) - 1:
            bloecke.append((" ".join(soll[k] for k in akt), zeit[akt[0]][0], zeit[akt[-1]][1]))
            akt = []
    # Block bis zum nächsten stehen lassen, damit Untertitel nicht flackern
    return [(txt, s, bloecke[n + 1][1] if n + 1 < len(bloecke) else e + 0.3) for n, (txt, s, e) in enumerate(bloecke)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--figur", required=True, choices=STIL)
    ap.add_argument("--hook", required=True)
    ap.add_argument("--key")
    ap.add_argument("--hook-bis", type=float, default=3.0)
    ap.add_argument("--hook-y", type=float, default=0.15, help="Oberkante Hook relativ zur Bildhöhe (Sprechclips: unter dem Gesicht)")
    ap.add_argument("--text2")
    ap.add_argument("--text2-ab", type=float, default=2.5)
    ap.add_argument("--text2-y", type=float, default=0.62)
    ap.add_argument("--skript")
    ap.add_argument("--musik", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    clip = Path(a.clip)
    out = Path(a.out) if a.out else clip.with_name(clip.stem + "_fertig.mp4")
    w, h, dauer = probe(clip)
    stil = STIL[a.figur]
    hook_bis = a.hook_bis or dauer

    tmp = Path(tempfile.mkdtemp())
    ebenen = []  # (png, start, ende)
    text_png(tmp / "hook.png", a.hook, w, h, a.hook_y, 0.07, stil, a.key)
    ebenen.append((tmp / "hook.png", 0, hook_bis))
    if a.text2:
        text_png(tmp / "text2.png", a.text2, w, h, a.text2_y, 0.045, stil)
        ebenen.append((tmp / "text2.png", a.text2_ab, dauer))
    if a.skript:
        wj = clip.with_suffix(".words.json")
        if not wj.exists():
            sys.exit(f"{wj} fehlt – zuerst transkribieren.py laufen lassen")
        for n, (txt, s, e) in enumerate(untertitel_bloecke(a.skript, json.loads(wj.read_text(encoding="utf-8")))):
            p = tmp / f"ut{n}.png"
            text_png(p, txt, w, h, 0.62, 0.045, stil)
            ebenen.append((p, s, min(e, dauer)))

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip)]
    for p, _, _ in ebenen:
        cmd += ["-i", str(p)]
    fc, last = [], "0:v"
    for n, (_, s, e) in enumerate(ebenen, 1):
        fc.append(f"[{last}][{n}:v]overlay=0:0:enable='between(t,{s:.2f},{e:.2f})'[v{n}]")
        last = f"v{n}"
    cmd += ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "0:a?", "-c:v", "libx264", "-crf", "18",
            "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    if a.musik:
        musik.unterlegen(out, a.figur, out)
    print(f"{out} ({len(ebenen)} Textebenen, {dauer:.1f} s{', mit Musik' if a.musik else ''})")


if __name__ == "__main__":
    main()
