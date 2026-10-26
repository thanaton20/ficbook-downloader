# ficbook-downloader

English | [Русский](README.ru.md)

A command-line and desktop app that saves [ficbook.net](https://ficbook.net/) stories as UTF-8 text, EPUB, and FB2. The window runs on macOS and Windows.

You give it story links. It reads each public story page, follows the chapter list, and writes one file per format. Each chapter is its own section. Author, translator, series name and number, fandom, tags, and description are stored in the file. A cover is included when the story has one. It waits between requests. It does not open a browser.

Ficbook answers ordinary HTTP libraries with a security check. This app uses [curl_cffi](https://github.com/lexiforest/curl_cffi) so those requests look like a normal browser connection and the public story HTML comes back.

## Install

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

On macOS, after the install commands above:

```bash
ficbook-gui
```

On Windows, from the project folder:

```bat
.venv\Scripts\activate
ficbook-gui
```

`ficbook-dl --gui` opens the same window. The title bar says **Ficbook Downloader**.

1. In **Story links**, paste one link per line. A story id works too, and a link to a single chapter still saves the whole story.
2. **Save to** is your `Stories` folder. Click **Browse** to pick another folder.
3. Under **Formats**, leave **TXT**, **EPUB**, and **FB2** checked, or clear the ones you do not want.
4. **Pause (seconds)** is the wait between requests. It starts at `1.5`.
5. Click **Download**. The button changes to **Stop**. The log under it prints each chapter, then a `saved …` line for every file.

The status line next to the button ends with how many stories were saved. Click **Stop** to halt before the next chapter. Files already written stay where they are.

Each story is saved as `Title — Author` with the extensions you checked.

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
