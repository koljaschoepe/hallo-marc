"""Countdown bis zu einem Datum, z.B. Urlaub. Laeuft einmal; fuer taeglich per cron:
    0 7 * * *  cd ~/hallo-marc && .venv/bin/python examples/02_countdown.py

    .venv/bin/python examples/02_countdown.py 2026-12-24 "Weihnachten"
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # damit 'smalltv' gefunden wird

import datetime as dt
import sys

from PIL import Image, ImageDraw

from smalltv.client import SmallTVClient
from smalltv.config import Config, font

ziel = dt.date.fromisoformat(sys.argv[1] if len(sys.argv) > 1 else "2026-12-24")
was = sys.argv[2] if len(sys.argv) > 2 else "Weihnachten"
tage = (ziel - dt.date.today()).days

img = Image.new("RGB", (240, 240), (0, 0, 0))
d = ImageDraw.Draw(img)
d.text((120, 92), str(max(tage, 0)), font=font(96), fill=(90, 222, 236), anchor="mm")
d.text((120, 160), "Tage bis", font=font(20, bold=False), fill=(44, 120, 130), anchor="mm")
d.text((120, 190), was, font=font(24), fill=(90, 222, 236), anchor="mm")
img.save("out/countdown.jpg", quality=90)

SmallTVClient(Config.from_env().ip).push_image("out/countdown.jpg")
