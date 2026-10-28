#!/bin/bash
# Baut "PSU Control.app" und eine ZIP-Datei zum Weitergeben nach dist/.
#   ./mac/build-mac-app.sh            (Version aus der Datei VERSION)
# Funktioniert auf macOS und Linux; auf dem Mac wird zusaetzlich ad-hoc signiert.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(cat "$ROOT/VERSION" 2>/dev/null || echo 1.0)"
NAME="PSU Control"
DIST="$ROOT/dist"
APP="$DIST/$NAME.app"

rm -rf "$APP" "$DIST/$NAME.zip"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
sed "s/__VERSION__/$VERSION/g" "$ROOT/mac/AppTemplate/Info.plist" > "$APP/Contents/Info.plist"
cp "$ROOT/mac/AppTemplate/launcher.sh" "$APP/Contents/MacOS/$NAME"
chmod 755 "$APP/Contents/MacOS/$NAME"
cp "$ROOT/mac/AppTemplate/AppIcon.icns" "$APP/Contents/Resources/"
cp "$ROOT/mac/udp3305.py" "$ROOT/web/index.html" "$APP/Contents/Resources/"

cd "$DIST"
if [ "$(uname)" = "Darwin" ]; then
  codesign --force --deep -s - "$APP" 2>/dev/null || true   # ad-hoc Signatur
  ditto -c -k --keepParent "$NAME.app" "$NAME.zip"
else
  zip -qr -X "$NAME.zip" "$NAME.app"
fi
echo "Fertig: $APP"
echo "        $DIST/$NAME.zip"
