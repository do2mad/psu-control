# TestFlight – was wohin gehört

App Store Connect → **Apps → PSU Control → TestFlight**

## 1. Testinformationen (links: *Testinformationen*)
Einmal pro App ausfüllen. Gilt für alle Builds.

| Feld | Inhalt |
|---|---|
| **Beta-App-Beschreibung** (Deutsch) | siehe unten „Beschreibung DE“ |
| **Beta-App-Beschreibung** (Englisch, über Sprache oben rechts) | siehe unten „Beschreibung EN“ |
| **Feedback-E-Mail** | deine E-Mail-Adresse |
| **Marketing-URL** (optional) | `https://github.com/do2mad/psu-control` |
| **Datenschutz-URL** | `https://github.com/do2mad/psu-control/blob/main/PRIVACY.md` |
| **Beta-App-Review – Kontakt** | Vorname, Nachname, Telefon, E-Mail |
| **Anmeldung erforderlich** | **nein** (kein Häkcreview-notes.md`](review-notes.mdüfung** | Inhalt von [`rreview-notes.md`](review-notes.md |

> Die Datenschutz-URL funktioniert erst, wenn das Projekt auf GitHub liegt. Deshalb zuerst `./tools/publish-github.sh <name>` ausführen, dann die Links hier mit deinem Namen eintragen.

### Beschreibung DE
```
PSU Control steuert das Labornetzteil UNI-T UDP3305S-E über das lokale Netzwerk – mit einer Oberfläche wie die Gerätefront.

Ohne Netzteil ausprobieren: Beim Start „Simulator (ohne Gerät)“ wählen.
Mit Netzteil: LANDELAYERät aktivieren, in der App „Netzwerk durchsuchen“ oder die IP-Adresse eintragen und den Zugriff auf das lokale Netzwerk erlauben.

Funktionen: Messwerte, Spannung/Strom, OVP/OCP, Ausgänge, SER/PARA, WAVE-Kurven, LIST/DELAYER, PRESET, STORAGE, UTILITY, Tastensperre, SCPI-Konsole.
```

### Beschreibung EN
```
PSU Control remote-controls the UNI-T UDP3305S-E bench power supply over the local network – with an interface modelled on the instrument's front panel (interface in German).

Try it without an instrument: choose "Simulator (ohne Gerät)" at start.
With an instrument: enable LAN on the supply, tap "Netzwerk durchsuchen" (search network) or enter its IP address, and allow local network access.

Features: readings, voltage/current, OVP/OCP, outputs, series/parallel, WAVE curves, LIST/DELAYER, PRESET, STORAGE, UTILITY, key lock, SCPI console.
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
