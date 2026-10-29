# PSU Control

[English](README.md) · **Deutsch**

Fernsteuerung für das programmierbare Labornetzteil **UNI-T UDP3305S-E** über das lokale Netzwerk.
Die Oberfläche bildet die Gerätefront nach, mit Display, Softkeys und Tasten, auf Mac, iPhone und iPad.

![PSU Control auf dem Mac](docs/screenshots/mac-main.png)

<p align="center">
  <img src="docs/screenshots/iphone-main.png" width="230" alt="iPhone">
  &nbsp;
  <img src="docs/screenshots/iphone-wave.png" width="230" alt="iPhone – WAVE">
</p>
<p align="center"><img src="docs/screenshots/ipad-main.png" width="600" alt="iPad"></p>

## Download

| Plattform | |
|---|---|
| **iPhone / iPad** | **[TestFlight-Beta](https://testflight.apple.com/join/tYkUeqYG)** · App Store: *folgt* <!-- APPSTORE_URL --> |
| **Mac** | [Neueste Version](../../releases/latest) → `PSU-Control-mac.zip` |
| **Quellcode** | dieses Repository (MIT-Lizenz) |

## Funktionen

- Messwerte aller Kanäle (V, A, Wh oder W), CV/CC-Anzeige, Ausgänge einzeln oder alle gemeinsam ein/aus
- Spannung und Strom einstellen, OVP/OCP-Grenzen mit Ein/Aus
- Betriebsarten unabhängig, **seriell** und **parallel**, CH3-Schnellwahl 1.8 / 2.5 / 3.3 / 5 V
- **WAVE** – Verlauf von Spannung, Strom und Leistung aller Kanäle (30 s / 2 min / 10 min)
- **LIST** – Spannungs-/Stromverläufe mit bis zu 2048 Schritten: Sinus, Puls, Rampe, Treppe, Exponential oder eigene Tabelle, mit Vorschau, Übertragung, Start/Stop und Fortschritt
- **DELAYER** – zeitgesteuertes Ein-/Ausschalten mit optionaler Abbruchbedingung (V, A oder W über/unter einem Grenzwert)
- **PRESET** P1–P5 und **STORAGE** 1–10
- **UTILITY** – Signalton, Helligkeit, Tasten- und Fernsperre, LAN (DHCP/IP/Maske/Gateway), RS232, Fehlerspeicher, Selbsttest, Werkseinstellung
- Netzwerksuche nach Geräten, manuelle IP, zuletzt verwendete Geräte
- Eingebauter **Simulator** – alles ohne Gerät ausprobieren
- SCPI-Konsole für beliebige Befehle aus der Programmieranleitung

| | |
|---|---|
| ![WAVE](docs/screenshots/mac-wave.png) | ![LIST](docs/screenshots/mac-list.png) |
| ![PRESET](docs/screenshots/mac-preset.png) | ![UTILITY](docs/screenshots/mac-utility.png) |

## Dokumentation

- 📗 [Benutzerhandbuch (Deutsch)](docs/HANDBUCH.de.md)
- 📘 [User manual (English)](docs/MANUAL.en.md)
- 🔒 [Datenschutz](PRIVACY.md)
- 📝 [Änderungen](CHANGELOG.md)

## Voraussetzungen

- UNI-T **UDP3305S-E** mit aktiviertem **LAN**. Andere UDP3000S-Modelle nutzen dieselben SCPI-Befehle und funktionieren sehr wahrscheinlich auch.
- **iPhone / iPad:** iOS / iPadOS 16 oder neuer
- **Mac:** macOS 10.15 oder neuer und Python 3. Fehlt Python, bietet die App die Installation der kostenlosen Apple Command Line Tools an.
- Netzteil und Mac/iPhone müssen im selben Netzwerk sein. Die App spricht SCPI über TCP-Port **5025**.

## Aufbau

```
                      ┌────────────────────────────┐
   web/index.html  ───┤ gleiche Oberfläche überall │
                      └──────────────┬─────────────┘
                     fetch('/api/…') │
             ┌───────────────────────┴───────────────────────┐
     Mac:  mac/udp3305.py (lokaler Webserver)       iOS: web/ios-bridge.js
           nur Python-Standardbibliothek                 + Swift (WKWebView, Sockets)
             └───────────────────────┬───────────────────────┘
                                     │ SCPI über TCP :5025
                              UNI-T UDP3305S-E
```

Mac-App und iOS-App bieten dieselben `/api/…`-Endpunkte. Deshalb läuft `web/index.html` unverändert auf beiden.

## Projektstruktur

```
web/index.html            Gemeinsame Oberfläche (HTML/CSS/JS, keine Bibliotheken)
web/ios-bridge.js         Geräte-Logik für iOS (beantwortet /api/… direkt in der App)
mac/udp3305.py            Mac-Server: liefert die Oberfläche aus, spricht SCPI
mac/AppTemplate/          Info.plist, Startskript und Symbol der Mac-App
mac/build-mac-app.sh      Baut dist/PSU Control.app und die ZIP-Datei
ios/PSUControl.xcodeproj  Xcode-Projekt der iOS-/iPadOS-App
ios/PSUControl/           Swift: WebView, native Brücke, TCP-Socket, Netzwerksuche
ios/project.yml           Alternative Projektbeschreibung für XcodeGen
tools/fake_device.py      Simuliertes Netzteil im Netzwerk (zum Testen)
tools/publish-github.sh   Hilfsskript zum Anlegen des GitHub-Repositorys
docs/                     Handbücher, Screenshots, App-Store-Texte
```

## Bauen

### Mac-App
```bash
./mac/build-mac-app.sh        # -> dist/PSU Control.app und dist/PSU Control.zip
```
Ohne App direkt starten: `python3 mac/udp3305.py [--host IP] [--lan] [--sim]`.

Die App ist nicht von Apple beglaubigt. Beim ersten Start unter macOS 15 und neuer: *Systemeinstellungen → Datenschutz & Sicherheit → Trotzdem öffnen*. Bei älteren Versionen: Rechtsklick auf die App → *Öffnen*.

### iOS-/iPadOS-App
1. `ios/PSUControl.xcodeproj` in Xcode 15 oder neuer öffnen.
2. Target **PSUControl** → *Signing & Capabilities* → eigenes **Team** wählen. Falls nötig, die Bundle-ID `de.1mhz.psucontrol` durch eine eigene ersetzen.
3. iPhone/iPad auswählen und **Run** drücken. Den Zugriff auf das **lokale Netzwerk** erlauben.

Für App Store / TestFlight: *Product → Archive → Distribute App*. Fertige Store-Texte liegen in [`docs/appstore/`](docs/appstore/).

### Testen ohne Netzteil
- In der App: *Verbindung → Simulator (ohne Gerät)*.
- Über das Netzwerk: `python3 tools/fake_device.py -v` auf dem Mac starten, dann in der App das Netzwerk durchsuchen oder die IP des Macs eintragen. Das simulierte Gerät verhält sich über TCP wie das echte, auch bei LIST und DELAYER.

## Grenzen des Geräts

- Die kürzeste Zeit pro LIST-Schritt beträgt **0,1 s**. Ein Sinus mit 20 Punkten läuft also mit höchstens 0,5 Hz. Gedacht ist LIST für langsame Abläufe wie Akku-Kurven, Spannungseinbrüche, Softstart oder Ein/Aus-Dauertests. Einen Signalgenerator ersetzt es nicht.
- Nur positive Spannungen (0–30 V je Kanal). Das Netzteil kann Strom liefern, aber nicht aufnehmen. Fallende Flanken sind bei kleiner Last deshalb langsamer als programmiert.
- Für die WAVE-Ansicht des Geräts gibt es keinen SCPI-Befehl. Die App zeichnet die Kurven aus eigenen Messungen (2 pro Sekunde).
- Den Energiezähler (Wh) berechnet die App selbst aus der gemessenen Leistung, weil das Gerät ihn nicht über SCPI liefert.

## Mitmachen

Fehlermeldungen und Pull-Requests sind willkommen, siehe [CONTRIBUTING.md](CONTRIBUTING.md).

## Hinweise

*UNI-T* und *UDP3305S-E* sind Marken der Uni-Trend Technology (China) Co., Ltd. Dieses Projekt ist unabhängig und nicht mit UNI-T verbunden. Die Namen dienen nur dazu, das unterstützte Gerät zu nennen.
Die SCPI-Befehle folgen der *UDP3000S Series Programming Manual* von UNI-T. Das Handbuch ist nicht Teil dieses Repositorys.
Benutzung auf eigene Gefahr: Ein Netzteil kann angeschlossene Schaltungen beschädigen. OVP und OCP sinnvoll setzen.

## Lizenz

[MIT](LICENSE) © 2026 Martin Oswald
