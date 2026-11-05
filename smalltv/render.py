"""Rendert 240x240-Frames fuer das SmallTV-Ultra mit Pillow.

Das Display ist klein (240x240, ST7789V, RGB565). Darum: grosse Schrift,
hoher Kontrast, wenig Text. JPEG ist auf dem ESP8266 deutlich schneller als PNG.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .config import font

SIZE = 240

# Farbpalette (RGB) - hoher Kontrast fuer das kleine IPS.
BG = (18, 18, 24)
FG = (240, 240, 245)
ACCENT = (120, 200, 255)
MUTED = (140, 140, 155)

def _font(size: int):
    return font(size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """Bricht Text auf max_width um (wortweise)."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        line = ""
        for word in words:
            trial = f"{line} {word}".strip()
            if draw.textlength(trial, font=font) <= max_width or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def render_task(
    text: str,
    title: str = "Aufgabe",
    emoji: str = ":)",
    out_path: str | Path = "/tmp/smalltv_frame.jpg",
) -> Path:
    """Rendert einen Aufgaben-/Hinweis-Frame und speichert ihn als JPEG.

    Gedacht fuer den Companion-Modus: kurze Botschaft, die dir sagt, wo du
    nachschauen sollst oder was ansteht.
    """
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)

    # Kopfzeile
    head_font = _font(20)
    draw.text((14, 12), title.upper(), font=head_font, fill=ACCENT)
    draw.line((14, 40, SIZE - 14, 40), fill=(50, 50, 60), width=2)

    # Haupttext - Schriftgroesse an Laenge anpassen
    body_size = 30 if len(text) <= 40 else (24 if len(text) <= 90 else 19)
    body_font = _font(body_size)
    lines = _wrap(draw, text, body_font, SIZE - 28)
    line_h = body_size + 6
    total_h = line_h * len(lines)
    y = max(52, (SIZE - total_h) // 2)
    for line in lines:
        w = draw.textlength(line, font=body_font)
        draw.text(((SIZE - w) / 2, y), line, font=body_font, fill=FG)
        y += line_h

    # Fusszeile mit kleinem "Gesicht"/Emoji
    foot_font = _font(22)
    draw.text((14, SIZE - 32), emoji, font=foot_font, fill=MUTED)

    out = Path(out_path)
    img.save(out, "JPEG", quality=85)
    return out


def render_status(
    lines: list[tuple[str, str]],
    title: str = "Status",
    out_path: str | Path = "/tmp/smalltv_status.jpg",
) -> Path:
    """Rendert ein einfaches Status-Dashboard (Label/Wert-Paare)."""
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)

    head_font = _font(20)
    draw.text((14, 12), title.upper(), font=head_font, fill=ACCENT)
    draw.line((14, 40, SIZE - 14, 40), fill=(50, 50, 60), width=2)

    label_font = _font(18)
    value_font = _font(22)
    y = 54
    for label, value in lines[:6]:
        draw.text((16, y), label, font=label_font, fill=MUTED)
        vw = draw.textlength(value, font=value_font)
        draw.text((SIZE - 16 - vw, y - 2), value, font=value_font, fill=FG)
        y += 30

    out = Path(out_path)
    img.save(out, "JPEG", quality=85)
    return out
