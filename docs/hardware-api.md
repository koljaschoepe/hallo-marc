# GeekMagic SmallTV-Ultra - Hardware & HTTP-API

Verdichtete Recherche (Stand Juni 2026), Abschnitt "verifiziert" vom November 2026. Quellen am Ende.

## Wichtige Korrektur: ESP8266, nicht ESP32

Der **SmallTV-Ultra** basiert auf einem **ESP8266** (ESP-12F-Klasse), nicht ESP32.
Das ist relevant fuer Firmware-Entscheidungen (z.B. kein LVGL moeglich).

| Modell | Chip | Hinweis |
|---|---|---|
| SmallTV (Basic) | ESP8266 | guenstig, kein Touch |
| **SmallTV-Ultra** | **ESP8266** | unser Geraet, Firmware V9.x |
| SmallTV-PRO | ESP32-WROOM-32 | Touch-Sensor oben |
| SmallTV S3 | ESP32-S3 | neuer, mehr Flash |

## Hardware

- **MCU:** ESP8266 (ESP-12F), ~80 KB RAM, meist 4 MB Flash. Kein LVGL.
- **Display:** 1,54" IPS, **240x240 px**, Treiber **ST7789V**, ~16-bit Farbe (RGB565).
- **Konnektivitaet:** **nur WLAN 2,4 GHz.** USB-C ist im Normalbetrieb **nur Strom** -
  kein USB-Seriell-Datenpfad zur Steuerung. (UART-Pads auf der Platine nur zum Flashen.)
- **Bedienung:** Tasten/Menue. **Kein Touch, kein Lautsprecher, kein Mikrofon, kein Lichtsensor**
  am Ultra (Touch ist Pro-Feature).

## HTTP-API der Werks-Firmware (V9.x)

Basis = `http://<geraete-ip>`. Web-Konsole: `http://<ip>/settings.html`.
Endpunkte aus der Referenz-Integration `adrienbrault/geekmagic-hacs` abgeleitet.

### Status / JSON
```bash
curl http://<ip>/app.json      # Geraetezustand: theme, brightness, aktuelles Bild
curl http://<ip>/brt.json      # Helligkeit -> {"brt":N}
curl http://<ip>/space.json    # Speicher/freier Platz
curl http://<ip>/album.json    # Album-Einstellungen (interval, gif_loop, autoplay)
curl "http://<ip>/filelist?dir=/image/"   # HTML-Liste der Bilder
```

### Bild hochladen (multipart POST)
```bash
curl -g -X POST -H "Content-Type: multipart/form-data" \
  -F "file=@status.jpg" "http://<ip>/doUpload?dir=/image/"
```

### Bild anzeigen
```bash
curl "http://<ip>/set?theme=3"                  # Ultra: theme 3 = eigenes Bild (Pro=4)
curl "http://<ip>/set?img=/image/status.jpg"
```

### Helligkeit / Album / Navigation / Reboot
```bash
curl "http://<ip>/set?brt=50"                       # API meist 0-100 (UI zeigt 0-255)
curl "http://<ip>/set?i_i=1&gif_loop=1&autoplay=1"  # Album/Slideshow
curl "http://<ip>/set?page=1"                       # naechste Seite
curl "http://<ip>/set?clear=image"                  # Bilder loeschen
curl "http://<ip>/delete?file=/image/status.jpg"
curl "http://<ip>/set?reboot=1"
```

### Firmware-HTTP-Macke (wichtig fuer Client-Code)
Die Firmware liefert teils **kaputte HTTP-Antworten** (doppelter `Content-Length`,
Daten nach `Connection: close`). `curl` toleriert das; strikte Libraries
(requests/httpx) koennen eine Exception werfen, **obwohl die Aktion klappte**.
-> Unser `smalltv/client.py` faengt das ab und wertet es als Erfolg.

## Bildformat

- **240x240 px**, **JPEG bevorzugt** (auf ESP8266 ~2,5 s vs. PNG ~5,8 s).
- Fuer RGB565 rendern (kraeftige Farben, hoher Kontrast, wenig feine Verlaeufe).
- Schrift >= ~10-12 px, sonst unleserlich.
- Dateien klein halten (wenige 10 KB). Kein dokumentiertes Hard-Limit -> `/space.json` pruefen.
- GIF (animiert) unterstuetzt; `gif_loop` steuert Schleifen.

## Am echten Geraet verifiziert (Ultra-V9.0.51, November 2026)
- `/set?theme=3` = eigenes Bild. `/app.json` liefert danach `{"theme":3}`.
- `/set?img=/image/<datei>` wirkt direkt (Antwort `OK`), kein Re-Upload noetig.
- `/set?autoplay=0` schaltet das Album ab, sonst wechselt das Geraet selbst durch `/image/`.
- `/brt.json` liefert z.B. `{"brt":"128"}` (String).
- `/v.json` liefert `{"m": "SmallTV-Ultra","v":"Ultra-V9.0.51"}`, gut fuers Finden im Netz.
- Speicher: 3,1 MB gesamt, rund 2,2 MB fuer eigene Bilder nutzbar.
- WLAN: `/wifisave?s=<ssid>&p=<passwort>` speichert und startet neu. `/config.json` zeigt die SSID.
- **Ohne erreichbares WLAN** laeuft ein eingestelltes eigenes Bild (theme 3) einfach weiter,
  es oeffnet sich *kein* Hotspot. Hotspot `GIFTV` (192.168.4.1) gibt es nur nach dem
  Stecker-Reset: beim Fortschrittsbalken zweimal Strom ziehen, beim dritten Mal stecken lassen.
- Der Stecker-Reset setzt das Theme auf 1 (Uhr) zurueck, Bilder bleiben erhalten.

## Firmware-Optionen (Bewertung)
- **Stock V9.x behalten (empfohlen):** simple, sprachunabhaengige Bild-Push-API.
  Passt perfekt zu "Frame auf dem Rechner rendern und hochladen". Kein Flash-Risiko.
- **ESPHome:** moeglich am Ultra, aber **kein LVGL** (ESP8266-RAM), HA-zentriert.
- **Tasmota / Community-Firmware:** mehr Aufwand, am ESP8266 eingeschraenkt.

## Quellen
- Referenz-Integration (API-Quelle): https://github.com/adrienbrault/geekmagic-hacs
- C-Uploader `ggpf`: https://codeberg.org/nereusx/geekmagic-smalltv
- Rust-Stats-Tool: https://lib.rs/crates/geekmagic-stats
- ESPHome-Geraeteseite (Hardware): https://devices.esphome.io/devices/geekmagic-ultra/
- Offizielles Repo/Manual: https://github.com/GeekMagicClock/smalltv-ultra
