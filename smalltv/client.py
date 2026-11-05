"""HTTP-Client fuer die Werks-Firmware des GeekMagic SmallTV-Ultra.

Die Firmware liefert teils kaputte HTTP-Antworten (doppelter Content-Length,
Daten nach 'Connection: close'). Strikte Libraries wie requests/httpx koennen
darauf mit einer Exception reagieren, obwohl die Aktion auf dem Geraet
erfolgreich war. Deshalb behandeln wir bekannte Verbindungsabbrueche nach dem
Senden als Erfolg.

Endpunkte sind aus der aktiv gepflegten Referenz-Integration abgeleitet:
https://github.com/adrienbrault/geekmagic-hacs (custom_components/geekmagic)

Getestet mit SmallTV-Ultra, Firmware Ultra-V9.0.51 (theme 3 = eigenes Bild).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from requests.exceptions import ChunkedEncodingError, ConnectionError as ReqConnError, InvalidHeader

# Diese Fehler bedeuten bei der Werks-Firmware: Aktion hat geklappt, nur die Antwort ist kaputt.
_TOLERATED = (ChunkedEncodingError, ReqConnError, InvalidHeader)

log = logging.getLogger("smalltv.client")

# Theme-Nummer fuer das "eigenes Bild"-Theme. Ultra = 3 (verifiziert), Pro = 4.
IMAGE_THEME = 3


@dataclass
class DeviceStatus:
    """Vom Geraet ausgelesener Zustand (so weit verfuegbar)."""

    reachable: bool
    raw: dict[str, Any]
    brightness: int | None = None
    free_space: str | None = None


class SmallTVClient:
    """Duenner Wrapper um die HTTP-API des SmallTV-Ultra."""

    def __init__(self, ip: str, timeout: float = 8.0, image_theme: int = IMAGE_THEME):
        self.ip = ip
        self.base = f"http://{ip}"
        self.timeout = timeout
        self.image_theme = image_theme

    # ----- interne Helfer ---------------------------------------------------

    def _get(self, path: str, **params: Any) -> requests.Response | None:
        """GET-Request, tolerant gegenueber den Firmware-HTTP-Macken."""
        url = f"{self.base}{path}"
        try:
            return requests.get(url, params=params or None, timeout=self.timeout)
        except _TOLERATED as exc:
            # Aktion wurde wahrscheinlich ausgefuehrt, nur die Antwort war kaputt.
            log.debug("Tolerierter Antwort-Fehler bei GET %s: %s", url, exc)
            return None

    def _get_json(self, path: str) -> dict[str, Any]:
        resp = self._get(path)
        if resp is None:
            return {}
        try:
            return resp.json()
        except ValueError:
            return {}

    # ----- Status / Diagnose -----------------------------------------------

    def ping(self) -> bool:
        """True, wenn das Geraet auf HTTP antwortet."""
        try:
            requests.get(self.base, timeout=4)
            return True
        except _TOLERATED:
            # Antwort kaputt, aber Geraet hat geantwortet -> erreichbar.
            return True
        except requests.RequestException:
            return False

    def status(self) -> DeviceStatus:
        app = self._get_json("/app.json")
        brt = self._get_json("/brt.json")
        space = self._get_json("/space.json")
        reachable = bool(app or brt or space) or self.ping()
        return DeviceStatus(
            reachable=reachable,
            raw={"app": app, "brt": brt, "space": space},
            brightness=brt.get("brt") if isinstance(brt, dict) else None,
            free_space=str(space) if space else None,
        )

    def list_images(self, directory: str = "/image/") -> str:
        resp = self._get("/filelist", dir=directory)
        return resp.text if resp is not None else ""

    # ----- Steuerung --------------------------------------------------------

    def set_theme(self, theme: int) -> None:
        """Theme/Modus wechseln (z.B. zurueck zur Uhr/Gesicht-Ansicht)."""
        self._get("/set", theme=theme)

    def set_brightness(self, value: int) -> None:
        """Helligkeit setzen. Bereich auf Geraet verifizieren (0-100 vs 0-255)."""
        self._get("/set", brt=max(0, value))

    def show_image(self, remote_name: str) -> None:
        """Zeigt ein bereits hochgeladenes Bild an (Pfad relativ zu /image/)."""
        name = remote_name if remote_name.startswith("/") else f"/image/{remote_name}"
        self.set_theme(self.image_theme)
        self._get("/set", img=name)

    def set_album(self, interval: int = 1, gif_loop: int = 1, autoplay: int = 1) -> None:
        """Album-/Slideshow-Verhalten (fuer Auto-Refresh eines Bildes)."""
        self._get("/set", i_i=interval, gif_loop=gif_loop, autoplay=autoplay)

    def next_page(self) -> None:
        self._get("/set", page=1)

    def prev_page(self) -> None:
        self._get("/set", page=-1)

    def reboot(self) -> None:
        self._get("/set", reboot=1)

    def delete_image(self, remote_name: str) -> None:
        name = remote_name if remote_name.startswith("/") else f"/image/{remote_name}"
        self._get("/delete", file=name)

    # ----- Upload -----------------------------------------------------------

    def upload_image(self, local_path: str | Path, directory: str = "/image/",
                     remote_name: str | None = None) -> bool:
        """Laedt eine lokale Bilddatei (JPEG bevorzugt) auf das Geraet.

        Gibt True zurueck, wenn der Upload (vermutlich) erfolgreich war - inkl.
        des Falls, dass die Firmware eine kaputte, aber vollstaendig gesendete
        Antwort liefert.
        """
        path = Path(local_path)
        url = f"{self.base}/doUpload"
        try:
            with path.open("rb") as fh:
                resp = requests.post(
                    url,
                    params={"dir": directory},
                    files={"file": (remote_name or path.name, fh, _content_type(path))},
                    timeout=max(self.timeout, 20),
                )
            return resp.status_code < 400
        except _TOLERATED as exc:
            log.debug("Tolerierter Antwort-Fehler beim Upload: %s", exc)
            return True
        except requests.RequestException as exc:
            log.warning("Upload fehlgeschlagen: %s", exc)
            return False

    def push_image(self, local_path: str | Path, remote_name: str | None = None) -> bool:
        """Hochladen + sofort anzeigen. Praktischster Einzelaufruf."""
        path = Path(local_path)
        name = remote_name or path.name
        if not self.upload_image(path, remote_name=name):
            return False
        self.show_image(name)
        return True


def _content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        return "image/jpeg"
    if suffix == ".gif":
        return "image/gif"
    if suffix == ".png":
        return "image/png"
    return "application/octet-stream"
