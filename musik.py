"""Eigene Hintergrundmusik für B-Rolls: per Code synthetisiert, daher ohne Lizenz und ohne Content-ID-Treffer.

Pro Figur ein fester Stil (Mila akustische Gitarre, Nele frisches Marimba mit Beat, Hilde gemütliches E-Piano im
Dreivierteltakt). Ist im Clip schon Sprache (Off-Stimme), wird die Musik leiser und duckt sich unter die Stimme.

Aufruf:
  python musik.py <clip.mp4> --figur mila [--out clip_musik.mp4] [--stimme auto|ja|nein]
  python musik.py --probe probe_mila.wav --figur mila [--dauer 15]
"""
import argparse
import json
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 44100
RNG = np.random.default_rng(7)  # fester Seed: gleiche Figur klingt immer gleich


def hz(note):
    """MIDI-Notennummer → Frequenz."""
    return 440.0 * 2 ** ((note - 69) / 12)


def huellkurve(n, attack=0.005, decay=1.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / attack) * np.exp(-t / decay)


def zupfen(f, dauer, hell=0.5):
    """Gezupfte Saite (Karplus-Strong), blockweise vektorisiert."""
    n, p = int(dauer * SR), max(2, int(SR / f))
    y = np.zeros(n + p + 1)  # y[0] bleibt 0 als Vorgänger des ersten Samples
    glatt = max(1, int(6 * (1 - hell)))
    y[1:p + 1] = np.convolve(RNG.uniform(-1, 1, p), np.ones(glatt) / glatt, "same")  # weicherer Anschlag
    for s in range(p + 1, n + p + 1, p):
        e = min(s + p, n + p + 1)
        y[s:e] = 0.996 * 0.5 * (y[s - p:e - p] + y[s - p - 1:e - p - 1])
    return y[1:n + 1] * huellkurve(n, 0.002, 2.5)


def epiano(f, dauer, tremolo=0.0):
    """Rhodes-ähnlich: Grundton, Oktave, kurzer Glockenanteil."""
    n = int(dauer * SR)
    t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) * huellkurve(n, 0.004, 1.6)
         + 0.3 * np.sin(2 * np.pi * 2 * f * t) * huellkurve(n, 0.004, 0.6)
         + 0.12 * np.sin(2 * np.pi * 7.1 * f * t) * huellkurve(n, 0.001, 0.08))
    return s * (1 - tremolo * (0.5 + 0.5 * np.sin(2 * np.pi * 4.5 * t)))


def marimba(f, dauer):
    n = int(dauer * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) * huellkurve(n, 0.002, 0.35)
            + 0.25 * np.sin(2 * np.pi * 4 * f * t) * huellkurve(n, 0.001, 0.05))


def flaeche(freqs, dauer):
    """Weicher Pad-Akkord mit leichter Verstimmung."""
    n = int(dauer * SR)
    t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * d * t) for f in freqs for d in (0.997, 1.003))
    ein = np.minimum(1, t / 0.4) * np.minimum(1, (dauer - t) / 0.4)
    return s / (2 * len(freqs)) * ein


def bass(f, dauer):
    n = int(dauer * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.2 * np.sin(2 * np.pi * 2 * f * t)) * huellkurve(n, 0.01, 0.5)


def kick(dauer=0.35):
    n = int(dauer * SR)
    t = np.arange(n) / SR
    f = 45 + 75 * np.exp(-t / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * huellkurve(n, 0.001, 0.12)


def rauschen(dauer, decay):
    n = int(dauer * SR)
    x = np.diff(RNG.uniform(-1, 1, n + 1))  # Hochpass: nur Höhen
    return x * huellkurve(n, 0.001, decay)


def hall(x, dauer=1.4, anteil=0.25):
    n = int(dauer * SR)
    ir = RNG.normal(0, 1, n) * np.exp(-np.arange(n) / SR / (dauer / 5))
    ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + n
    nass = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)]
    return (1 - anteil) * x + anteil * nass


