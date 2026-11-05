# Hallo Marc!

Das kleine Display auf deinem Schreibtisch ist ein **GeekMagic SmallTV-Ultra**. Bis
eben hat es bei mir Abfahrten, Wetter und ein Gesicht gezeigt, ab jetzt gehört es dir.
In diesem Repo liegt alles, was du brauchst, um eigene Sachen darauf zu bringen.

Viel Spaß beim Basteln!
Kolja

---

## Was das Ding ist (und was nicht)

| | |
| --- | --- |
| Chip | ESP8266, 4 MB Flash, ~80 KB RAM |
| Display | 1,54" IPS, **240 x 240 px**, RGB565 |
| Verbindung | **nur WLAN, 2,4 GHz**. USB-C liefert nur Strom, keine Daten |
| Firmware | Werks-Firmware `Ultra-V9.0.51`, bleibt drauf |
| Speicher für Bilder | rund 2 MB |

Auf dem Gerät läuft kein eigener Code. Das Prinzip ist simpel: **ein Rechner rendert ein
Bild (JPEG oder GIF), lädt es per HTTP hoch und sagt dem Gerät, dass es das zeigen soll.**
Das Rendern übernimmt Pillow. Der Rechner kann dein Laptop sein, für Dauerbetrieb
ein Raspberry Pi, ein NAS oder ein Homeserver.

Die Begrüßung, die gerade läuft, ist einfach ein GIF (`hallo_marc.gif`), das auf dem Gerät
liegt. Sie läuft auch ohne WLAN und ohne Rechner weiter.

## 1. Ins WLAN bringen

Das Gerät kennt dein WLAN noch nicht und macht deshalb einen eigenen Hotspot auf.

1. Mit dem Handy oder Laptop ins WLAN **`GIFTV`** gehen.
2. Im Browser `http://192.168.4.1` öffnen, falls sich nichts von selbst öffnet.
3. Unter *Network* dein 2,4-GHz-WLAN wählen, Passwort eingeben, **save**.
4. Das Gerät startet neu und zeigt beim Hochfahren kurz seine neue IP-Adresse.

Danach ist die Weboberfläche unter `http://<ip>` erreichbar. Tipp: im Router eine
feste IP für das Gerät vergeben.

## 2. Loslegen

```bash
git clone https://github.com/koljaschoepe/hallo-marc.git
cd hallo-marc
make setup        # venv + Pillow, requests, qrcode; legt .env an
make discover     # sucht das Display im WLAN
# IP in .env eintragen (SMALLTV_IP=...)
make probe        # antwortet es?
```

Dann einfach ausprobieren:

```bash
.venv/bin/python examples/01_hallo_welt.py "Moin Kolja"
make face MOOD=happy        # neutral happy listening thinking speaking sad
make weather                # Wetterkarte
make transit                # Abfahrtstafel Zwinglistraße
make notify TEXT="Kaffee?"  # Hinweis-Karte
make hallo                  # die Begrüßung wiederherstellen
```

## 3. Was drin ist

```
smalltv/
  client.py     HTTP-Client für die Werks-Firmware (fängt ihre HTTP-Macken ab)
  config.py     .env laden, Schrift (DejaVu liegt bei, läuft überall gleich)
  greeting.py   die Begrüßung: Gesicht + Sprechblasen + QR-Karte als ein GIF
  face.py       das Gesicht in sechs Stimmungen, als loopende GIFs
  weather.py    Wetterkarte (Open-Meteo, kein API-Key)
  transit.py    Abfahrtstafel (VVO-Echtzeit, kein API-Key)
  render.py     Text- und Status-Karten
  notify.py     CLI: Hinweis anzeigen oder in die Queue legen
  companion.py  Daemon: jede Minute Tafel, ab und zu Wetter, Hinweise aus der Queue
  discover.py   Gerät im Netz finden
examples/
  01_hallo_welt.py   das kleinste mögliche Programm (15 Zeilen)
  02_countdown.py    Tage bis zu einem Datum
  03_animation.py    eigenes animiertes GIF (hüpfender Ball)
docs/
  hardware-api.md    alle HTTP-Endpunkte, Bildformate, Firmware-Optionen
```

Ort, Haltestelle und Linien stehen in der `.env`. Voreingestellt sind Striesen und die
Haltestelle Zwinglistraße. Andere Haltestelle finden:

```bash
.venv/bin/python -m smalltv.transit find "Schillerplatz"
```

## 4. Die API in 30 Sekunden

```bash
IP=192.168.178.50
curl -F "file=@bild.jpg" "http://$IP/doUpload?dir=/image/"   # hochladen
curl "http://$IP/set?theme=3"                                 # Modus "eigenes Bild"
curl "http://$IP/set?img=/image/bild.jpg"                     # anzeigen
curl "http://$IP/set?autoplay=0"                              # Album-Wechsel aus
curl "http://$IP/set?brt=60"                                  # Helligkeit
curl "http://$IP/delete?file=/image/bild.jpg"                 # löschen
curl  http://$IP/space.json                                   # freier Speicher
```

Mehr in [docs/hardware-api.md](docs/hardware-api.md).

## 5. Was ich auf dem Weg gelernt habe

- **JPEG für Standbilder, GIF für Animationen.** JPEG lädt am ESP8266 etwa doppelt so schnell wie PNG.
- **Groß und kontrastreich.** Unter ~12 px Schrift wird es unleserlich. Schwarzer Grund plus eine Akzentfarbe sieht auf dem IPS am besten aus.
- **GIFs klein halten.** Wenige Farben (`quantize(colors=16..48)`), unter ~300 KB. Gleiche Frames fasst Pillow beim Speichern selbst zusammen.
- **Jeder `/set`-Aufruf kostet ~1 s.** Theme und Autoplay einmal setzen, danach nur noch `img=` wechseln.
- **Die Firmware antwortet manchmal kaputtes HTTP**, obwohl die Aktion geklappt hat. `curl` ist das egal, `requests` wirft. `client.py` fängt das ab.
- **Flash schonen.** Nicht sekündlich hochladen. Jede Minute ist unkritisch.
- **Uhrzeit ins Bild backen.** Das Gerät kann keine Live-Daten in eigene Bilder schreiben. Wer eine Uhr will, rendert minütlich neu (siehe `transit.py`) oder schaltet in der Weboberfläche auf eine der eingebauten Uhr-Ansichten.

## 6. Ideen

- Build-Status deiner CI (grün/rot, Gesicht `happy`/`sad`)
- Kalender: nächster Termin und Minuten bis dahin
- Pomodoro-Timer mit dem Gesicht als Pausenerinnerung
- Home-Assistant-Werte (es gibt dafür eine fertige Integration: `adrienbrault/geekmagic-hacs`)
- Ein lokales LLM, das morgens einen Satz zum Tag sagt
- Pixel-Art-Galerie im Album-Modus (`/set?autoplay=1&i_i=10`)

## Lizenz

Code: MIT. Schrift: DejaVu Sans (Bitstream-Vera-Lizenz, frei weitergebbar), liegt in `smalltv/fonts/`.
