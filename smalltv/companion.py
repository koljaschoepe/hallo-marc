"""Companion-Daemon: macht aus dem Display einen kleinen Schreibtisch-Mitbewohner.

Ablauf in einer Schleife:
  - jede Minute die Abfahrtstafel (Uhrzeit ist im Bild eingebacken),
  - alle WEATHER_EVERY Minuten kurz die Wetterkarte,
  - Hinweise aus der Queue sofort einblenden, danach weiter wie gehabt.

Die Queue ist eine JSONL-Datei. Fuettern z.B. per
  python3 -m smalltv.notify --enqueue "Build ist gruen"
oder aus jedem anderen Programm:
  open("/tmp/smalltv_queue.jsonl", "a").write('{"text": "Kaffee?", "title": "Pause"}\\n')

Laeuft auf allem, was dauerhaft an ist (Raspberry Pi, Homeserver, NAS).
Start:  python3 -m smalltv.companion
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from . import transit, weather
from .client import SmallTVClient
from .config import Config
from .render import render_task

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("companion")

OUT = Path("out")
WEATHER_EVERY = 10      # Minuten
WEATHER_SECONDS = 12    # so lange bleibt die Wetterkarte stehen


def _read_queue(q: Path) -> list[dict]:
    if not q.exists():
        return []
    items = []
    for line in q.read_text().splitlines():
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    q.write_text("")
    return items


def main() -> int:
    cfg = Config.from_env()
    tv = SmallTVClient(cfg.ip, image_theme=cfg.image_theme)
    tv._get("/set", autoplay=0)          # Album aus, wir bestimmen das Bild
    log.info("Companion laeuft (Geraet %s, Queue %s)", cfg.ip, cfg.queue_file)

    last_minute = -1
    while True:
        for item in _read_queue(cfg.queue_file):
            frame = render_task(item.get("text", ""), title=item.get("title", "Hinweis"),
                                emoji=item.get("emoji", ":)"))
            tv.push_image(frame, remote_name="notify.jpg")
            log.info("Hinweis: %s", item.get("text", "")[:60])
            time.sleep(cfg.show_seconds)
            last_minute = -1             # danach sofort wieder die Tafel

        minute = time.localtime().tm_min
        if minute != last_minute:
            last_minute = minute
            try:
                if minute % WEATHER_EVERY == 0:
                    tv.push_image(weather.render_card(OUT / "weather.gif"))
                    time.sleep(WEATHER_SECONDS)
                tv.push_image(transit.render(OUT / "transit.gif"))
            except Exception as exc:      # Netz weg o.ae.: einfach weiterversuchen
                log.warning("Fehler: %s", exc)
        time.sleep(2)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass
