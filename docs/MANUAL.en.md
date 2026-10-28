# PSU Control – User Manual

**English** · [Deutsch](HANDBUCH.de.md)

PSU Control remote-controls the UNI-T UDP3305S-E bench power supply over the local network. It runs as a Mac app and as an iPhone/iPad app. Both use the same interface, which recreates the instrument's front panel.

> The user interface is currently in German. This manual uses the German labels as they appear on screen, with a translation in brackets the first time.

## Contents
1. [Preparing the instrument](#1-preparing-the-instrument)
2. [Installation](#2-installation)
3. [Connecting](#3-connecting)
4. [The main screen](#4-the-main-screen)
5. [Entering values](#5-entering-values)
6. [Keys](#6-keys)
7. [WAVE – curves](#7-wave--curves)
8. [LIST – voltage and current sequences](#8-list--voltage-and-current-sequences)
9. [DELAYER – timed on/off](#9-delayer--timed-onoff)
10. [PRESET](#10-preset)
11. [STORAGE](#11-storage)
12. [UTILITY](#12-utility)
13. [SCPI console](#13-scpi-console)
14. [Simulator and test device](#14-simulator-and-test-device)
15. [Limits and good to know](#15-limits-and-good-to-know)
16. [Troubleshooting](#16-troubleshooting)
17. [Files and settings](#17-files-and-settings)

---

## 1. Preparing the instrument

1. Connect the UDP3305S-E to your router or switch with a network cable.
2. On the instrument, open **UTILITY → Interface / LAN** and either enable DHCP or enter a fixed IP address. A fixed address is recommended, so the app always finds the instrument at the same place.
3. Note the IP address shown on the instrument, e.g. `192.168.0.137`.

The app communicates via SCPI over **TCP port 5025**. Close the UNI-T PC software before using PSU Control, because it may occupy the connection.

## 2. Installation

### iPhone / iPad
Install **PSU Control** via the [TestFlight beta](https://testflight.apple.com/join/tYkUeqYG) (first install the free *TestFlight* app from the App Store), later from the App Store. iOS / iPadOS 16 or later is required.

On first start, iOS asks for permission to access the **local network**. Tap **Allow**. Without this permission the app cannot reach the instrument. You can change it later in *Settings → Privacy & Security → Local Network*.

### Mac
1. Download `PSU Control.zip` from the [releases page](../../../releases/latest) and unzip it.
2. Move **PSU Control.app** to your *Applications* folder.
3. Because the app is not notarised by Apple, macOS blocks the first launch:
   * macOS 15 and later: try to open it, then go to *System Settings → Privacy & Security* and click **Open Anyway**.
   * Older versions: right-click the app → **Open** → **Open**.
4. PSU Control needs **Python 3**. If it is missing, the app offers to install Apple's free *Command Line Tools*. Open the app again afterwards.
5. If macOS asks for access to the local network, allow it.

The Mac app opens the interface in your default web browser at `http://localhost:8080`. If that port is in use, it picks the next free one. Opening the app a second time only opens a new browser window. To quit, use **Connection → App beenden** (quit app).

## 3. Connecting

Click the connection button at the top right (green dot = connected, red = not connected) or the LAN symbol in the display. The dialog **Netzteil verbinden** (connect power supply) appears. It also opens by itself on first launch.

![Connect dialog](screenshots/mac-connect.png)

- **Netzwerk durchsuchen** (search network): searches your own network (/24) for devices with port 5025 open and shows each device's identification (`*IDN?`). UNI-T devices are listed first. Click an entry to connect.
- **Zuletzt verwendet** (recently used): the last eight devices. The app reconnects to the last one automatically on the next start. ✕ removes an entry.
- **IP-Adresse manuell** (manual IP): enter the address (and port, normally 5025) and click **Verbinden** (connect).
- **Simulator (ohne Gerät)**: a built-in virtual UDP3305S-E for trying the app out.

## 4. The main screen

![Main screen](screenshots/mac-main.png)

The display shows one column per channel, colour-coded as on the instrument: **CH1 turquoise, CH2 yellow, CH3 purple**. In series or parallel mode, the combined channel (SER/PARA) and CH3 are shown.

Each column contains:
- **Header:** channel, **On/Off**, **CV/CC**. While the output is on, the header is filled with the channel colour. CC (constant current, the current limit is active) is shown in red.
- **Readings:** measured voltage (V), current (A) and energy (Wh). Click Wh to switch to power (W) and back. Values of switched-off channels are dimmed.
- **Setzen** (set): voltage and current set points.
- **Grenze** (limit): OVP (over-voltage protection) and OCP (over-current protection) values. The box next to each value switches the protection on or off.

The selected channel has a coloured frame. Select it by clicking the column or using the **CH1/CH2/CH3** keys.

The soft keys below the display, **Spannung** (voltage), **Strom** (current), **OVP**, **OCP**, select the corresponding field of the selected channel. **Zoom** shows only the selected channel in large digits.

## 5. Entering values

1. Click or tap a value, or press a soft key. The field gets a white frame.
2. Type the number on the keyboard or the on-screen keypad. The entry is highlighted in blue, as on the instrument.
3. Confirm with **Enter** or **OK**. **ESC** cancels.

Further options:
- **Mouse wheel** over a value acts like the rotary knob: voltage ±0.1 V, current ±0.01 A. Hold **⌥ (Option)** for fine steps of 0.01 V / 0.001 A.
- **▲ / ▼** on the keypad, or the arrow keys, change the selected value in small steps.
- The app sends changes to the instrument immediately and then reads the value back. If the instrument rejects a value, a message appears at the bottom right.

## 6. Keys

| Key | Function |
|---|---|
| **WAVE** | Curve view (see 7). The key lights green while active. |
| **SER / PARA** | Series or parallel mode. Pressing again returns to independent mode. Switch outputs off first. |
| **LIST / DELAYER** | Sequences (see 8 and 9). |
| **STORAGE** | Save/recall settings in slots 1–10 (see 11). Press again to close. |
| **PRESET** | Preset groups P1–P5 (see 10). Press again to return to the main view. |
| **UTILITY** | System settings (see 12). Press again to return to the main view. |
| **LOCK** | Switches the instrument's key lock on and off. While it is locked, the padlock is closed and "LOCK" glows green, as on the instrument. Unlocking also releases a remote lock. The app shows locks set on the instrument itself after a few seconds. |
| **CH1 / CH2 / CH3** | Select a channel. |
| **ON/OFF** | Switch the channel output. Lights green while on. |
| **ALL ON/OFF** | All outputs on, or all off if any is on. |
| **CH3 1.8V … 5V** | Quick select for the CH3 voltage. The active value lights. |
| **Keypad, ESC, ←, ▲▼, OK** | Value entry. |

## 7. WAVE – curves

![WAVE](screenshots/mac-wave.png)

**WAVE** switches to the curve view, modelled on the instrument's *:WAVEDISP* screen.
- **Left:** the selected channel with its readings and settings. Switch with CH1/CH2/CH3.
- **Right:** three charts for voltage (0–30 V), current (0–5 A) and power (0–150 W) of all channels. In series/parallel mode the scales adapt (60 V / 10 A).
- **Click into the chart** to change the time axis: **30 s → 2 min → 10 min**.
- **Normal** (5th soft key) or WAVE again returns to the normal view.

The curves come from the app's own measurements, taken twice per second. They start when the app is opened. Events shorter than about half a second may not show.

## 8. LIST – voltage and current sequences

![LIST](screenshots/mac-list.png)

LIST makes the instrument play a sequence of up to **2048 steps** on its own. Each step defines a **voltage**, a **current limit** and a **duration**. Open it with **LIST / DELAYER**, select the **LIST** tab and the channel at the top.

### Creating a curve
On the left under **Kurve erzeugen** (create curve):

| Field | Meaning |
|---|---|
| **Vorlage** (template) | Sinus (sine), Puls (pulse), Rampe/Dreieck (ramp/triangle), Treppe aufwärts/abwärts/auf und ab (staircase up/down/up-down), Exponentiell steigend/fallend (exponential rise/fall) |
| **Verändern** (vary) | Whether the template shapes the **voltage** or the **current** |
| **Minimum / Maximum** | Range of the curve |
| **Strombegrenzung / Spannung** | The fixed other value: current limit when shaping voltage, voltage when shaping current |
| **Punkte** (points) | Number of steps (2–2048) |
| **Zeit pro Punkt** (time per point) | Duration of each step, at least 0.1 s |
| **Invertieren** (invert) | Sine, pulse and ramp upside down |
| **Tastverhältnis** (duty cycle) | Pulse: share of the period at maximum |
| **Symmetrie** (symmetry) | Ramp: 100 % = rising sawtooth, 0 % = falling, 50 % = triangle |
| **Exponent** | Exponential: steepness 0–10 (0 = linear) |

The info box shows the **period and frequency** and the total duration. **Kurve in Tabelle übernehmen** (copy curve to table) fills the table on the right. You can edit every value there, add rows with **+ Zeile** or remove them with **− letzte Zeile**.

### Sequence
Under **Ablauf** (sequence):
- **Startgruppe** (start group): where in the instrument's memory (0–2047) the table begins
- **Wiederholungen** (repetitions): 1–99,999
- **Am Ende** (at the end): switch the output off, or keep the last value
- **Ausgang beim Start einschalten** (switch output on at start): recommended

### Transfer and run
1. **Ans Gerät senden** (send to instrument) writes the table and sequence settings into the instrument. Long tables take a few seconds, and the progress is shown.
2. **▶ Start** runs the sequence. The status bar shows **Punkt** (current step), **Restzeit** (remaining time) and **Wiederholungen übrig** (remaining repetitions). The current row is highlighted in the table and the preview.
3. **■ Stop** ends it early.

**Vom Gerät lesen** (read from instrument) loads the sequence stored in the instrument into the table. While a sequence is running, the instrument does not accept changes.

### Example: brown-out test for a 5 V circuit
Template *Treppe auf und ab*, vary *voltage*, minimum 4.2 V, maximum 5.0 V, current limit 1 A, 9 points, 2 s per point, 3 repetitions. The circuit then sees 5.0 → 4.2 → 5.0 V in 0.2 V steps, three times in a row.

## 9. DELAYER – timed on/off

Here the voltage stays as set, and the sequence switches the **output** on and off. Up to **2048 steps**, each with a state (on/off) and a duration. Open it with the **DELAYER** tab.

**Ablauf erzeugen** (create sequence):
- **Ein/Aus im Wechsel** (on/off alternating), starting with on or off: fixed on-time and off-time
- **Zeiten steigend / fallend** (increasing / decreasing times): alternating on/off, durations start at *Startzeit* (start time) and change by *Schritt* (step) each time

**Ablauf** (sequence) settings: start group, repetitions, state at the end (output off / on / keep last state), and an optional **Abbruch wenn** (stop when) condition: voltage, current or power above or below a limit, e.g. *Strom > 3 A* (current > 3 A) stops the test when the circuit draws too much.

Transfer and run work as with LIST. Typical uses: power-cycling endurance tests, switch-on order of several channels (one delayer per channel), checking how a circuit starts up.

## 10. PRESET

![PRESET](screenshots/mac-preset.png)

The instrument has five preset groups **P1–P5**. Each holds voltage, current, OVP and OCP for every channel. Select a tab:
- **Lesen** (read): load the group from the instrument
- **Aktuelle übernehmen** (copy current): insert the current settings
- **Speichern** (save): write the group into the instrument
- **Anwenden** (apply): make the group the current setting

## 11. STORAGE

**STORAGE** saves the complete current setting in one of ten slots in the instrument (**Speichern**, save) or recalls it (**Laden**, load). LIST and DELAYER have their own ten slots inside the LIST/DELAYER window.

## 12. UTILITY

![UTILITY](screenshots/mac-utility.png)

- **System:** Signalton (beeper), Helligkeit (display brightness), Tastensperre (key lock), Fernsperre (remote lock). The remote lock can only be released by a command or by restarting the instrument. The **LOCK** key in the app shows the lock state and releases both locks.
- **LAN:** DHCP, IP address, subnet mask, gateway. Changes take effect only after **Übernehmen** (apply). If the IP changes, the app reconnects to the new address after a few seconds. With DHCP, the network search opens instead.
- **RS232:** baud rate.
- **Info & Wartung** (info & maintenance): instrument ID, SCPI version, **Fehlerspeicher** (error queue) with the number of entries and **Auslesen** (read out), **Selbsttest** (self-test), **Werkseinstellung** (factory reset, with a double confirmation).

## 13. SCPI console

At the bottom of the page, **SCPI-Konsole & Protokoll** opens a console. Type any command from the *UDP3000S Programming Manual*, e.g. `*IDN?` or `:MEASure:ALL? CH1`. Queries (with `?`) show the reply. For other commands, any error message from the instrument is shown. ↑/↓ browse the command history. The log also lists all changes the app sends.

## 14. Simulator and test device

- **Simulator:** *Connection → Simulator (ohne Gerät)*. A virtual UDP3305S-E with resistive loads on the outputs (CH1 10 Ω, CH2 4 Ω, CH3 2 Ω). It supports all functions including LIST and DELAYER.
- **Test device over the network:** `python3 tools/fake_device.py -v` (from the source code) starts a simulated instrument on port 5025 of your Mac. Connect to it from the iPhone or Mac like a real instrument. `-v` logs every command.

## 15. Limits and good to know

- The instrument accepts **0.1 s** as the shortest LIST step. A sine of 20 points therefore has a period of at least 2 s (0.5 Hz). LIST is meant for slow processes, not as a signal generator.
- Only positive voltages, 0–30 V (CH3 0–6 V). The supply can source current but not sink it, so voltages fall more slowly than programmed at light load.
- The app reads the measurements twice per second. The **Wh** counter is calculated by the app from the measured power and restarts when the output is switched on, so it may differ slightly from the instrument's display.
- Input limits in the app: CH1/CH2 32 V / 5.2 A, CH3 6.2 V / 3.2 A, SER 64 V, PARA 10.4 A. The instrument limits further itself.
- While the key lock is on, only the ON/OFF keys work on the instrument. The app keeps full control. **LOCK** in the app releases it.

## 16. Troubleshooting

| Problem | Solution |
|---|---|
| Network search finds nothing | Is LAN enabled on the instrument, with an IP in the same network? Are both on the same network (not a guest Wi-Fi)? iPhone: allow local network access in Settings. Mac: allow local network access. |
| *nicht erreichbar* (not reachable) | Check the IP on the instrument. Close the UNI-T PC software. Check port 5025. |
| Values are not accepted | Check the instrument's message (bottom right) and the error queue in UTILITY. Above OVP/OCP? Is a LIST/DELAYER sequence running? |
| Mac: app does not open | *System Settings → Privacy & Security → Open Anyway*. Is Python 3 missing? Open the app again and accept the installation. |
| Mac: browser shows "Mac-Server läuft nicht" (Mac server not running) | Start the app again. Log file: `~/Library/Logs/PSU Control.log` |
| Front panel locked | Press **LOCK** in the app, or hold LOCK on the instrument. |

## 17. Files and settings

| | Mac | iPhone / iPad |
|---|---|---|
| Settings (recent devices) | `~/Library/Application Support/PSU Control/config.json` | stored inside the app |
| Log | `~/Library/Logs/PSU Control.log` | – |

PSU Control sends no data to the internet and contains no tracking, see the [privacy policy](../PRIVACY.md).

---
*UNI-T and UDP3305S-E are trademarks of Uni-Trend Technology (China) Co., Ltd. PSU Control is an independent project.*
