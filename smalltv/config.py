"""Konfiguration aus Umgebungsvariablen bzw. der .env im Repo-Wurzelordner.

Alles, was ortsabhaengig ist (Geraete-IP, Wetterort, Haltestelle), steht in der
.env. Vorlage: .env.example.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from PIL import ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = Path(__file__).resolve().parent / "fonts"


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


_fonts: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """DejaVu Sans aus smalltv/fonts (laeuft auf macOS, Linux, Windows gleich)."""
    key = (size, bold)
    if key not in _fonts:
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        _fonts[key] = ImageFont.truetype(str(FONT_DIR / name), size)
    return _fonts[key]


@dataclass
class Config:
    ip: str
    image_theme: int
    show_seconds: int
    queue_file: Path

    @classmethod
    def from_env(cls) -> "Config":
        ip = env("SMALLTV_IP")
        if not ip or "X" in ip:
            raise SystemExit(
                "SMALLTV_IP ist nicht gesetzt. `cp .env.example .env` und IP eintragen "
                "(finden mit `make discover`)."
            )
        return cls(
            ip=ip,
            image_theme=int(env("SMALLTV_IMAGE_THEME", "3")),
            show_seconds=int(env("SMALLTV_SHOW_SECONDS", "20")),
            queue_file=Path(env("SMALLTV_QUEUE", "/tmp/smalltv_queue.jsonl")),
        )


# Ort fuer Wetter (Open-Meteo, kein Key). Default: Dresden-Striesen.
LAT = float(env("WEATHER_LAT", "51.0447"))
LON = float(env("WEATHER_LON", "13.7770"))
LOCATION_NAME = env("WEATHER_NAME", "Striesen")

# Haltestelle fuer die Abfahrtstafel (VVO, kein Key). Default: Zwinglistraße.
VVO_STOP_ID = env("VVO_STOP_ID", "33000084")
VVO_LINES = [x.strip() for x in env("VVO_LINES", "").split(",") if x.strip()]
WALK_MIN = float(env("VVO_WALK_MIN", "3"))
