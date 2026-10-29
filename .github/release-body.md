## PSU Control – Mac

Fernsteuerung für das Labornetzteil **UNI-T UDP3305S-E** über das lokale Netzwerk (SCPI über TCP 5025).
Remote control for the **UNI-T UDP3305S-E** bench power supply over the local network (SCPI over TCP 5025).

### Installation (Deutsch)
1. **`PSU-Control-mac.zip`** unten unter *Assets* laden und entpacken.
2. **PSU Control.app** in den Ordner *Programme* ziehen.
3. Die App ist nicht von Apple beglaubigt. Beim ersten Start:
   - **macOS 15 und neuer:** App öffnen, Meldung schließen, dann *Systemeinstellungen → Datenschutz & Sicherheit → Trotzdem öffnen*.
   - **Ältere Versionen:** Rechtsklick auf die App → **Öffnen** → **Öffnen**.
4. Die Oberfläche öffnet sich im Browser. Netzteil über *Netzwerk durchsuchen* wählen oder IP-Adresse eingeben. Ohne Gerät: *Simulator (ohne Gerät)*.

Voraussetzungen: macOS 10.15 oder neuer, Python 3. Fehlt Python, bietet die App die Installation der kostenlosen Apple Command Line Tools an.

### Installation (English)
1. Download **`PSU-Control-mac.zip`** from *Assets* below and unzip it.
2. Move **PSU Control.app** to *Applications*.
3. The app is not notarised by Apple. On first launch:
   - **macOS 15 and later:** open the app, close the message, then *System Settings → Privacy & Security → Open Anyway*.
   - **Older versions:** right-click the app → **Open** → **Open**.
4. The interface opens in your browser. Pick the supply via *Netzwerk durchsuchen* (search network) or enter its IP address. Without an instrument: *Simulator (ohne Gerät)*.

Requirements: macOS 10.15 or later, Python 3. If Python is missing, the app offers to install Apple's free Command Line Tools.

### iPhone / iPad
TestFlight: https://testflight.apple.com/join/tYkUeqYG

📗 [Handbuch](https://github.com/do2mad/psu-control/blob/main/docs/HANDBUCH.de.md) · 📘 [Manual](https://github.com/do2mad/psu-control/blob/main/docs/MANUAL.en.md) · 📝 [Changelog](https://github.com/do2mad/psu-control/blob/main/CHANGELOG.md)
