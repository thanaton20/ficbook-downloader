# ficbook-downloader

English | [Русский](README.ru.md) | [Українська](README.uk.md)

A command-line and desktop app that saves [ficbook.net](https://ficbook.net/) stories as UTF-8 text, EPUB, and FB2. The window runs on macOS and Windows.

You give it story links. It reads each public story page, follows the chapter list, and writes one file per format. Each chapter is its own section. Author, translator, series name and number, fandom, tags, and description are stored in the file. A cover is included when the story has one. It waits between requests. It does not open a browser.

Ficbook answers ordinary HTTP libraries with a security check. This app uses [curl_cffi](https://github.com/lexiforest/curl_cffi) so those requests look like a normal browser connection and the public story HTML comes back.

## Download for Mac

Download [Ficbook-Downloader.dmg](https://github.com/thanaton20/ficbook-downloader/releases/latest/download/Ficbook-Downloader.dmg). This build is for Apple silicon Macs.

1. Open the disk image.
2. Drag **Ficbook Downloader** onto the Applications folder.
3. Open the app from Applications.

The first launch can show **"Ficbook Downloader" Not Opened**, with the text that Apple could not verify the app. Click **Done**. Do not click **Move to Trash**. Then open Terminal and run:

```bash
xattr -dr com.apple.quarantine "/Applications/Ficbook Downloader.app"
```

Open the app from Applications again. The warning is gone.

## Download for Windows

Download [Ficbook-Downloader.exe](https://github.com/thanaton20/ficbook-downloader/releases/latest/download/Ficbook-Downloader.exe) and double-click it.

Windows may show a SmartScreen warning because the file is not signed. Choose **More info**, then **Run anyway**.

## Download for iPhone

Download [Ficbook.ipa](https://github.com/thanaton20/ficbook-downloader/releases/latest/download/Ficbook.ipa) and install it with [Sideloadly](https://sideloadly.io) or AltStore using your Apple ID. It needs iOS 16.4 or later. With a free Apple ID, reinstall it every 7 days. Saved books are in **Files › On My iPhone › Ficbook**.

## Download for Android

On the phone, download [Ficbook.apk](https://github.com/thanaton20/ficbook-downloader/releases/latest/download/Ficbook.apk) and open it. Allow installing from your browser when Android asks. It needs Android 10 or later. Saved books are in **Downloads › Ficbook**.

The phone apps open ficbook pages in the phone's own browser view. If ficbook shows a security check or an age confirmation, the app shows that page so you can answer it. See [mobile/README.md](mobile/README.md) for how they are built.

## Install from source

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

From the GitHub repository:

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

1. In **Story links**, paste one link per line. A story id works too, and a link to a single chapter still saves the whole story.
2. **Save to** starts as your `Stories` folder. **Browse** picks another folder, and that choice is kept the next time you open the app.
3. **TXT**, **EPUB**, and **FB2** start selected. Click a format to turn it off.
4. **Pause (seconds)** is the wait between requests. It starts at `1.5`.
5. Click **Download**. The button changes to **Stop**. The log prints each chapter, then a `saved …` line for every file.

**Stop** halts the download before the next chapter. Files already written stay where they are. Each story is saved as `Title — Author` with the extensions you left on.

### Library

Paste an author link, such as `https://ficbook.net/authors/2`, and click **Show books**. The page lists that author's books. **TXT**, **EPUB**, and **FB2** on this page choose the file type. **Download** on a row saves that book in the selected types, into the folder chosen on the Download page. **Preview** opens the book title, the author's name, the series name, and the cover.

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

The story has to be readable on the public page. An age check or a chapter without text stops that story and the app continues with the next link. Keep the copies for your own reading, and leave a pause between requests so the site is not hammered. The default pause is 1.5 seconds.
