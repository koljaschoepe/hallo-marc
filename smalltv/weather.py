"""Wetter-Bild: cleanes 240x240-GIF im Cyan-Roboter-Stil (passt zu face.py).

Holt aktuelle Wetterdaten von Open-Meteo (kein API-Key) fuer den Ort aus der .env und rendert
ein animiertes GIF:
  - grosse Uhr HH:MM
  - Wochentag + Datum (deutsch)
  - Temperatur + vektorisiertes Wetter-Symbol
  - wetterabhaengige Hintergrund-Animation (Regentropfen / Sonnenstrahlen /
    ziehende Wolken / Schneeflocken / Nebel)

Die Uhr ist im GIF "eingebacken" - das Bild muss also regelmaessig (jede Minute)
neu gerendert und aufs Geraet gepusht werden, damit die Uhrzeit stimmt. Die
Wetterdaten werden zwischengespeichert (WEATHER_TTL), nur die Uhr aendert sich
minuetlich.

CLI:  python3 -m smalltv.weather build [ausgabeordner]
"""

from __future__ import annotations

import json
import math
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

# ---- Stil (identisch zu face.py) ----------------------------------------
SIZE = 240
SS = 3                       # Supersampling fuer glatte Kanten
BG = (0, 0, 0)
EYE = (90, 222, 236)         # freundliches Cyan (Hauptfarbe)
EYE_DIM = (44, 120, 130)     # gedimmtes Cyan (Sekundaertext)
ANIM = (34, 92, 102)         # noch dunkler: Hintergrund-Animation, Text bleibt lesbar

from .config import LAT, LON, LOCATION_NAME, font as _cfg_font

# ---- Ort + Datenquelle --------------------------------------------------
URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&current=temperature_2m,apparent_temperature,weather_code,is_day"
    ",wind_speed_10m,wind_direction_10m"
    "&hourly=precipitation_probability"
    "&daily=temperature_2m_max,temperature_2m_min"
    "&timezone=Europe%2FBerlin&forecast_days=2"
)
WEATHER_TTL = 600            # Wetter hoechstens alle 10 Min neu holen

WD = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
MON = ("Januar", "Februar", "Maerz", "April", "Mai", "Juni", "Juli",
       "August", "September", "Oktober", "November", "Dezember")

NUM_FRAMES = 12
FRAME_MS = 110
DROPS_X = (22, 58, 96, 128, 150, 186, 214)

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Europe/Berlin")
except Exception:  # pragma: no cover
    _TZ = None

_cache: dict = {"data": None, "ts": 0.0}


def _font(size: int):
    return _cfg_font(size)


def _now():
    import datetime as dt
    return dt.datetime.now(_TZ) if _TZ else dt.datetime.now()


# ---- Wetter holen -------------------------------------------------------

def fetch_weather() -> dict:
    try:
        with urllib.request.urlopen(URL, timeout=8) as r:
            j = json.loads(r.read())
        cur = j.get("current", {})
        daily = j.get("daily", {})
        hourly = j.get("hourly", {})
        # Regenwahrscheinlichkeit: hoechster Wert der naechsten 6h ab aktueller Stunde
        rain = None
        times = hourly.get("time", []) or []
        probs = hourly.get("precipitation_probability", []) or []
        key = _now().strftime("%Y-%m-%dT%H:00")
        if key in times:
            i = times.index(key)
            seg = [p for p in probs[i:i + 6] if p is not None]
            rain = max(seg) if seg else None
        return {
            "temp": cur.get("temperature_2m"),
            "apparent_temp": cur.get("apparent_temperature"),
            "code": int(cur.get("weather_code", 0)),
            "is_day": bool(cur.get("is_day", 1)),
            "tmax": (daily.get("temperature_2m_max") or [None])[0],
            "tmin": (daily.get("temperature_2m_min") or [None])[0],
            "rain": rain,
            "wind_speed": cur.get("wind_speed_10m"),
            "wind_dir": cur.get("wind_direction_10m"),
            "ok": True,
        }
    except Exception:
        return {"temp": None, "apparent_temp": None, "code": -1, "is_day": True,
                "tmax": None, "tmin": None, "rain": None,
                "wind_speed": None, "wind_dir": None, "ok": False}


