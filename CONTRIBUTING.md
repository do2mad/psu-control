# Contributing · Mitmachen

## English

Thanks for your interest in PSU Control!

- **Bugs and ideas:** please open an [issue](../../issues). For bugs, include the platform (Mac/iPhone/iPad and version), the instrument model and firmware (*UTILITY → Info*), what you did and what happened. The SCPI console log helps a lot.
- **Pull requests:** welcome. Please keep them focused on one topic.
- **Code style:** no external libraries. The Mac server uses only the Python standard library, and the web UI is plain HTML/CSS/JavaScript. This keeps the apps small and easy to build.
- **One UI for all platforms:** `web/index.html` is shared by the Mac and iOS apps. New device functions need to be supported in both backends: `mac/udp3305.py` and `web/ios-bridge.js` (including their simulators).
- **Testing without hardware:** use the built-in simulator or `python3 tools/fake_device.py -v`.
- **Other instruments:** if you own another UDP3000S model and can test, reports are very welcome.

By contributing you agree that your contribution is licensed under the [MIT licence](LICENSE).

## Deutsch

Danke für dein Interesse an PSU Control!

- **Fehler und Ideen:** bitte als [Issue](../../issues) melden. Bei Fehlern bitte angeben: Plattform (Mac/iPhone/iPad und Version), Gerätemodell und Firmware (*UTILITY → Info*), was du gemacht hast und was passiert ist. Das Protokoll der SCPI-Konsole hilft sehr.
- **Pull-Requests:** gern, bitte jeweils auf ein Thema beschränkt.
- **Code-Stil:** keine externen Bibliotheken. Der Mac-Server nutzt nur die Python-Standardbibliothek, die Oberfläche ist reines HTML/CSS/JavaScript. So bleiben die Apps klein und leicht zu bauen.
- **Eine Oberfläche für alle Plattformen:** `web/index.html` nutzen Mac- und iOS-App gemeinsam. Neue Gerätefunktionen müssen in beiden Backends unterstützt werden: `mac/udp3305.py` und `web/ios-bridge.js` (jeweils einschließlich Simulator).
- **Testen ohne Gerät:** eingebauter Simulator oder `python3 tools/fake_device.py -v`.
- **Andere Geräte:** Wer ein anderes UDP3000S-Modell besitzt und testen kann, ist herzlich willkommen.

Mit einem Beitrag stimmst du zu, dass er unter der [MIT-Lizenz](LICENSE) steht.
