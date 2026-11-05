"""Findet das SmallTV im lokalen Netz (macOS, Linux, Windows).

Fragt jede Adresse im /24-Netz parallel nach /v.json; das Geraet antwortet
mit Modell und Firmware-Version.

Aufruf:  python3 -m smalltv.discover            (Subnetz wird geraten)
         python3 -m smalltv.discover 192.168.178
"""

from __future__ import annotations

import socket
import sys
from concurrent.futures import ThreadPoolExecutor

import requests


def _guess_subnet() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))       # sendet nichts, ermittelt nur die lokale IP
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ".".join(ip.split(".")[:3])


def _probe(ip: str) -> str | None:
    try:
        r = requests.get(f"http://{ip}/v.json", timeout=1.5)
        if "smalltv" in r.text.lower() or "geekmagic" in r.text.lower():
            return r.text.strip()
    except requests.RequestException:
        pass
    return None


def discover(subnet: str | None = None) -> list[tuple[str, str]]:
    subnet = subnet or _guess_subnet()
    print(f"Suche in {subnet}.0/24 ...", file=sys.stderr)
    ips = [f"{subnet}.{i}" for i in range(1, 255)]
    with ThreadPoolExecutor(max_workers=64) as pool:
        results = list(pool.map(_probe, ips))
    return [(ip, info) for ip, info in zip(ips, results) if info]


if __name__ == "__main__":
    hits = discover(sys.argv[1] if len(sys.argv) > 1 else None)
    if hits:
        for ip, info in hits:
            print(f"  {ip}   {info}")
        print(f"\nIn die .env eintragen:  SMALLTV_IP={hits[0][0]}")
    else:
        print("Kein SmallTV gefunden. Ist es im selben WLAN (2,4 GHz)? Siehe README, Abschnitt WLAN.")