def get_weather() -> dict:
    """Gecachte Wetterdaten - holt hoechstens alle WEATHER_TTL Sekunden neu."""
    if _cache["data"] is None or (time.time() - _cache["ts"]) > WEATHER_TTL:
        d = fetch_weather()
        if d["ok"] or _cache["data"] is None:
            _cache["data"], _cache["ts"] = d, time.time()
    return _cache["data"]


def _category(code: int) -> str:
    if code == 0:
        return "clear"
    if code in (1, 2):
        return "partly"
    if code == 3:
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    return "cloudy"


# ---- Zeichnen -----------------------------------------------------------

def _cloud(d, cx, cy, r, color=EYE):
    s = SS
    d.ellipse([(cx - r) * s, (cy - r * 0.5) * s, cx * s, (cy + r * 0.5) * s], fill=color)
    d.ellipse([(cx - r * 0.4) * s, (cy - r) * s, (cx + r * 0.6) * s, (cy + r * 0.4) * s], fill=color)
    d.ellipse([cx * s, (cy - r * 0.4) * s, (cx + r) * s, (cy + r * 0.6) * s], fill=color)
    d.rectangle([(cx - r) * s, cy * s, (cx + r) * s, (cy + r * 0.5) * s], fill=color)


def _draw_symbol(d, cx, cy, r, cat, is_day):
    s = SS
    if cat == "clear":
        if is_day:
            d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=EYE)
        else:  # Mondsichel
            d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=EYE)
            d.ellipse([(cx - r + 9) * s, (cy - r) * s, (cx + r + 9) * s, (cy + r) * s], fill=BG)
    elif cat == "partly":
        d.ellipse([(cx - r) * s, (cy - r - 2) * s, (cx + r - 8) * s, (cy + r - 10) * s], fill=EYE)
        _cloud(d, cx, cy + 4, r * 0.9)
    elif cat in ("cloudy", "fog"):
        _cloud(d, cx, cy, r)
    elif cat in ("rain", "storm"):
        _cloud(d, cx, cy - 4, r)
        for j in range(3):
            x = cx - 8 + j * 8
            d.line([(x * s, (cy + 10) * s), ((x - 3) * s, (cy + 20) * s)], fill=EYE, width=2 * s)
    elif cat == "snow":
        _cloud(d, cx, cy - 4, r)
        for j in range(3):
            x = cx - 8 + j * 8
            d.ellipse([(x - 2) * s, (cy + 12) * s, (x + 2) * s, (cy + 16) * s], fill=EYE)


def _draw_anim(d, t, cat, is_day):
    s = SS
    if cat in ("rain", "storm"):
        for i, x in enumerate(DROPS_X):
            ph = (i * 0.137) % 1.0
            y = ((t + ph) % 1.0) * (SIZE + 24) - 12
            d.line([(x * s, y * s), ((x - 4) * s, (y + 16) * s)], fill=ANIM, width=2 * s)
    elif cat == "snow":
        for i, x in enumerate(DROPS_X):
            ph = (i * 0.211) % 1.0
            prog = (t + ph) % 1.0
            y = prog * (SIZE + 24) - 12
            xx = x + math.sin((prog * 2 + i) * math.pi) * 6
            d.ellipse([(xx - 3) * s, (y - 3) * s, (xx + 3) * s, (y + 3) * s], fill=ANIM)
    elif cat in ("clear", "partly"):
        # sanft rotierende Strahlen ums Symbol neben der Temperatur
        cx, cy = 198, 142
        for k in range(8):
            a = (k / 8) * 2 * math.pi + t * (2 * math.pi / 8)
            x1, y1 = cx + math.cos(a) * 20, cy + math.sin(a) * 20
            x2, y2 = cx + math.cos(a) * 28, cy + math.sin(a) * 28
            d.line([(x1 * s, y1 * s), (x2 * s, y2 * s)], fill=ANIM, width=2 * s)
    else:  # cloudy / fog -> ziehende Nebelschwaden
        for i in range(3):
            base_y = (44, 124, 200)[i]
            x = ((t + i * 0.33) % 1.0) * SIZE
            for off in (-SIZE, 0):
                d.line([((x + off) * s, base_y * s), ((x + off + 64) * s, base_y * s)],
                       fill=ANIM, width=3 * s)


