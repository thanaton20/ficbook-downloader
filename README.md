# ficbook-downloader

English | [Русский](README.ru.md) | [Українська](README.uk.md)

A desktop, phone, and command-line app that saves [ficbook.net](https://ficbook.net/) stories as UTF-8 text, EPUB, and FB2. It runs on macOS, Windows, iPhone, and Android, and from source on Linux.

You give it story links. It reads each public story page, follows the chapter list, and writes one file per format. Each chapter is its own section. Author, translator, series name and number, fandom, tags, and description are stored in the file. A cover is included when the story has one. It waits between requests. It does not open a browser.

Ficbook answers ordinary HTTP libraries with a security check. The desktop app and the command line use [curl_cffi](https://github.com/lexiforest/curl_cffi) so those requests look like a normal browser connection and the public story HTML comes back. The phone apps open each page in the phone's own browser view instead.

## Which file do I need?

| Device | Download | Needs |
| --- | --- | --- |
| Mac | [Ficbook-Downloader.dmg](https://github.com/thanaton20/ficbook-downloader/releases/latest/download/Ficbook-Downloader.dmg) | A Mac with Apple silicon (M1 or newer) |
| Windows | [Ficbook-Downloader.exe](https://github.com/thanaton20/ficbook-downloader/releases/latest/download/Ficbook-Downloader.exe) | Windows |
| iPhone, iPad | [Ficbook-Downloader.ipa](https://github.com/thanaton20/ficbook-downloader/releases/latest/download/Ficbook-Downloader.ipa) | iOS 16.4 or later, and a Mac or PC with Sideloadly |
| Android | [Ficbook-Downloader.apk](https://github.com/thanaton20/ficbook-downloader/releases/latest/download/Ficbook-Downloader.apk) | Android 10 or later |
| Linux, Intel Mac | [Install from source](#install-from-source) | Python 3.11 or later |

All versions are on the [Releases page](https://github.com/thanaton20/ficbook-downloader/releases).

## Download for Mac

Download [Ficbook-Downloader.dmg](https://github.com/thanaton20/ficbook-downloader/releases/latest/download/Ficbook-Downloader.dmg). This build is for Apple silicon Macs. On an Intel Mac, [install from source](#install-from-source).

1. Open the disk image.
2. Drag **Ficbook Downloader** onto the Applications folder.
3. Open the app from Applications.

The first launch can show **"Ficbook Downloader" Not Opened**, with the text that Apple could not verify the app. Click **Done**. Do not click **Move to Trash**. Then open Terminal and run:

```bash
xattr -dr com.apple.quarantine "/Applications/Ficbook Downloader.app"
```

Open the app from Applications again. The warning is gone.

To update, download the new disk image and drag the app onto Applications again, replacing the old one.

## Download for Windows

Download [Ficbook-Downloader.exe](https://github.com/thanaton20/ficbook-downloader/releases/latest/download/Ficbook-Downloader.exe) and double-click it.

Windows may show a SmartScreen warning because the file is not signed. Choose **More info**, then **Run anyway**.

The Windows file is still version 0.3.0. It does not have the newer look, link numbers, or book previews yet. To get them now, [install from source](#install-from-source).

## Download for iPhone

The iPhone app is not in the App Store. You install it from a computer with [Sideloadly](https://sideloadly.io), using your own Apple ID.

1. On a Mac or Windows PC, install [Sideloadly](https://sideloadly.io).
2. Download [Ficbook-Downloader.ipa](https://github.com/thanaton20/ficbook-downloader/releases/latest/download/Ficbook-Downloader.ipa) to that computer.
3. Connect the iPhone with a cable. Drag **Ficbook-Downloader.ipa** into Sideloadly, enter your Apple ID, and click **Start**.
4. On the iPhone, open **Settings › Privacy & Security › Developer Mode**, turn it on, and restart when asked.
5. Open **Settings › General › VPN & Device Management**, tap your Apple ID, and tap **Trust**.
6. Open **Ficbook Downloader** from the home screen.

It needs iOS 16.4 or later. With a free Apple ID the app stops opening after 7 days; install it again with Sideloadly to renew it. AltStore works too. Saved books are in **Files › On My iPhone › Ficbook Downloader**.

## Download for Android

1. On the phone, download [Ficbook-Downloader.apk](https://github.com/thanaton20/ficbook-downloader/releases/latest/download/Ficbook-Downloader.apk).
2. Open the downloaded file. If Android asks, allow your browser or Files app to install unknown apps, then go back and tap **Install**.
3. If Google Play Protect warns that the app is unknown, tap **More details**, then **Install anyway**.

It needs Android 10 or later. Saved books are in **Downloads › Ficbook**. A newer `Ficbook-Downloader.apk` installs over the old one.

The phone apps open ficbook pages in the phone's own browser view. If ficbook shows a security check or an age confirmation, the app shows that page so you can answer it. See [mobile/README.md](mobile/README.md) for how they are built.

## Install from source

This works on macOS (Intel or Apple silicon), Windows, and Linux. It needs Python 3.11 or later and Git.

On macOS or Linux:

```bash
git clone https://github.com/thanaton20/ficbook-downloader.git
cd ficbook-downloader
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

On Windows:

```bat
git clone https://github.com/thanaton20/ficbook-downloader.git
cd ficbook-downloader
py -m venv .venv
.venv\Scripts\activate
pip install -e .
```

On Linux the window needs Tk. On Debian or Ubuntu run `sudo apt install python3-tk`; on Fedora run `sudo dnf install python3-tkinter`.

Then `ficbook-gui` opens the window and `ficbook-dl` runs the command line. To install without cloning:

```bash
pip install git+https://github.com/thanaton20/ficbook-downloader.git
```

## Use the window

The downloaded app opens this window. From a source install, run:

```bash
ficbook-gui
```

On Windows, from the project folder:

```bat
.venv\Scripts\activate
ficbook-gui
```

`ficbook-dl --gui` opens the same window. A sidebar on the left has three pages: **Download**, **Library**, and **About**. At the bottom of the sidebar, **EN**, **RU**, and **UK** switch the language. The choice is remembered, and text-file labels such as Author and Series follow it. On the command line, use `--lang en`, `--lang ru`, or `--lang uk`.

### Download

1. In **Story links**, paste one link per line. A story id works too, and a link to a single chapter still saves the whole story. Each link gets a number for its place in the download order, and a preview with the cover, title, and author appears under the box. Stories without a cover show their title on a coloured block.
2. **Save to** starts as your `Stories` folder. **Browse** picks another folder, and that choice is kept the next time you open the app.
3. **TXT**, **EPUB**, and **FB2** start selected. Click a format to turn it off.
4. **Pause (seconds)** is the wait between requests. It starts at `1.5`.
5. Click **Download**. The button changes to **Stop**. The log prints each chapter, then a `saved …` line for every file.

**Stop** halts the download before the next chapter. Files already written stay where they are. Each story is saved as `Title — Author` with the extensions you left on.

### Library

Paste an author link, such as `https://ficbook.net/authors/2`, and click **Show books**. The page lists that author's books. **TXT**, **EPUB**, and **FB2** on this page choose the file type. The author's picture and name sit above a grid of book covers. **Download** under a book saves it in the selected types, into the folder chosen on the Download page. Click a cover to see the book title, the author's name, the series name, and a larger cover.

### About

**About** is the page for the person who made the app, Yaroslau Hatalski. **Open GitHub** goes to [github.com/thanaton20](https://github.com/thanaton20).

## Use the command line

```bash
ficbook-dl https://ficbook.net/readfic/1
ficbook-dl 1 13340733 -o ~/Stories --delay 2 --format epub,fb2
```

A chapter link works too. `https://ficbook.net/readfic/<id>/<part>` still saves the whole story.

Files land in `stories/` unless you pass `--out`. `--format` accepts `txt`, `epub`, and `fb2`. The default is all three. The name is `Title — Author.txt`, `.epub`, and `.fb2`.

```
Title
Author: Name
https://ficbook.net/readfic/<id>
Series: Series name (2)
Fandom: ...
PG-13 · Finished
Tags: ...

Description

Chapter title

Chapter text
```

## Limits

The story has to be readable on the public page. On a computer, an age check or a chapter without text stops that story and the app continues with the next link. On a phone, the app shows the age check so you can confirm it. Keep the copies for your own reading, and leave a pause between requests so the site is not hammered. The default pause is 1.5 seconds.
