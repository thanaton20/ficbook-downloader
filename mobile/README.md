# Ficbook for iPhone and Android

The phone apps save ficbook.net stories as txt, EPUB, and FB2, like the desktop app.

## Install

Download the files from the [Releases page](https://github.com/thanaton20/ficbook-downloader/releases).

**iPhone / iPad** (iOS 16.4 or later): download `Ficbook.ipa` and install it with
[Sideloadly](https://sideloadly.io) or AltStore using your Apple ID. With a free Apple ID the app
must be reinstalled every 7 days. Saved books appear in **Files › On My iPhone › Ficbook**.

**Android** (10 or later): download `Ficbook.apk` on the phone, open it, and allow
installing from your browser when asked. Saved books appear in **Downloads › Ficbook**.

## How it works

Each app is a thin native shell around one shared web interface in `shared/web/`:

| File | Job |
| --- | --- |
| `parse.js` | Reads story, chapter, series, and author pages. A port of `src/ficbook_dl/parse.py`. |
| `books.js` | Writes txt, FB2, and EPUB. A port of `src/ficbook_dl/formats/`. |
| `app.js`, `index.html`, `app.css` | The screens and the download loop. |
| `strings.js` | Generated from `src/ficbook_dl/i18n.py` by `tools/export_strings.py`. |

The native shell (`ios/` in Swift, `android/` in Kotlin) opens each ficbook page in the system web
view, runs `parse.js` on it, and saves the finished files. If ficbook shows its security check or
age confirmation, the app shows that page so you can answer it, then carries on.

## Develop

After changing `src/ficbook_dl/i18n.py`, run `python3 mobile/tools/export_strings.py`.

Check that the JavaScript reads pages and writes books exactly like the desktop app:

```
cd mobile && npm install && cd ..
python3 mobile/tests/parity.py
```

### iOS

Needs Xcode and [XcodeGen](https://github.com/yonaskolb/XcodeGen) (`brew install xcodegen`).

```
cd mobile/ios && xcodegen generate && open Ficbook.xcodeproj   # run in the simulator
mobile/scripts/build_ios.sh                                     # unsigned .ipa in mobile/dist/
```

### Android

Needs JDK 17 and the Android SDK (platform 35, build tools 35).

```
cd mobile/android && ./gradlew assembleDebug                   # debug .apk
mobile/scripts/build_android.sh                                 # signed release .apk in mobile/dist/
```

Release builds are signed with a key kept outside the repository. Create it once:

```
mkdir -p ~/.config/ficbook-downloader
keytool -genkeypair -v -keystore ~/.config/ficbook-downloader/android-release.jks \
  -alias ficbook -keyalg RSA -keysize 4096 -validity 10000
```

and write `~/.config/ficbook-downloader/android-signing.properties`:

```
storeFile=/Users/<you>/.config/ficbook-downloader/android-release.jks
storePassword=<password>
keyAlias=ficbook
keyPassword=<password>
```

Keep a backup of both files. Android only installs an update over an existing app when it is
signed with the same key.