def _frame(t, w, timestr, datestr) -> Image.Image:
    img = Image.new("RGB", (SIZE * SS, SIZE * SS), BG)
    d = ImageDraw.Draw(img)
    s = SS
    cat, is_day = w["category"], w["is_day"]

    _draw_anim(d, t, cat, is_day)                       # Hintergrund-Animation (dim)
    _draw_symbol(d, 198, 142, 16, cat, is_day)          # Wetter-Symbol neben der Temperatur

    # Uhr (gross, mittig)
    d.text((120 * s, 62 * s), timestr, font=_font(70 * s), fill=EYE, anchor="mm")
    # Trennlinie
    d.line([(62 * s, 102 * s), (178 * s, 102 * s)], fill=EYE_DIM, width=3 * s)
    # Temperatur (etwas nach links, damit rechts Platz fuers Symbol ist)
    d.text((108 * s, 142 * s), w["temp_str"], font=_font(60 * s), fill=EYE, anchor="mm")
    # Ort
    d.text((120 * s, 180 * s), LOCATION_NAME, font=_font(22 * s), fill=EYE_DIM, anchor="mm")
    # Datum
    d.text((120 * s, 210 * s), datestr, font=_font(24 * s), fill=EYE, anchor="mm")

    return img.resize((SIZE, SIZE), Image.LANCZOS)


def render(out_path: str | Path) -> Path:
    """Rendert das aktuelle Idle-GIF (Wetter + Uhr) nach out_path."""
    w = dict(get_weather())
    w["category"] = _category(w["code"])
    w["temp_str"] = f"{round(w['temp'])}°" if w["temp"] is not None else "--°"

    n = _now()
    timestr = n.strftime("%H:%M")
    datestr = f"{WD[n.weekday()]} · {n.day}. {MON[n.month - 1]}"

    frames, durs = [], []
    for i in range(NUM_FRAMES):
        frames.append(_frame(i / NUM_FRAMES, w, timestr, datestr))
        durs.append(FRAME_MS)

    pal = [f.quantize(colors=32, method=Image.MEDIANCUT) for f in frames]
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durs,
                loop=0, optimize=True, disposal=2)
    return out


# ---- Wetter-Karte (kurzer Idle-Blink, Tafel-Stil) -----------------------
# Designsprache identisch zur OEPNV-Abfahrtstafel (Kopf + Trennlinien + Hero +
# Info-Zeile). Bewusst OHNE Uhr: die Tafel zeigt die Zeit, die Karte zeigt Datum,
# grosse Temperatur, neu gezeichnetes Wetter-Icon sowie Tageshoch/-tief und
# Regenwahrscheinlichkeit. Der Inhalt aendert sich nur bei Temp/Tag/Wetter/Max/
# Min/Regen - nur dann muss neu aufs Geraet geschrieben werden (card_key spart
# Uploads, schont den ESP8266-Flash; die Tafel laedt ohnehin minuetlich).

# Akzentfarben (sparsam eingesetzt, sonst bleibt der Cyan-Robot-Stil):
SUN = (240, 200, 92)         # warmes Gold (Sonne, Blitz, Tageshoch)
RAIN = (96, 165, 240)        # Regen-Blau (Tropfen, Tagestief)
SNOW = (224, 238, 248)       # fast weiss (Schneeflocken)


def _disc(d, cx, cy, r, fill):
    s = SS
    d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=fill)