def tiefpass(x, fc):
    """Weicher Tiefpass über FFT (Rolloff ab fc)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / fc) ** 4), len(x))


def setzen(spur, klang, zeit, pegel=1.0):
    i = int(zeit * SR)
    if i >= len(spur):
        return
    k = klang[:len(spur) - i]
    spur[i:i + len(k)] += pegel * k


# Akkorde als MIDI-Noten (Grundton im Bass, Rest für die Begleitung)
STILE = {
    "mila": {"bpm": 92, "takt": 4, "tiefpass": 4500, "akkorde": [(43, [55, 59, 62, 67]), (38, [54, 57, 62, 66]),
                                                (40, [55, 59, 64, 67]), (36, [55, 60, 64, 67])]},
    "nele": {"bpm": 112, "takt": 4, "tiefpass": 9000, "akkorde": [(45, [69, 73, 76, 81]), (40, [68, 71, 76, 80]),
                                                 (42, [69, 73, 78, 81]), (38, [69, 74, 78, 81])]},
    "hilde": {"bpm": 84, "takt": 3, "tiefpass": 7000, "akkorde": [(41, [57, 60, 65]), (38, [57, 62, 65]),
                                                 (34, [58, 62, 65]), (36, [55, 60, 64])]},
}


def komponieren(figur, dauer):
    """Stereo-Array (n, 2) in der gewünschten Länge, mit Ein- und Ausblendung."""
    st = STILE[figur]
    schlag = 60 / st["bpm"]
    n = int(dauer * SR)
    L, R = np.zeros(n + SR * 2), np.zeros(n + SR * 2)
    t, i = 0.0, 0
    while t < dauer:
        grund, akk = st["akkorde"][i % len(st["akkorde"])]
        if figur == "mila":
            # Fingerpicking in Achteln: Bass, dann Akkordtöne auf und ab
            muster = [0, 2, 1, 3, 2, 1, 3, 2]
            setzen(L, bass(hz(grund), 2.0), t, 0.5)
            setzen(R, bass(hz(grund), 2.0), t, 0.5)
            for k, m in enumerate(muster):
                ton = zupfen(hz(akk[m]), 2.0, 0.6)
                links = 0.5 + 0.3 * (m % 2 - 0.5)
                setzen(L, ton, t + k * schlag / 2, 0.45 * links)
                setzen(R, ton, t + k * schlag / 2, 0.45 * (1 - links))
                sh = rauschen(0.08, 0.02)
                setzen(R, sh, t + k * schlag / 2, 0.04 if k % 2 else 0.07)
        elif figur == "nele":
            muster = [0, 1, 2, 3, 2, 1, 2, 3]
            for k in range(4):
                if k % 2 == 0:
                    setzen(L, kick(), t + k * schlag, 0.55)
                    setzen(R, kick(), t + k * schlag, 0.55)
                else:
                    setzen(L, rauschen(0.15, 0.05), t + k * schlag, 0.12)  # Klatscher, leise
                for h in (0, 0.5):
                    setzen(R, rauschen(0.05, 0.012), t + (k + h) * schlag, 0.08)
            setzen(L, bass(hz(grund), 0.9), t, 0.55)
            setzen(R, bass(hz(grund), 0.9), t + 2.5 * schlag, 0.4)
            for k, m in enumerate(muster):
                ton = marimba(hz(akk[m]), 0.6)
                setzen(L, ton, t + k * schlag / 2, 0.35 if k % 2 else 0.25)
                setzen(R, ton, t + k * schlag / 2, 0.25 if k % 2 else 0.35)
        else:  # hilde: Walzer, Bass auf 1, Akkord auf 2 und 3, dazu weiche Fläche
            setzen(L, bass(hz(grund), 1.2), t, 0.5)
            setzen(R, bass(hz(grund), 1.2), t, 0.5)
            for k in (1, 2):
                for m, f in enumerate(akk):
                    ton = epiano(hz(f), 1.2, tremolo=0.25)
                    setzen(L if m % 2 else R, ton, t + k * schlag, 0.22)
                    setzen(R if m % 2 else L, ton, t + k * schlag, 0.12)
            pad = flaeche([hz(f) for f in akk], st["takt"] * schlag + 0.3)
            setzen(L, pad, t, 0.12)
            setzen(R, pad, t, 0.12)
            # kleine Melodie: oberster Akkordton, dann einen Schritt tiefer
            setzen(L, epiano(hz(akk[-1] + 12), 1.0), t + 0.02, 0.18)
            setzen(R, epiano(hz(akk[-2] + 12), 1.0), t + 1.5 * schlag, 0.12)
        t += st["takt"] * schlag
        i += 1
    x = np.stack([tiefpass(hall(k[:n]), st["tiefpass"]) for k in (L, R)], axis=1)
    x /= np.sqrt(np.mean(x ** 2)) / 10 ** (-20 / 20)  # RMS auf -20 dBFS
    x = np.tanh(x * 1.2) / 1.2                       # Spitzen weich begrenzen
    tt = np.arange(n) / SR
    x *= (np.minimum(1, tt / 0.05) * np.minimum(1, (dauer - tt) / 0.6))[:, None]
    return x


def wav_schreiben(pfad, x):
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def dauer_von(clip):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(clip)],
                         capture_output=True, check=True, text=True).stdout
    return float(json.loads(out)["format"]["duration"])


def hat_stimme(clip):
    """Mittlerer Pegel über -35 dB → im Clip wird gesprochen (B-Rolls ohne Stimme liegen bei -60 dB und tiefer)."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(clip), "-map", "0:a:0?", "-af", "volumedetect",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    zeile = next((z for z in err.splitlines() if "mean_volume" in z), None)
    return zeile is not None and float(zeile.split("mean_volume:")[1].split("dB")[0]) > -35


