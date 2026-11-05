"""Die Begruessung: Gesicht mit Sprechblase, als ein einziges loopendes GIF.

Das GIF liegt auf dem Geraet und laeuft ohne Rechner und ohne WLAN: Gesicht
blinzelt, zwinkert, laechelt, ab und zu poppt eine Sprechblase auf, dazwischen
eine Karte mit QR-Code zu diesem Repo.

Eigene Botschaften: MESSAGES unten aendern, dann
  python3 -m smalltv.greeting deploy
Nur bauen (Vorschau in out/):
  python3 -m smalltv.greeting build
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from .config import font
from .face import BG, EYE, EYE_DIM, GLINT, EYE_DX, EYE_CY, EYE_W, EYE_H, MOUTH_CY, SIZE

REPO_URL = "https://github.com/koljaschoepe/hallo-marc"
FILENAME = "hallo_marc.gif"

# Reihenfolge der Sprechblasen. Zeilenumbruch mit \n.
MESSAGES = [
    "Hallo Marc!",
    "Viel Spaß\nbeim Basteln!",
    "Liebe Grüße\nvon Kolja",
]

SS = 3                       # Supersampling
# Ohne Blase steht das Gesicht gross in der Mitte. Kommt eine Blase, rueckt es
# weich nach unten und wird etwas kleiner; Blase + Gesicht sind dann zusammen
# vertikal zentriert.
TALK_SCALE = 0.70
TALK_TOP = 84                # y-Versatz des verkleinerten Gesichts
BUBBLE = (16, 20, 224, 90)   # x0, y0, x1, y1 der Sprechblase
INK = (8, 24, 28)            # Schrift in der Blase (fast schwarz)


# ---- Gesicht ---------------------------------------------------------------

def _eye(d, cx, cy, h, state, look=(0, 0)):
    """state: open | closed (Strich) | happy (^-Bogen)."""
    cx, cy = (cx + look[0]) * SS, (cy + look[1]) * SS
    w = EYE_W * SS
    if state == "open":
        hh = h * SS
        d.rounded_rectangle([cx - w / 2, cy - hh / 2, cx + w / 2, cy + hh / 2],
                            radius=min(w, hh) / 2, fill=EYE)
        if h > 18:
            gr = w * 0.17
            gx, gy = cx - w * 0.16, cy - hh * 0.22
            d.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], fill=GLINT)
    else:
        amp = (-16 if state == "happy" else -4) * SS
        cy += 6 * SS
        ww = w + 6 * SS
        pts = [(cx + (t / 20 - 0.5) * ww, cy + math.sin(t / 20 * math.pi) * amp) for t in range(21)]
        d.line(pts, fill=EYE, width=8 * SS, joint="curve")


def _mouth(d, smile):
    cx, cy, half = SIZE / 2 * SS, MOUTH_CY * SS, 26 * SS
    pts = [(cx + (t / 20 - 0.5) * 2 * half, cy + math.sin(t / 20 * math.pi) * smile * 22 * SS)
           for t in range(21)]
    d.line(pts, fill=EYE, width=7 * SS, joint="curve")


def _face(left="open", right="open", h=EYE_H, smile=0.5, look=(0, 0)) -> Image.Image:
    img = Image.new("RGB", (SIZE * SS, SIZE * SS), BG)
    d = ImageDraw.Draw(img)
    lx, rx = SIZE / 2 - EYE_DX, SIZE / 2 + EYE_DX
    _eye(d, lx, EYE_CY, h, left, look)
    _eye(d, rx, EYE_CY, h, right, look)
    _mouth(d, smile)
    return img


def _compose(face: Image.Image, bubble: str | None = None, pop: float = 1.0,
             k: float = 0.0) -> Image.Image:
    """k = 0: Gesicht gross und mittig. k = 1: Gesicht klein unten, Platz fuer Blase.
    pop = Skalierung der Blase (0..1)."""
    out = Image.new("RGB", (SIZE * SS, SIZE * SS), BG)
    e = k * k * (3 - 2 * k)                       # weiches Ein-/Ausblenden
    scale = 1 + (TALK_SCALE - 1) * e
    top = TALK_TOP * e
    fs = int(SIZE * SS * scale)
    small = face.resize((fs, fs), Image.LANCZOS) if fs != SIZE * SS else face
    out.paste(small, ((SIZE * SS - fs) // 2, int(top * SS + (SIZE * SS - fs) * (1 - e) / 2)))
    if bubble:
        _bubble(out, bubble, pop)
    return out.resize((SIZE, SIZE), Image.LANCZOS)


def _bubble(img: Image.Image, text: str, pop: float) -> None:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = (v * SS for v in BUBBLE)
    # Zipfel zeigt nach unten zum Gesicht
    tx = SIZE / 2 * SS
    d.polygon([(tx - 14 * SS, y1 - 4 * SS), (tx + 10 * SS, y1 - 4 * SS), (tx - 6 * SS, y1 + 16 * SS)], fill=EYE)
    d.rounded_rectangle([x0, y0, x1, y1], radius=20 * SS, fill=EYE)
    lines = text.split("\n")
    size = 28 if len(lines) == 1 else 22
    f = font(size * SS)
    lh = (size + 4) * SS
    cy = (y0 + y1) / 2 - lh * (len(lines) - 1) / 2
    for i, line in enumerate(lines):
        d.text((tx, cy + i * lh), line, font=f, fill=INK, anchor="mm")
    if pop < 1.0:
        # Pop-Effekt: Blase waechst vom Zipfel aus
        w, h = layer.size
        sw, sh = max(1, int(w * pop)), max(1, int(h * pop))
        scaled = layer.resize((sw, sh), Image.LANCZOS)
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ax, ay = int(tx), int(y1 + 16 * SS)
        layer.paste(scaled, (int(ax - ax * pop), int(ay - ay * pop)))
    img.paste(layer, (0, 0), layer)


def _qr_card() -> Image.Image:
    import qrcode
    qr = qrcode.QRCode(border=2, box_size=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(REPO_URL)
    qr.make(fit=True)
    q = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    n = q.size[0]
    box = 168 // n
    q = q.resize((n * box, n * box), Image.NEAREST)
    qs = q.size[0]
    title_h, cap_h, gap = 24, 16, 10
    total = title_h + gap + qs + gap + cap_h
    y = (SIZE - total) // 2
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)
    d.text((SIZE // 2, y + title_h // 2), "Scan mich!", font=font(24), fill=EYE, anchor="mm")
    img.paste(q, ((SIZE - qs) // 2, y + title_h + gap))
    d.text((SIZE // 2, y + title_h + gap + qs + gap + cap_h // 2), "Code & Anleitung",
           font=font(16), fill=EYE_DIM, anchor="mm")
    return img


# ---- Ablauf ----------------------------------------------------------------

def _sequence():
    frames: list[Image.Image] = []
    durs: list[int] = []

    def add(img, ms):
        frames.append(img)
        durs.append(ms)

    def idle(seconds, look=(0, 0)):
        add(_compose(_face(look=look)), int(seconds * 1000))

    def blink(look=(0, 0)):
        for h in (24, 8, 24):
            add(_compose(_face(h=h, look=look)), 50)

    def glance(dx, hold=0.9):
        """Augen gleiten zur Seite, verweilen, gleiten zurueck."""
        for t in (0.35, 0.75, 1.0):
            add(_compose(_face(look=(dx * t, 0))), 55)
        add(_compose(_face(look=(dx, 0))), int(hold * 1000))
        for t in (0.6, 0.2):
            add(_compose(_face(look=(dx * t, 0))), 55)

    def wink():
        add(_compose(_face(right="closed", smile=0.7)), 90)
        add(_compose(_face(right="closed", smile=0.8)), 600)
        add(_compose(_face(smile=0.6)), 60)

    def say(text, hold=2.0):
        # Gesicht rueckt nach unten
        for k in (0.2, 0.45, 0.7, 0.9, 1.0):
            add(_compose(_face(smile=0.6), k=k), 45)
        happy = _face(left="happy", right="happy", smile=0.95)
        for p in (0.35, 0.7, 0.92):
            add(_compose(happy, text, pop=p, k=1), 55)
        add(_compose(happy, text, k=1), int(hold * 1000))
        add(_compose(_face(smile=0.8), text, k=1), 450)   # Augen wieder auf, Blase bleibt
        for p in (0.6, 0.25):
            add(_compose(_face(smile=0.7), text, pop=p, k=1), 55)
        # und zurueck in die Mitte
        for k in (0.8, 0.55, 0.3, 0.1):
            add(_compose(_face(smile=0.6), k=k), 45)

    # Auftakt: aufwachen
    for h in (6, 20, 38, EYE_H):
        add(_compose(_face(h=h, smile=0.3)), 90)
    idle(0.8)
    blink()
    say(MESSAGES[0])
    idle(1.2)
    glance(12, hold=0.6)
    glance(-12, hold=0.6)
    blink()
    wink()
    idle(0.8)
    say(MESSAGES[1], hold=2.4)
    idle(1.0)
    glance(-12, hold=0.7)
    blink()
    say(MESSAGES[2], hold=2.4)
    idle(1.0)
    wink()
    idle(0.6)
    add(_qr_card(), 15000)
    idle(1.0)
    blink()
    glance(12, hold=0.7)
    idle(0.8)
    return frames, durs


def build(out_dir: str | Path = "out") -> Path:
    frames, durs = _sequence()
    pal = [f.quantize(colors=48, method=Image.MEDIANCUT) for f in frames]
    out = Path(out_dir) / FILENAME
    out.parent.mkdir(parents=True, exist_ok=True)
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durs,
                loop=0, optimize=True, disposal=1)
    return out


def deploy() -> None:
    from .client import SmallTVClient
    from .config import Config
    cfg = Config.from_env()
    p = build()
    print(f"  {p}: {p.stat().st_size // 1024} KB")
    c = SmallTVClient(cfg.ip, image_theme=cfg.image_theme)
    c._get("/set", autoplay=0)
    c.push_image(p)
    print("  laeuft.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "build":
        p = build()
        print(f"  {p}: {p.stat().st_size // 1024} KB")
    elif cmd == "deploy":
        deploy()
    else:
        print(__doc__)