def _wx_cloud(d, cx, cy, w, color=EYE):
    """Saubere, runde Wolke um (cx, cy) mit Halbbreite w (logische px)."""
    s = SS
    r = w * 0.52
    d.rounded_rectangle([(cx - w) * s, (cy - r * 0.15) * s, (cx + w) * s, (cy + r) * s],
                        radius=r * s, fill=color)
    _disc(d, cx - w * 0.50, cy - r * 0.05, r * 0.72, color)
    _disc(d, cx + w * 0.42, cy - r * 0.02, r * 0.62, color)
    _disc(d, cx - w * 0.02, cy - r * 0.72, r * 0.98, color)
    _disc(d, cx + w * 0.40, cy - r * 0.45, r * 0.60, color)


def _wx_sun(d, cx, cy, r, color=SUN):
    s = SS
    for k in range(8):
        a = k / 8 * 2 * math.pi
        x1, y1 = cx + math.cos(a) * r * 1.45, cy + math.sin(a) * r * 1.45
        x2, y2 = cx + math.cos(a) * r * 1.95, cy + math.sin(a) * r * 1.95
        d.line([(x1 * s, y1 * s), (x2 * s, y2 * s)], fill=color, width=max(1, int(r * 0.32 * s)))
    _disc(d, cx, cy, r, color)


def _wx_moon(d, cx, cy, r, color=EYE):
    _disc(d, cx, cy, r, color)
    _disc(d, cx + r * 0.55, cy - r * 0.35, r * 0.92, BG)   # Sichel ausstanzen
    _disc(d, cx + r * 1.05, cy - r * 0.6, r * 0.14, color)  # kleiner Stern


def _wx_rain(d, cx, cy, color=RAIN, n=3):
    s = SS
    for j in range(n):
        x = cx + (j - (n - 1) / 2) * 13
        d.line([(x * s, cy * s), ((x - 4) * s, (cy + 14) * s)], fill=color, width=max(1, int(2.6 * s)))


def _wx_snow(d, cx, cy, color=SNOW, n=3):
    s = SS
    for j in range(n):
        x = cx + (j - (n - 1) / 2) * 13
        for k in range(3):
            a = k / 3 * math.pi
            dx, dy = math.cos(a) * 4.8, math.sin(a) * 4.8
            d.line([((x - dx) * s, (cy - dy) * s), ((x + dx) * s, (cy + dy) * s)],
                   fill=color, width=max(1, int(1.6 * s)))


def _wx_bolt(d, cx, cy, color=SUN):
    s = SS
    pts = [(cx + 2, cy - 11), (cx - 6, cy + 3), (cx - 1, cy + 3),
           (cx - 3, cy + 14), (cx + 8, cy - 2), (cx + 1, cy - 2)]
    d.polygon([(x * s, y * s) for x, y in pts], fill=color)


def _wx_icon(d, cx, cy, cat, is_day, scale=1.0):
    """Neu gezeichnetes Wetter-Icon, zentriert auf (cx, cy)."""
    w = 26 * scale
    if cat == "clear":
        _wx_sun(d, cx, cy, 15 * scale) if is_day else _wx_moon(d, cx, cy, 17 * scale)
    elif cat == "partly":
        if is_day:
            _wx_sun(d, cx - w * 0.55, cy - w * 0.5, 11 * scale)
        else:
            _wx_moon(d, cx - w * 0.5, cy - w * 0.5, 12 * scale)
        _wx_cloud(d, cx + w * 0.12, cy + w * 0.18, w * 0.92)
    elif cat in ("cloudy", "fog"):
        _wx_cloud(d, cx, cy, w)
        if cat == "fog":
            s = SS
            for yy in (cy + w * 0.78, cy + w * 1.08):
                d.line([((cx - w * 0.7) * s, yy * s), ((cx + w * 0.7) * s, yy * s)],
                       fill=EYE_DIM, width=max(1, int(2.4 * s)))
    elif cat == "rain":
        _wx_cloud(d, cx, cy - 5 * scale, w)
        _wx_rain(d, cx, cy + w * 0.62)
    elif cat == "storm":
        _wx_cloud(d, cx, cy - 5 * scale, w)
        _wx_bolt(d, cx, cy + w * 0.5)
    elif cat == "snow":
        _wx_cloud(d, cx, cy - 5 * scale, w)
        _wx_snow(d, cx, cy + w * 0.68)


