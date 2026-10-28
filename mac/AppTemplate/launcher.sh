#!/bin/bash
# Startprogramm fuer PSU Control: sucht Python 3, startet den lokalen
# Server im Hintergrund und oeffnet die Oberflaeche im Standard-Browser.
RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
LOG="$HOME/Library/Logs/PSU Control.log"
mkdir -p "$HOME/Library/Logs"

PY=""
for c in /opt/homebrew/bin/python3 /usr/local/bin/python3 \
         /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
  [ -x "$c" ] && { PY="$c"; break; }
done
if [ -z "$PY" ] && xcode-select -p >/dev/null 2>&1 && [ -x /usr/bin/python3 ]; then
  PY=/usr/bin/python3
fi

if [ -z "$PY" ] || ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,7) else 1)' >/dev/null 2>&1; then
  BTN=$(osascript -e 'button returned of (display dialog "PSU Control benötigt Python 3.\n\nDas lässt sich kostenlos über die Apple-Entwicklerwerkzeuge (Command Line Tools) installieren. Danach die App einfach erneut öffnen." buttons {"Abbrechen", "Installieren"} default button "Installieren" with icon caution with title "PSU Control")' 2>/dev/null)
  [ "$BTN" = "Installieren" ] && xcode-select --install
  exit 0
fi

echo "---- $(date) Start mit $PY" >> "$LOG"
nohup "$PY" "$RES/udp3305.py" >> "$LOG" 2>&1 &
disown
exit 0
