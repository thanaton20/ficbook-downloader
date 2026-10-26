#!/bin/bash
# Build a drag-to-Applications disk image of the macOS app.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -x .venv/bin/python ]]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi

if ! "$PY" -c "import PyInstaller" >/dev/null 2>&1; then
  "$PY" -m pip install pyinstaller
fi

"$PY" -m PyInstaller --noconfirm --clean \
  --distpath dist \
  --workpath build/pyinstaller \
  packaging/ficbook.spec

APP="dist/Ficbook Downloader.app"
if [[ ! -d "$APP" ]]; then
  echo "App bundle was not created." >&2
  exit 1
fi

codesign --force --deep --sign - "$APP"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

hdiutil create \
  -volname "Ficbook Downloader" \
  -srcfolder "$STAGE" \
  -ov \
  -format UDZO \
  "dist/Ficbook-Downloader.dmg"

echo "Built dist/Ficbook-Downloader.dmg"
