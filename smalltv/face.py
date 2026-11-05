"""Generiert das Gesicht als kleine, loopende 240x240-GIFs (minimalistisch).

Stil: freundliche Roboter-Augen + Mund auf SCHWARZEM Grund (Cozmo/Vector-Vibe).
Default ist eine MOTIVIERTE, positive Haltung (laechelt). Alle Stimmungen teilen
dieselbe Kopf-/Augenposition, damit Wechsel fluessig wirken. Die Augen tragen einen
kleinen Glanzpunkt (Highlight), das gibt Tiefe und wirkt lebendig.

Stimmungen:
  neutral   - Default, motiviert/positiv, atmet + Mikro-Sakkaden + organisches Blinzeln
  happy     - deutliches Laecheln, froehliche Bogen-Augen
  listening - aufmerksam, mit eingebackenem Aufwach-Auftakt, dann sanftes Pulsieren
  thinking  - Augen wandern nach oben
  speaking  - Mund spricht (leicht positiv)
  sad       - selten, Mund nach unten, Augen haengen

Aufruf:  python3 -m smalltv.face build [ausgabeordner]
Aufs Geraet:  python3 -m smalltv.face deploy   |   python3 -m smalltv.face show happy
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 240
SS = 3                       # Supersampling fuer glatte Kanten
BG = (0, 0, 0)              # echtes Schwarz
EYE = (90, 222, 236)       # freundliches Cyan
EYE_DIM = (44, 120, 130)
GLINT = (200, 246, 252)    # heller Glanzpunkt im Auge (Highlight, eine Lichtquelle oben-links)

EYE_DX = 40
EYE_CY = 90          # etwas hoeher (war 104), Gesicht leicht oberhalb der Mitte
EYE_W = 34
EYE_H = 50
MOUTH_CY = 154       # entsprechend hoeher (war 170)


def _canvas():
    img = Image.new("RGB", (SIZE * SS, SIZE * SS), BG)
    return img, ImageDraw.Draw(img)


def _eye_capsule(draw, cx, cy, w, h, color, look=(0, 0)):
    cx = (cx + look[0]) * SS
    cy = (cy + look[1]) * SS
    w *= SS
    h *= SS
    r = min(w, h) / 2
    draw.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2],
                           radius=r, fill=color)
    # Glanzpunkt nur bei ausreichend offenem Auge (nicht waehrend des Blinzelns).
    if h > 18 * SS:
        gr = w * 0.17
        gx = cx - w * 0.16        # oben-links -> konsistente Lichtquelle auf beiden Augen
        gy = cy - h * 0.22
        draw.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], fill=GLINT)


def _eye_arc(draw, cx, cy, w, color, look=(0, 0), down=False):
    """Froehliches Bogen-Auge (^) bzw. haengendes Auge (v bei down=True)."""
    cx = (cx + look[0]) * SS
    cy = (cy + look[1]) * SS
    w *= SS
    amp = 16 * SS * (1 if down else -1)
    pts = []
    for i in range(0, 21):
        t = i / 20
        x = cx + (t - 0.5) * w
        y = cy + math.sin(t * math.pi) * amp
        pts.append((x, y))
    draw.line(pts, fill=color, width=int(8 * SS), joint="curve")


def _mouth(draw, openness=0.0, smile=0.4, color=EYE):
    """smile>0 = Laecheln (U), smile<0 = traurig, openness>0 = offener Mund."""
    cx = SIZE / 2 * SS
    cy = MOUTH_CY * SS
    half = 26 * SS
    if openness > 0.05:
        h = (6 + openness * 26) * SS
        draw.rounded_rectangle([cx - half * 0.7, cy - h / 2, cx + half * 0.7, cy + h / 2],
                               radius=min(half * 0.7, h / 2), fill=color)
    else:
        pts = []
        for i in range(0, 21):
            t = i / 20
            x = cx + (t - 0.5) * 2 * half
            # +sin -> Mitte tiefer -> U-Form -> Laecheln (bei smile>0)
            y = cy + math.sin(t * math.pi) * smile * 22 * SS
            pts.append((x, y))
        draw.line(pts, fill=color, width=int(7 * SS), joint="curve")


def _finish(img):
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def _frame(eye_h=EYE_H, eye_w=EYE_W, look=(0, 0), color=EYE,
           mouth_open=0.0, smile=0.4, eyes="capsule") -> Image.Image:
    img, d = _canvas()
    lx = SIZE / 2 - EYE_DX
    rx = SIZE / 2 + EYE_DX
    if eyes == "capsule":
        _eye_capsule(d, lx, EYE_CY, eye_w, eye_h, color, look)
        _eye_capsule(d, rx, EYE_CY, eye_w, eye_h, color, look)
    elif eyes == "happy":
        _eye_arc(d, lx, EYE_CY + 6, eye_w + 6, color, look, down=False)
        _eye_arc(d, rx, EYE_CY + 6, eye_w + 6, color, look, down=False)
    elif eyes == "sad":
        _eye_arc(d, lx, EYE_CY - 4, eye_w + 4, color, look, down=True)
        _eye_arc(d, rx, EYE_CY - 4, eye_w + 4, color, look, down=True)
    _mouth(d, openness=mouth_open, smile=smile, color=color)
    return _finish(img)


# ---- Stimmungs-Sequenzen ----------------------------------------------------

def _frames_neutral():
    """Motiviert/positiv und LEBENDIG, aber kompakt (laedt schnell aufs ESP):
    sanftes Atmen (Augen-Pulsieren), Mikro-Sakkaden (winzige Blickspruenge) und
    organisches, ungleichmaessiges Blinzeln."""
    smile = 0.5
    frames, durs = [], []

    def breathe(n, look=(0, 0)):
        for i in range(n):
            eh = 50 + math.sin(i / max(1, n) * 2 * math.pi) * 2   # Atmen 48..52
            frames.append(_frame(eye_h=eh, smile=smile, look=look)); durs.append(130)

    def blink(look=(0, 0)):
        for h in (50, 24, 8, 24, 50):
            frames.append(_frame(eye_h=h, smile=smile, look=look)); durs.append(45)

    breathe(6)
    blink()                       # erstes Blinzeln
    breathe(5, look=(3, 0))       # kurze Sakkade nach rechts
    blink()                       # zweites Blinzeln
    breathe(6, look=(-3, 1))      # Sakkade nach links
    return frames, durs


def _frames_happy():
    """Deutliches Laecheln, froehliche Bogen-Augen, kleiner Huepfer."""
    frames, durs = [], []
    for dy in (0, -3, -5, -3, 0, 0):
        img, d = _canvas()
        lx, rx = SIZE / 2 - EYE_DX, SIZE / 2 + EYE_DX
        _eye_arc(d, lx, EYE_CY + 6, EYE_W + 6, EYE, (0, dy))
        _eye_arc(d, rx, EYE_CY + 6, EYE_W + 6, EYE, (0, dy))
        _mouth(d, smile=0.95)
        frames.append(_finish(img)); durs.append(150)
    return frames, durs


def _frames_listening():
    """Aufmerksam: kurzer Aufwach-Auftakt (Augen oeffnen sich) EINGEBACKEN, dann
    sanftes Pulsieren. So 'wacht' das Gesicht sichtbar auf, ohne
    einen zweiten (langsamen) Bildwechsel auf dem ESP zu kosten."""
    frames, durs = [], []
    for h, w in [(8, 30), (24, 33), (44, 36), (58, 39)]:   # Aufwach-Auftakt
        frames.append(_frame(eye_h=h, eye_w=w, smile=0.35)); durs.append(55)
    for i in range(12):                                     # aufmerksames Pulsieren
        p = (math.sin(i / 12 * 2 * math.pi) + 1) / 2
        col = tuple(int(EYE_DIM[k] + (EYE[k] - EYE_DIM[k]) * (0.5 + 0.5 * p)) for k in range(3))
        frames.append(_frame(eye_h=50 + p * 8, eye_w=34 + p * 4, color=col, smile=0.35))
        durs.append(85)
    return frames, durs


def _frames_thinking():
    """Augen wandern nach oben/seitlich, neutraler Mund."""
    frames, durs = [], []
    path = [(-6, -10), (-3, -13), (0, -14), (3, -13), (6, -10),
            (6, -10), (3, -13), (0, -14), (-3, -13), (-6, -10)]
    for lx, ly in path:
        frames.append(_frame(look=(lx, ly), eye_h=44, smile=0.1)); durs.append(160)
    return frames, durs


def _frames_speaking():
    """Mund bewegt sich (spricht), leicht positiv."""
    frames, durs = [], []
    for o in (0.1, 0.6, 0.9, 0.4, 0.8, 0.2, 0.7, 0.3):
        frames.append(_frame(mouth_open=o, smile=0.2)); durs.append(110)
    return frames, durs


def _frames_sad():
    """Selten: Mund nach unten, haengende Augen."""
    frames, durs = [], []
    base = _frame(smile=-0.5, eyes="sad")
    for _ in range(14):
        frames.append(base); durs.append(150)
    for h in (40, 26, 40):
        frames.append(_frame(eye_h=h, smile=-0.5)); durs.append(60)
    return frames, durs


BUILDERS = {
    "neutral": _frames_neutral,
    "happy": _frames_happy,
    "listening": _frames_listening,
    "thinking": _frames_thinking,
    "speaking": _frames_speaking,
    "sad": _frames_sad,
}


def build_gif(emotion: str, out_path) -> Path:
    frames, durations = BUILDERS[emotion]()
    # Gesicht = Schwarz + ein paar Cyan-Toene + Glanz -> wenige Farben reichen und
    # halten die GIFs klein (schnelleres Laden auf dem ESP).
    pal_frames = [f.quantize(colors=16, method=Image.MEDIANCUT) for f in frames]
    out = Path(out_path)
    pal_frames[0].save(out, save_all=True, append_images=pal_frames[1:],
                       duration=durations, loop=0, optimize=True, disposal=2)
    return out


def build_all(outdir="out") -> list[Path]:
    d = Path(outdir)
    d.mkdir(parents=True, exist_ok=True)
    paths = []
    for emo in BUILDERS:
        p = build_gif(emo, d / f"face_{emo}.gif")
        paths.append(p)
        print(f"  {p.name}: {p.stat().st_size} bytes")
    return paths


def deploy(outdir="out") -> None:
    """Alle Stimmungen bauen, hochladen und 'neutral' anzeigen."""
    from .client import SmallTVClient
    from .config import Config
    cfg = Config.from_env()
    c = SmallTVClient(cfg.ip, image_theme=cfg.image_theme)
    for p in build_all(outdir):
        print(f"  lade hoch: {p.name}")
        c.upload_image(p)
    show("neutral")


def show(emotion: str) -> None:
    """Zeigt eine bereits hochgeladene Stimmung (dauert ~1 s am ESP8266)."""
    from .client import SmallTVClient
    from .config import Config
    cfg = Config.from_env()
    c = SmallTVClient(cfg.ip, image_theme=cfg.image_theme)
    c._get("/set", autoplay=0)
    c.show_image(f"face_{emotion}.gif")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "build":
        print("Baue Gesichter ...")
        build_all(sys.argv[2] if len(sys.argv) > 2 else "out")
    elif cmd == "deploy":
        deploy()
    elif cmd == "show":
        show(sys.argv[2] if len(sys.argv) > 2 else "neutral")
    else:
        print("Nutzung: python3 -m smalltv.face build|deploy|show <" + "|".join(BUILDERS) + ">")
