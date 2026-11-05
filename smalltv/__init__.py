"""SmallTV-Starter: Steuerung fuer das GeekMagic SmallTV-Ultra (ESP8266, 240x240, nur WLAN).

Die Werks-Firmware bleibt drauf, gesteuert wird ueber ihre HTTP-API:
Bild rendern (Pillow), hochladen, anzeigen. Siehe README und docs/hardware-api.md.
"""

__version__ = "1.0.0"

from .client import SmallTVClient

__all__ = ["SmallTVClient"]
