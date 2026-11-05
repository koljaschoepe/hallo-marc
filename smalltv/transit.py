"""Abfahrtstafel: naechste Abfahrten einer Haltestelle (VVO-Echtzeit, kein API-Key).

Holt die Abfahrten von der freien VVO-WebAPI, wirft alles raus, was vor dem
Fussweg-Vorlauf abfaehrt, sortiert nach echter Abfahrtszeit (inkl. Verspaetung)
und rendert eine 240x240-Tafel: Uhr oben, darunter "Linie  Ziel  Minuten".

Konfiguration (.env):
  VVO_STOP_ID   Haltestellen-ID (Default 33000084 = Zwinglistraße)
  VVO_LINES     optional, nur diese Linien, z.B. "1,2,61"
  VVO_WALK_MIN  Minuten Fussweg; fruehere Abfahrten werden ausgeblendet

Haltestellen-ID finden:  python3 -m smalltv.transit find "Schillerplatz"

Fuer eigene Richtungsfilter siehe STOP_FILTER unten (allow/deny je Linie).
Andere Verkehrsverbuende: _fetch_stop() austauschen, z.B. gegen
https://v6.db.transport.rest (bundesweit, ebenfalls ohne Key).

CLI:  python3 -m smalltv.transit build | show | find <name>
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

# ---- Stil (wie face.py / weather.py) ------------------------------------
SIZE = 240
SS = 3
BG = (0, 0, 0)
EYE = (90, 222, 236)         # Cyan (Hauptfarbe)
EYE_DIM = (44, 120, 130)     # gedimmtes Cyan (Ziel/Sekundaer)
ACCENT = (236, 196, 90)      # warmer Akzent fuer Verspaetung (+N)

from .config import VVO_STOP_ID, VVO_LINES, WALK_MIN, font as _cfg_font

# ---- Haltestelle + optionaler Richtungsfilter ---------------------------
# Pro Linie: {"allow": [...]} (Ziel muss eines enthalten) ODER
#            {"deny":  [...]} (Ziel darf keines enthalten). Substring, case-insensitiv.
# Beispiel: {"61": {"allow": ["Löbtau"]}, "2": {"deny": ["Gorbitz"]}}
STOP_FILTER: dict[str, dict] = {}

STOPS = [{"id": VVO_STOP_ID, "lines": STOP_FILTER}]

MAX_ROWS = 6
DM_URL = "https://webapi.vvo-online.de/dm"
PF_URL = "https://webapi.vvo-online.de/tr/pointfinder"
HTTP_UA = "smalltv-starter/1.0 (privates Desk-Display)"

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Europe/Berlin")
except Exception:  # pragma: no cover
    _TZ = None

def _font(size: int):
    return _cfg_font(size)


def _now():
    import datetime as dt
    return dt.datetime.now(_TZ) if _TZ else dt.datetime.now()


# ---- VVO-Abfahrtsmonitor ------------------------------------------------

def _ms(dotnet: str | None) -> int | None:
    """Parst .NET-JSON-Datum '/Date(1782503460000-0000)/' -> Millisekunden."""
    if not dotnet:
        return None
    m = re.search(r"/Date\((\d+)", dotnet)
    return int(m.group(1)) if m else None


def find_stop(name: str) -> list[tuple[str, str]]:
    """Sucht Haltestellen per Name -> [(id, name)]."""
    body = json.dumps({"query": name, "limit": 8, "stopsOnly": True}).encode()
    req = urllib.request.Request(PF_URL, data=body, method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": HTTP_UA})
    with urllib.request.urlopen(req, timeout=8) as r:
        pts = json.loads(r.read()).get("Points", []) or []
    out = []
    for p in pts:
        f = p.split("|")
        out.append((f[0], f"{f[3]} ({f[2] or 'Dresden'})"))
    return out


def _fetch_stop(stopid: str) -> list[dict]:
    body = json.dumps({"stopid": stopid, "limit": 30}).encode()
    req = urllib.request.Request(
        DM_URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": HTTP_UA},
    )
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read()).get("Departures", []) or []


def _dir_ok(direction: str, cfg: dict) -> bool:
    d = (direction or "").lower()
    if "allow" in cfg:
        return any(a.lower() in d for a in cfg["allow"])
    if "deny" in cfg:
        return not any(x.lower() in d for x in cfg["deny"])
    return True


_NOISE = {"Bahnhof", "Nationalparkbahnhof", "S-Bf.", "S-Bf", "Bf.", "Btf.",
          "S-Bahnhof", "(Sachs)", "(Sachsen)"}

# Bekannte lange Ziele -> kurze, eindeutige Form (spart Platz, vor allem mit +N).
_ABBR = {
    "Südvorstadt": "Südvorst.",
    "Bad Schandau": "Bad Schandau",
    "Meißen Triebischtal": "Meißen",
    "Coswig": "Coswig",
}


def _short_dest(s: str, maxlen: int = 11) -> str:
    toks = [t for t in (s or "").split() if t not in _NOISE]
    out = " ".join(toks) if toks else (s or "")
    if out in _ABBR:
        out = _ABBR[out]
    if len(out) > maxlen:
        out = out[: maxlen - 1].rstrip() + "…"
    return out


def get_departures() -> list[dict]:
    """Gefilterte, zeitsortierte Abfahrten ueber alle Haltestellen."""
    now = time.time()
    rows: list[dict] = []
    for stop in STOPS:
        try:
            deps = _fetch_stop(stop["id"])
        except Exception:
            continue
        for x in deps:
            line = x.get("LineName", "")
            if VVO_LINES and line not in VVO_LINES:
                continue
            cfg = stop["lines"].get(line, {})
            direction = x.get("Direction", "")
            if not _dir_ok(direction, cfg):
                continue
            sched = _ms(x.get("ScheduledTime"))
            real = _ms(x.get("RealTime")) or sched
            if real is None:
                continue
            mins = round((real / 1000 - now) / 60)
            if mins < WALK_MIN:          # nicht mehr erreichbar -> raus
                continue
            delay = round((real - sched) / 60000) if sched else 0
            rows.append({
                "line": line,
                "dest": _short_dest(direction),
                "mins": mins,
                "delay": max(0, delay),
                "mot": x.get("Mot", ""),
                "sort": real,
            })
    rows.sort(key=lambda r: r["sort"])
    return rows[:MAX_ROWS]


# ---- Rendern ------------------------------------------------------------

def _fit(font: ImageFont.FreeTypeFont, text: str, max_w: float) -> str:
    """Kuerzt Text pixelgenau auf max_w (mit … falls noetig)."""
    if font.getlength(text) <= max_w:
        return text
    while text and font.getlength(text + "…") > max_w:
        text = text[:-1]
    return (text + "…") if text else ""


def _render(rows: list[dict], timestr: str) -> Image.Image:
    s = SS
    img = Image.new("RGB", (SIZE * s, SIZE * s), BG)
    d = ImageDraw.Draw(img)

    # Kopf: Uhr mittig + feine Trennlinie
    d.text((120 * s, 28 * s), timestr, font=_font(40 * s), fill=EYE, anchor="mm")
    d.line([(16 * s, 52 * s), (224 * s, 52 * s)], fill=EYE_DIM, width=2 * s)

    if not rows:
        d.text((120 * s, 140 * s), "keine Abfahrten", font=_font(22 * s),
               fill=EYE_DIM, anchor="mm")
        return img.resize((SIZE, SIZE), Image.LANCZOS)

    # Feste Spalten (in echten px): Linie rechtsb. | Ziel linksb. | +Verspaetung rechtsb. | Min rechtsb.
    # +Verspaetung steht bewusst mit Abstand links der Minuten (nicht angequetscht).
    LINE_R, DEST_L, DEST_MAX, DLY_R, MIN_R = 46, 54, 158, 190, 236
    y0, dy = 72, 28
    f_line = _font(22 * s)
    f_dest = _font(17 * s)
    f_min = _font(21 * s)
    f_dly = _font(13 * s)
    for i, r in enumerate(rows):
        y = (y0 + i * dy) * s
        d.text((LINE_R * s, y), r["line"], font=f_line, fill=EYE, anchor="rm")
        dest = _fit(f_dest, r["dest"], (DEST_MAX - DEST_L) * s)
        d.text((DEST_L * s, y), dest, font=f_dest, fill=EYE_DIM, anchor="lm")
        if r["mins"] <= 0:
            d.text((MIN_R * s, y), "jetzt", font=f_min, fill=EYE, anchor="rm")
        else:
            d.text((MIN_R * s, y), f"{r['mins']}'", font=f_min, fill=EYE, anchor="rm")
            if r["delay"] >= 1:
                d.text((DLY_R * s, y), f"+{r['delay']}", font=f_dly, fill=ACCENT, anchor="rm")

    return img.resize((SIZE, SIZE), Image.LANCZOS)


def render(out_path: str | Path) -> Path:
    rows = get_departures()
    img = _render(rows, _now().strftime("%H:%M"))
    pal = img.quantize(colors=32, method=Image.MEDIANCUT)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    # einzelbild-GIF (palette -> knackiger Text, kleine Datei)
    pal.save(out, save_all=True, append_images=[], duration=1000, loop=0, optimize=True)
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "find":
        for sid, nm in find_stop(" ".join(sys.argv[2:]) or "Zwinglistraße"):
            print(f"  {sid}  {nm}")
    elif cmd in ("build", "show"):
        deps = get_departures()
        for r in deps:
            print(f"  {r['line']:>3} -> {r['dest']:<14} {r['mins']:>3}'  (+{r['delay']})")
        p = render(Path("out") / "transit.gif")
        print(f"  -> {p}: {p.stat().st_size} bytes, {len(deps)} Abfahrten")
        if cmd == "show":
            from .client import SmallTVClient
            from .config import Config
            cfg = Config.from_env()
            SmallTVClient(cfg.ip, image_theme=cfg.image_theme).push_image(p)
    else:
        print("Nutzung: python3 -m smalltv.transit build|show|find <name>")
