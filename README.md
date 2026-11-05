# Hallo Marc!

Das kleine Display ist ein **GeekMagic SmallTV-Ultra**. Bei mir hat es Abfahrten, Wetter
und ein Gesicht gezeigt, ab jetzt gehört es dir. Hier liegt alles, um eigene Sachen
draufzubringen.

Viel Spaß beim Basteln!
Kolja

---

## Das Ding in Kürze

ESP8266, 240 x 240 px, **nur WLAN 2,4 GHz**. Das USB-C-Kabel liefert nur Strom.
Auf dem Gerät läuft kein eigener Code. Stattdessen **rendert ein Rechner ein Bild
(JPEG/GIF), lädt es per HTTP hoch und lässt es anzeigen.** Rund 2 MB Platz für Bilder.

Die Begrüßung ist ein GIF auf dem Gerät und läuft ohne WLAN und ohne Rechner.

## 1. Ins WLAN bringen

Das Gerät kennt noch kein WLAN und öffnet von selbst keinen Hotspot. So geht es:

1. **Stecker-Reset:** Kabel rein. Sobald der Fortschrittsbalken erscheint, sofort ziehen.
   **Zweimal** so, beim **dritten** Mal stecken lassen.
2. Das Display zeigt die Einrichtung. Handy ins WLAN **`GIFTV`** (Warnung „kein Internet“ ignorieren).
3. **`http://192.168.4.1`** öffnen → *Network* → 2,4-GHz-WLAN wählen, Passwort, **save**.
4. Das Gerät startet neu und zeigt kurz seine IP. Danach steht es auf der Werks-Uhr.

Die Begrüßung bleibt gespeichert, `make hallo` holt sie zurück.

## 2. Die Weboberfläche

Unter `http://<ip>` (vom selben WLAN aus):

| Menü | Wofür |
| --- | --- |
| *Network* | WLAN wechseln |
| *Weather* | Stadt für die eingebaute Wetteranzeige |
| *Time* | Zeitserver, 12/24 h |
| *Pictures* | Bilder und GIFs per Browser hochladen und auswählen (240 x 240) |
| *Settings* | Helligkeit, zeitgesteuertes Dimmen, weitere Geräteeinstellungen |

Kein Programmieren nötig, um Bilder draufzuladen. Fertige GIFs passend zuschneiden:
[ezgif.com](https://ezgif.com) auf 240 x 240.

## 3. Programmieren

```bash
git clone https://github.com/koljaschoepe/hallo-marc.git && cd hallo-marc
make setup       # venv + Pillow, requests, qrcode; legt .env an
make discover    # findet das Display, IP in .env eintragen
```

```bash
.venv/bin/python examples/01_hallo_welt.py "Moin"   # 15 Zeilen, das Grundprinzip
make face MOOD=happy      # neutral happy listening thinking speaking sad
make weather              # Wetterkarte
make transit              # Abfahrten Zwinglistraße
make notify TEXT="Kaffee?"
make run                  # Daemon: Tafel jede Minute, Wetter, Hinweise aus Queue
make hallo                # Begrüßung wiederherstellen
```

Ort, Haltestelle und Linien stehen in der `.env`. Andere Haltestelle:
`.venv/bin/python -m smalltv.transit find "Schillerplatz"`.

| Datei | Inhalt |
| --- | --- |
| `smalltv/client.py` | HTTP-Client, fängt die Firmware-Macken ab |
| `smalltv/greeting.py` | die Begrüßung, `MESSAGES` ändern für eigene Sprüche |
| `smalltv/face.py` | das Gesicht in sechs Stimmungen |
| `smalltv/weather.py`, `transit.py` | Wetter (Open-Meteo), Abfahrten (VVO), beide ohne API-Key |
| `smalltv/companion.py` | Dauerbetrieb, z.B. auf einem Raspberry Pi |
| `examples/` | Hallo Welt, Countdown, eigene Animation |
| `docs/hardware-api.md` | alle Endpunkte und was am Gerät getestet ist |

## 4. Die API in 30 Sekunden

```bash
curl -F "file=@bild.jpg" "http://$IP/doUpload?dir=/image/"   # hochladen
curl "http://$IP/set?theme=3"                                 # Modus eigenes Bild
curl "http://$IP/set?img=/image/bild.jpg"                     # anzeigen
curl "http://$IP/set?autoplay=0"                              # Album-Wechsel aus
curl "http://$IP/set?brt=60"                                  # Helligkeit
```

## 5. Gut zu wissen

- **JPEG für Standbilder, GIF für Animationen**, GIFs unter ~300 KB, wenige Farben.
- **Große Schrift, starker Kontrast.** Unter ~12 px wird es unleserlich.
- **Jeder `/set`-Aufruf dauert ~1 s.** Theme einmal setzen, danach nur `img=` wechseln.
- **Kaputte HTTP-Antworten** der Firmware heißen meist: hat trotzdem geklappt.
- **Flash schonen:** höchstens etwa minütlich hochladen.
- **Firmware-Update** nur von [GeekMagicClock/smalltv-ultra](https://github.com/GeekMagicClock/smalltv-ultra)
  und nur die Ultra-Variante. Dort liegt auch das Handbuch.

## 6. Ideen

CI-Status mit Gesicht `happy`/`sad` · nächster Kalendertermin · Pomodoro-Timer ·
Home-Assistant-Werte ([geekmagic-hacs](https://github.com/adrienbrault/geekmagic-hacs)) ·
Pixel-Art-Galerie im Album-Modus (`/set?autoplay=1&i_i=10`)

---

Code: MIT. Schrift: DejaVu Sans (frei weitergebbar).