def _tri_up(d, x, y, r, fill):
    s = SS
    d.polygon([(x * s, (y - r) * s), ((x - r) * s, (y + r * 0.8) * s),
               ((x + r) * s, (y + r * 0.8) * s)], fill=fill)


def _tri_dn(d, x, y, r, fill):
    s = SS
    d.polygon([(x * s, (y + r) * s), ((x - r) * s, (y - r * 0.8) * s),
               ((x + r) * s, (y - r * 0.8) * s)], fill=fill)


_COMPASS = ("N", "NO", "O", "SO", "S", "SW", "W", "NW")


def _wind_label(deg: float | None, spd: float | None) -> str:
    """Kompakter Wind-Text: 'SW 14' oder '18' (ohne Richtung wenn unbekannt)."""
    if spd is None or spd < 1:
        return ""
    spd_str = f"{round(spd)}"
    if deg is None:
        return spd_str
    idx = round(deg / 45) % 8
    return f"{_COMPASS[idx]} {spd_str}"


def _wind_arrow(d, cx: float, cy: float, deg_from: float, length: float = 9) -> None:
    """Kleiner gezeichneter Windpfeil (zeigt wohin Wind weht) um (cx,cy)."""
    s = SS
    deg_to = (deg_from + 180) % 360
    rad = math.radians(deg_to)
    dx, dy = math.sin(rad) * length, -math.cos(rad) * length
    x1, y1 = cx - dx * 0.45, cy - dy * 0.45
    x2, y2 = cx + dx * 0.55, cy + dy * 0.55
    d.line([(x1 * s, y1 * s), (x2 * s, y2 * s)], fill=EYE_DIM, width=max(1, int(2.2 * s)))
    # Pfeilkopf: kleines Dreieck
    perp = rad + math.pi / 2
    base_x = x2 - math.sin(rad) * 4
    base_y = y2 + math.cos(rad) * 4
    d.polygon([
        (x2 * s, y2 * s),
        ((base_x + math.sin(perp) * 3) * s, (base_y - math.cos(perp) * 3) * s),
        ((base_x - math.sin(perp) * 3) * s, (base_y + math.cos(perp) * 3) * s),
    ], fill=EYE_DIM)


def card_key() -> str:
    """Inhalts-Schluessel: aendert sich bei Temp/Gefuehl/Wind/Tag/Kategorie/Max/Min/Regen."""
    w = get_weather()
    cat = _category(w["code"])
    temp = f"{round(w['temp'])}" if w["temp"] is not None else "--"
    app = f"{round(w['apparent_temp'])}" if w.get("apparent_temp") is not None else "--"
    tmax = f"{round(w['tmax'])}" if w.get("tmax") is not None else "--"
    tmin = f"{round(w['tmin'])}" if w.get("tmin") is not None else "--"
    wind = f"{round(w['wind_speed'])}" if w.get("wind_speed") is not None else "--"
    n = _now()
    return (f"{temp}|{app}|{tmax}|{tmin}|{w.get('rain')}|{wind}"
            f"|{n.year}-{n.timetuple().tm_yday}|{cat}|{int(w['is_day'])}")


