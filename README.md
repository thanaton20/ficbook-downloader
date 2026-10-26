# ficbook-downloader

A command-line app that saves [ficbook.net](https://ficbook.net/) stories as UTF-8 text files.

You give it story links. It reads each public story page, follows the chapter list, and writes one `.txt` file per story. It waits between requests. It does not open a browser.

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

## Use

```bash
ficbook-dl https://ficbook.net/readfic/1
ficbook-dl 1 13340733 -o ~/Stories --delay 2
```

A chapter link works too. `https://ficbook.net/readfic/<id>/<part>` still saves the whole story.

Files land in `stories/` unless you pass `--out`. The name is `Title — Author.txt`.

```
Title
Author
https://ficbook.net/readfic/<id>
PG-13 · Finished

Description

Chapter title

Chapter text
```

## Limits

The story has to be readable on the public page. An age check or a chapter without text stops that story and the app continues with the next link. Keep the copies for your own reading, and leave a pause between requests so the site is not hammered. The default pause is 1.5 seconds.
