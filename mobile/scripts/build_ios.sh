#!/bin/bash
# Build an unsigned .ipa for sideloading (Sideloadly, AltStore) into mobile/dist/.
set -euo pipefail
cd "$(dirname "$0")/.."

export DEVELOPER_DIR="${DEVELOPER_DIR:-/Applications/Xcode.app/Contents/Developer}"
python3 tools/export_strings.py
(cd ios && xcodegen generate --quiet)

VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' ../src/ficbook_dl/__init__.py)
BUILD="ios/build/release"
xcodebuild -project ios/Ficbook.xcodeproj -scheme Ficbook -configuration Release \
  -sdk iphoneos -derivedDataPath "$BUILD" \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY="" \
  MARKETING_VERSION="$VERSION" build -quiet

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/Payload" dist
cp -R "$BUILD/Build/Products/Release-iphoneos/Ficbook.app" "$STAGE/Payload/"
(cd "$STAGE" && zip -qry "Ficbook-Downloader.ipa" Payload)
mv "$STAGE/Ficbook-Downloader.ipa" "dist/Ficbook-Downloader.ipa"
echo "Built mobile/dist/Ficbook-Downloader.ipa ($VERSION)"
