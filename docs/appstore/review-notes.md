# App Review notes (paste into App Store Connect → App Review Information → Notes)

PSU Control is a remote control for the UNI-T UDP3305S-E bench power supply. It communicates with the instrument in the user's local network via SCPI over TCP port 5025. No account or login is required.

HOW TO TEST WITHOUT THE INSTRUMENT
The app contains a built-in simulator of the power supply:
1. Launch the app. The dialog "Netzteil verbinden" (Connect power supply) opens automatically. If it does not, tap the button at the top right.
2. Tap "Simulator (ohne Gerät)" (Simulator, without device).
3. All functions now work with the simulated instrument:
   - Tap a value (e.g. "5.00 V" under "Setzen" (set)), type a number on the keypad and tap OK.
   - Tap "ON/OFF" below CH1/CH2/CH3 to switch outputs. The readings change.
   - WAVE shows curves. LIST/DELAYER opens the sequence editor: tap "Kurve in Tabelle übernehmen" (create curve), then "Ans Gerät senden" (send), then "▶ Start".
   - PRESET, UTILITY, STORAGE open the respective menus.

LOCAL NETWORK PERMISSION
The app asks for local network access (NSLocalNetworkUsageDescription). It is required to connect to the power supply and to search the local subnet for instruments when "Netzwerk durchsuchen" (search network) is tapped. No data is sent to the internet.

LANGUAGE
The user interface is in German. The English store description states this.

The source code is public under the MIT licence: https://github.com/do2mad/psu-control
