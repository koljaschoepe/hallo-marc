"""Eigenes animiertes GIF: ein huepfender Ball. Zeigt, wie Animationen gebaut werden.
Tipps: wenige Farben (quantize), kleine Dateien (< 300 KB), 40-120 ms pro Frame.

    .venv/bin/python examples/03_animation.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # damit 'smalltv' gefunden wird

import math

from PIL import Image, ImageDraw

from smalltv.client import SmallTVClient
from smalltv.config import Config

frames = []
for i in range(24):
    t = i / 24
    y = 190 - abs(math.sin(t * math.pi * 2)) * 130     # Huepfen
    squash = 1.25 if y > 180 else 1.0                    # beim Aufprall platt
    img = Image.new("RGB", (240, 240), (0, 0, 0))
    d = ImageDraw.Draw(img)
    r = 22
    d.ellipse([120 - r * squash, y - r / squash, 120 + r * squash, y + r / squash], fill=(240, 200, 92))
    d.line([(40, 214), (200, 214)], fill=(44, 120, 130), width=3)
    frames.append(img.quantize(colors=16))

frames[0].save("out/ball.gif", save_all=True, append_images=frames[1:],
               duration=50, loop=0, optimize=True, disposal=2)

SmallTVClient(Config.from_env().ip).push_image("out/ball.gif")
