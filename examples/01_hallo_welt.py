"""Das kleinste moegliche Programm: Text rendern, hochladen, anzeigen.

    .venv/bin/python examples/01_hallo_welt.py "Moin!"
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # damit 'smalltv' gefunden wird

import sys

from PIL import Image, ImageDraw

from smalltv.client import SmallTVClient
from smalltv.config import Config, font

text = sys.argv[1] if len(sys.argv) > 1 else "Hallo Welt"

img = Image.new("RGB", (240, 240), (0, 0, 0))          # das Display hat 240x240 px
d = ImageDraw.Draw(img)
d.text((120, 120), text, font=font(30), fill=(90, 222, 236), anchor="mm")
img.save("out/hallo.jpg", quality=90)                   # JPEG laedt am schnellsten

cfg = Config.from_env()
SmallTVClient(cfg.ip).push_image("out/hallo.jpg")       # hochladen + anzeigen