def unterlegen(clip, figur, out, stimme="auto"):
    """Mischt die Figurenmusik unter den Clip; Video wird nur kopiert."""
    clip, out = Path(clip), Path(out)
    dauer = dauer_von(clip)
    mit_stimme = hat_stimme(clip) if stimme == "auto" else stimme == "ja"
    wav = Path(tempfile.mkdtemp()) / "musik.wav"
    wav_schreiben(wav, komponieren(figur, dauer))
    hat_ton = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                              "-of", "csv=p=0", str(clip)], capture_output=True, text=True).stdout.strip() != ""
    if not hat_ton:
        fc = "[1:a]anull[a]"
    elif mit_stimme:
        # Musik leise und zusätzlich unter der Stimme weggedrückt
        fc = ("[0:a]asplit[s1][s2];[1:a]volume=-13dB[m];"
              "[m][s1]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350[md];"
              "[s2][md]amix=inputs=2:duration=first:normalize=0[a]")
    else:
        fc = "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]"
    ziel = out if out != clip else out.with_name(out.stem + "_tmp.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-i", str(wav), "-filter_complex", fc,
                    "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", str(SR),
                    "-movflags", "+faststart", str(ziel)], check=True)
    if ziel != out:
        ziel.replace(out)
    return mit_stimme


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip", nargs="?")
    ap.add_argument("--figur", required=True, choices=STILE)
    ap.add_argument("--out")
    ap.add_argument("--stimme", choices=["auto", "ja", "nein"], default="auto")
    ap.add_argument("--probe", help="nur Musik als WAV schreiben")
    ap.add_argument("--dauer", type=float, default=15)
    a = ap.parse_args()
    if a.probe:
        wav_schreiben(a.probe, komponieren(a.figur, a.dauer))
        print(a.probe)
        return
    clip = Path(a.clip)
    out = Path(a.out) if a.out else clip.with_name(clip.stem + "_musik.mp4")
    mit_stimme = unterlegen(clip, a.figur, out, a.stimme)
    print(f"{out} (Musik {a.figur}, {'leise unter Stimme' if mit_stimme else 'ohne Stimme'})")


if __name__ == "__main__":
    main()
