# App Store / TestFlight – Unterlagen

Fertige Texte und Angaben für **App Store Connect**. Die Zeichenbegrenzungen von Apple sind eingehalten.

| Datei | Inhalt |
|---|---|
| [`metadata.de.md`](metadata.de.md) | Store-Texte Deutsch |
| [`metadata.en.md`](metadata.en.md) | Store-Texte Englisch |
| [`review-notes.md`](review-notes.md) | Hinweise für die App-Prüfung (Englisch, zum Einfügen) |
| `screenshots/` | Screenshots in den von Apple verlangten Größen (iPhone 6,9″: 1320 × 2868, iPad 13″: 2064 × 2752) |

## Allgemeine Angaben

| Feld | Wert |
|---|---|
| Name | PSU Control |
| Bundle-ID | `de.1mhz.psucontrol` |
| SKU | `psucontrol-ios` |
| Primäre Sprache | Deutsch |
| Kategorie | Dienstprogramme (Utilities), sekundär: Entwickler-Tools |
| Altersfreigabe | 4+ (keine der abgefragten Inhalte) |
| Preis | kostenlos |
| Copyright | 2026 Martin Oswald |
| Datenschutz-URL | `https://github.com/do2mad/psu-control/blob/main/PRIVACY.md` |
| Support-URL | `https://github.com/do2mad/psu-control/issues` |
| Marketing-URL (optional) | `https://github.com/do2mad/psu-control` |
| App-Datenschutz („Nutrition Label“) | **Keine Daten erfasst** (Data Not Collected) |
| Exportkonformität | keine Verschlüsselung (`ITSAppUsesNonExemptEncryption = NO` ist bereits gesetzt) |
| Inhaltsrechte | keine Inhalte Dritter |
| Werbe-ID (IDFA) | nein |

## Ablauf in Kurzform
1. In Xcode die Versionsnummer prüfen (Target → General → Version / Build).
2. *Product → Archive* → *Distribute App* → *App Store Connect* → *Upload*.
3. In App Store Connect eine neue App mit Bundle-ID `de.1mhz.psucontrol` anlegen und die Texte aus den Dateien hier einfügen.
4. **TestFlight:** Nach der automatischen Verarbeitung (meist 10–30 min) unter *TestFlight → Externe Tester* eine Gruppe anlegen und *Öffentlichen Link aktivieren*. Der Link ist in `README.md` und `README.de.md` eingetragen. Für externe Tester prüft Apple den ersten Build kurz (Beta App Review).
5. **App Store:** Screenshots hochladen, Prüfhinweise einfügen, *Zur Prüfung einreichen*. Den App-Store-Link (`https://apps.apple.com/app/id…`) trägst du danach bei `APPSTORE_URL` ein.

## Hinweise zur Prüfung
- **Gerät:** Die Prüfer haben kein Netzteil. Der eingebaute **Simulator** ist deshalb wichtig und in den Prüfhinweisen beschrieben.
- **Sprache:** Die Oberfläche ist Deutsch. In der englischen Beschreibung steht das ausdrücklich („Interface in German“), damit die Angaben stimmen. Eine englische Oberfläche wäre für eine internationale Veröffentlichung sinnvoll.
- **Marke:** „UNI-T“ bewusst nicht im App-Namen und nicht in den Schlüsselwörtern verwenden (Apple-Richtlinie 5.2.1), nur in der Beschreibung als unterstütztes Gerät nennen.