def render_card(out_path: str | Path) -> Path:
    """Wetter-Karte Hero-Layout: grosses zentriertes Icon, Temperatur darunter,
    Gefuehlstemperatur, Tageshoch/-tief, Regen und Wind in der Info-Leiste.
    Cyan-Robot-Stil mit sparsamen Akzentfarben."""
    w = dict(get_weather())
    cat = _category(w["code"])
    is_day = w["is_day"]
    s = SS
    img = Image.new("RGB", (SIZE * s, SIZE * s), BG)
    d = ImageDraw.Draw(img)

    n = _now()
    datestr = f"{WD[n.weekday()]} · {n.day}. {MON[n.month - 1]}"

    # ── Zone 1: Kopf (Datum + Trennlinie) ────────────────────────────────────
    d.text((120 * s, 26 * s), datestr, font=_font(22 * s), fill=EYE, anchor="mm")
    d.line([(18 * s, 48 * s), (222 * s, 48 * s)], fill=EYE_DIM, width=2 * s)

    # ── Zone 2: Hero (grosses Icon + Temperatur + Gefuehl) ───────────────────
    # Icon: gross, horizontal zentriert in der Mitte des Hero-Bereichs
    _wx_icon(d, 120, 91, cat, is_day, scale=1.72)

    temp_str = f"{round(w['temp'])}°" if w["temp"] is not None else "--°"
    d.text((120 * s, 146 * s), temp_str, font=_font(47 * s), fill=EYE, anchor="mm")

    # Gefuehlstemperatur: nur zeigen wenn Abweichung >= 2 Grad spuerbar
    app = w.get("apparent_temp")
    if app is not None and w["temp"] is not None and abs(round(app) - round(w["temp"])) >= 2:
        feels_str = f"fühlt wie {round(app)}°"
        d.text((120 * s, 163 * s), feels_str, font=_font(15 * s), fill=EYE_DIM, anchor="mm")

    # ── Trennlinie ────────────────────────────────────────────────────────────
    d.line([(18 * s, 173 * s), (222 * s, 173 * s)], fill=EYE_DIM, width=2 * s)

    # ── Zone 3: Info (2 Zeilen) ───────────────────────────────────────────────
    fi = _font(19 * s)

    # Zeile 1: ▲ Tageshoch  ▼ Tagestief   [Regenwahrscheinlichkeit rechts]
    y1 = 193
    tmax_str = f"{round(w['tmax'])}°" if w.get("tmax") is not None else "--"
    tmin_str = f"{round(w['tmin'])}°" if w.get("tmin") is not None else "--"
    _tri_up(d, 20, y1 - 3, 6, SUN)
    d.text((31 * s, y1 * s), tmax_str, font=fi, fill=EYE, anchor="lm")
    lx = 31 + d.textlength(tmax_str, font=fi) / s + 16
    _tri_dn(d, lx, y1 - 3, 6, RAIN)
    d.text(((lx + 11) * s, y1 * s), tmin_str, font=fi, fill=EYE_DIM, anchor="lm")
    if w.get("rain") is not None:
        rtxt = f"{w['rain']}%"
        d.text((226 * s, y1 * s), rtxt, font=fi, fill=EYE, anchor="rm")
        drx = 226 - d.textlength(rtxt, font=fi) / s - 12
        d.line([(drx * s, (y1 - 7) * s), ((drx - 3) * s, (y1 + 4) * s)],
               fill=RAIN, width=max(1, int(2.4 * s)))
        _disc(d, drx - 2.5, y1 + 4, 3.0, RAIN)

    # Zeile 2: Wind (Pfeil + Richtung + Geschwindigkeit), nur wenn > 1 km/h
    y2 = 218
    wind_spd = w.get("wind_speed")
    wind_deg = w.get("wind_dir")
    wlabel = _wind_label(wind_deg, wind_spd)
    if wlabel:
        if wind_deg is not None:
            _wind_arrow(d, 20, y2, wind_deg)
        wx = 32 if wind_deg is not None else 18
        d.text((wx * s, y2 * s), f"{wlabel} km/h", font=fi, fill=EYE_DIM, anchor="lm")

    frame = img.resize((SIZE, SIZE), Image.LANCZOS)
    pal = frame.quantize(colors=128, method=Image.MEDIANCUT)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pal.save(out, optimize=True)
    return out


if __name__ == "__main__":
    outdir = sys.argv[2] if len(sys.argv) > 2 else "out"
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        p = render(Path(outdir) / "weather_anim.gif")
        print(f"  {p}: {p.stat().st_size} bytes  (Wetter ok={get_weather()['ok']})")
    elif len(sys.argv) > 1 and sys.argv[1] == "card":
        p = render_card(Path(outdir) / "weather.gif")
        print(f"  {p}: {p.stat().st_size} bytes  key={card_key()}")
    else:
        print("Nutzung: python3 -m smalltv.weather build|card [ausgabeordner]")
