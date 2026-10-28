# TestFlight – was wohin gehört

App Store Connect → **Apps → PSU Control → TestFlight**

## 1. Testinformationen (links: *Testinformationen*)
Einmal pro App ausfüllen. Gilt für alle Builds.

> Tipp: Texte abschnittsweise kopieren. Falls beim Einfügen Wörter vertauscht werden, ist meist die Textersetzung von macOS schuld (Systemeinstellungen → Tastatur → Textersetzungen).

| Feld | Inhalt |
|---|---|
| **Beta-App-Beschreibung** (Deutsch) | siehe unten „Beschreibung DE“ |
| **Beta-App-Beschreibung** (Englisch, über Sprache oben rechts) | siehe unten „Beschreibung EN“ |
| **Feedback-E-Mail** | deine E-Mail-Adresse |
| **Marketing-URL** (optional) | `https://github.com/do2mad/psu-control` |
| **Datenschutz-URL** | `https://github.com/do2mad/psu-control/blob/main/PRIVACY.md` |
| **Beta-App-Review – Kontakt** | Vorname, Nachname, Telefon, E-Mail |
| **Anmeldung erforderlich** | **nein** (kein Häkchen) |
| **Anmerkungen für die Prüfung** | Inhalt von [`review-notes.md`](review-notes.md) |

> Die Datenschutz-URL funktioniert erst, wenn das Projekt auf GitHub liegt. Deshalb zuerst `./tools/publish-github.sh <name>` ausführen, dann die Links hier mit deinem Namen eintragen.

### Beschreibung DE
```
PSU Control steuert das Labornetzteil UNI-T UDP3305S-E über das lokale Netzwerk. Die Oberfläche sieht aus wie die Front des Geräts.

Ohne Netzteil ausprobieren:
Beim ersten Start im Fenster "Netzteil verbinden" auf "Simulator (ohne Gerät)" tippen.

Mit Netzteil:
1. Am Netzteil unter UTILITY die LAN-Schnittstelle einschalten.
2. In der App "Netzwerk durchsuchen" antippen oder die IP-Adresse des Netzteils eingeben.
3. Den Zugriff auf das lokale Netzwerk erlauben, wenn iOS danach fragt.

Funktionen: Messwerte, Spannung und Strom einstellen, OVP/OCP, Ausgänge schalten, Seriell/Parallel, WAVE-Kurven, LIST und DELAYER, PRESET, STORAGE, UTILITY, Tastensperre, SCPI-Konsole.
```

### Beschreibung EN
```
PSU Control remote-controls the UNI-T UDP3305S-E bench power supply over the local network. The interface looks like the instrument's front panel (interface in German).

Try it without an instrument:
On first launch, tap "Simulator (ohne Gerät)" in the "Netzteil verbinden" (connect) window.

With an instrument:
1. On the power supply, enable the LAN interface under UTILITY.
2. In the app, tap "Netzwerk durchsuchen" (search network) or enter the supply's IP address.
3. Allow local network access when iOS asks.

Features: readings, set voltage and current, OVP/OCP, switch outputs, series/parallel, WAVE curves, LIST and DELAYER, PRESET, STORAGE, UTILITY, key lock, SCPI console.
```

## 2. Pro Build: „Was soll getestet werden?“
TestFlight → Build 1.3 (3) anklicken → *Testdetails*.

### DE
```
Erste Testversion 1.3.
Bitte testen: Verbinden (Netzwerksuche oder IP), Spannung/Strom setzen, Ausgänge schalten, WAVE, LIST mit Sinus-Vorlage, DELAYER, PRESET, UTILITY, LOCK.
Fehler bitte über „Feedback senden“ in TestFlight oder als Issue auf GitHub melden – mit Gerätemodell und Firmware (UTILITY → Info).
```

### EN
```
First beta 1.3.
Please test: connecting (network search or IP), setting voltage/current, switching outputs, WAVE, LIST with the sine template, DELAYER, PRESET, UTILITY, LOCK.
Please report bugs via "Send Beta Feedback" in TestFlight or as a GitHub issue – include the instrument model and firmware (UTILITY → Info).
```

## 3. Externe Testergruppe und öffentlicher Link
1. Links unter **Externe Tests** auf **+** → Gruppe anlegen, z. B. „Öffentliche Beta“.
2. In der Gruppe unter **Builds** auf **+** → Build **1.3 (3)** hinzufügen → *Zur Prüfung einreichen*. Der erste Build einer App wird von Apple kurz geprüft (meist unter 24 h).
3. In der Gruppe **Öffentlichen Link aktivieren**, optional ein Tester-Limit setzen.
4. Den Link (`https://testflight.apple.com/join/…`) in `README.md` und `README.de.md` bei `TESTFLIGHT_URL` eintragen.

Bis die Prüfung durch ist, zeigt der Link „This beta isn't accepting any new testers right now“. Das ist normal.

**Achtung:** Jede App hat eigene Gruppen und eigene Links. Immer in der App **PSU Control** nachsehen, nicht in einer anderen App wie Blue64.

## 4. Export-Compliance
Wird nicht abgefragt: `ITSAppUsesNonExemptEncryption = NO` steht bereits in der Info.plist.
