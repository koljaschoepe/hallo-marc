"""CLI: einen Hinweis/eine Aufgabe sofort aufs Display pushen.

Beispiele:
  python -m smalltv.notify "Schau mal in dein Postfach"
  python -m smalltv.notify --title "Erinnerung" "Wasser trinken" --emoji ":)"
  python -m smalltv.notify --enqueue "Rechnung verarbeitet"   # in Queue legen

Ohne --enqueue wird direkt gepusht (Bild rendern, hochladen, anzeigen).
Mit --enqueue wird der Hinweis nur in die Queue geschrieben; der laufende
Companion-Daemon zeigt ihn dann an.
"""

from __future__ import annotations

import argparse
import json
import sys

from .client import SmallTVClient
from .config import Config
from .render import render_task


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Hinweis aufs SmallTV-Display pushen")
    p.add_argument("text", help="anzuzeigender Text")
    p.add_argument("--title", default="Aufgabe")
    p.add_argument("--emoji", default=":)")
    p.add_argument("--enqueue", action="store_true",
                   help="nur in die Queue schreiben statt direkt pushen")
    args = p.parse_args(argv)

    cfg = Config.from_env()

    if args.enqueue:
        with cfg.queue_file.open("a") as fh:
            fh.write(json.dumps({
                "text": args.text, "title": args.title, "emoji": args.emoji,
            }) + "\n")
        print(f"In Queue gelegt: {cfg.queue_file}")
        return 0

    frame = render_task(args.text, title=args.title, emoji=args.emoji)
    client = SmallTVClient(cfg.ip, image_theme=cfg.image_theme)
    ok = client.push_image(frame, remote_name="notify.jpg")
    print("Gepusht." if ok else "Push fehlgeschlagen.", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
