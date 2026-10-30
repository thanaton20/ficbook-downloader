#!/bin/bash
# Build a signed release .apk into mobile/dist/.
# Signing settings live outside the repo; see app/build.gradle.kts.
set -euo pipefail
cd "$(dirname "$0")/.."

export ANDROID_HOME="${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}"
SIGNING="${FICBOOK_SIGNING:-$HOME/.config/ficbook-downloader/android-signing.properties}"
if [[ ! -f "$SIGNING" ]]; then
  echo "No signing settings at $SIGNING. Create a keystore first (see mobile/README.md)." >&2
  exit 1
fi

python3 tools/export_strings.py
VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' ../src/ficbook_dl/__init__.py)
(cd android && ./gradlew --quiet assembleRelease)
mkdir -p dist
cp android/app/build/outputs/apk/release/app-release.apk "dist/Ficbook-Downloader.apk"
echo "Built mobile/dist/Ficbook-Downloader.apk ($VERSION)"
