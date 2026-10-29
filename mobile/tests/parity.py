"""Check that the phone apps' JavaScript core reads pages and writes books like the desktop app.

Run from the repository root:  python3 mobile/tests/parity.py
Needs Node and `npm install` in mobile/.
"""

from __future__ import annotations

import base64
import io
import json
import subprocess
import sys
import unittest
import zipfile
from dataclasses import asdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from ficbook_dl import __version__  # noqa: E402
from ficbook_dl.errors import FicbookError  # noqa: E402
from ficbook_dl.formats.epub import build_epub  # noqa: E402
from ficbook_dl.formats.fb2 import build_fb2  # noqa: E402
from ficbook_dl.formats.txt import render  # noqa: E402
from ficbook_dl.i18n import TEXT, t  # noqa: E402
from ficbook_dl.parse import (  # noqa: E402
    canonical_author_works_url,
    canonical_story_url,
    file_stem,
    parse_author_works,
    parse_chapter_content,
    parse_story,
    series_index,
)
from tests.test_parse import CHAPTER, SINGLE, STORY  # noqa: E402

RICH_STORY = """
<html><head>
  <meta property="og:image" content="https://assets.teinon.net/assets/design/ogimage/socials_ru.png"/>
  <meta property="og:image" content="https://assets.teinon.net/fanfic-covers/m_cover.webp"/>
</head><body>
<section class="fanfic-hat">
  <h1 class="heading">Ink &amp; "Paper"</h1>
  <a class="word-break" href="/authors/5">Plush</a>
  <div class="ds-label ds-label-rating-NC-21">NC-21</div>
  <div class="ds-label ds-label-status-finished">Завершён</div>
  <div class="direction direction-slash">Слэш</div>
  <div class="promo"><div class="direction">Чужое</div></div>
  <div class="description word-break">
    <strong>Автор оригинала:</strong><div>Daniel May</div>
    <strong>Серия:</strong><div><a href="/series/20385">Свежий вкус</a></div>
    <strong>Фэндом:</strong><div><a href="/fanfiction/x">Ориджиналы</a></div>
    <strong>Пэйринг и персонажи:</strong><div><a href="/pairings/x">А/Б</a>, <a href="/pairings/y">В</a></div>
    <strong>Метки:</strong><div><a href="/tags/1">Романтика</a><a href="/tags/2">Драма</a></div>
    <strong>Описание:</strong><div>Первая строка<br>Вторая <b>строка</b><span>Спойлеры</span></div>
    <strong>Посвящение:</strong><div>Другу</div>
    <strong>Примечания:</strong><div>Спасибо <i>всем</i></div>
  </div>
</section>
<ul class="list-of-fanfic-parts">
  <li><a class="part-link" href="/readfic/9/1#part_content"><h3>Первая</h3></a></li>
  <li><a class="part-link" href="https://ficbook.net/readfic/9/2"><h3>Вторая <script>x()</script></h3></a></li>
  <li><a class="part-link" href="/readfic/9/1">Dup</a></li>
</ul>
</body></html>
"""

RICH_CHAPTER = """
<html><body>
<h2>Глава <em>первая</em></h2>
<div class="part-comment-top"><p>Note one</p>\n<p>  Note   two </p></div>
<div id="content">Start <i>soft\nloud</i> end.<br>Line &amp; "quotes" 'apostrophe' &lt;tag&gt;
<p>Para <b>bold <i>both</i></b></p><div>Block<br/>after</div><style>.x{}</style><script>var a = 1;</script>
<blockquote>Quote</blockquote><ul><li>One</li><li>Two</li></ul>Tail\r\nwin
<div class="fanfic-text-promo js-text-insert"><a class="js-promo-fanfic" href="/readfic/1">ПРОМО Other story</a></div>After promo</div>
<div class="part-comment-bottom">Bye</div>
</body></html>
"""

WORKS = """
<html><head><title>Ada – profile</title></head><body>
<a class="visit-link" href="/readfic/10">First book</a>
<a class="visit-link js-promo-fanfic" href="/readfic/99">Ad</a>
<a class="visit-link" href="/readfic/10/">First book</a>
<a class="visit-link" href="https://ficbook.net/readfic/11">Second <b>book</b></a>
<a href="/authors/4/profile/works?p=2">2</a><a href="/authors/4/profile/works?p=3">3</a>
</body></html>
"""

SERIES = """
<a class="visit-link" href="/readfic/8">Other</a>
<a class="visit-link" href="/readfic/9">Ink</a>
<a class="visit-link" href="/readfic/8/">Again</a>
"""


def run_js(cases: list[dict]) -> list:
    out = subprocess.run(
        ["node", str(Path(__file__).with_name("run_js.cjs"))],
        input=json.dumps(cases),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


def python_result(call):
    try:
        value = call()
    except FicbookError as exc:
        return {"ok": False, "error": exc.code, "params": exc.params}
    return {"ok": True, "data": value}


def story_dict(story) -> dict:
    data = asdict(story)
    data.pop("cover_jpeg")
    return data


class ParityTests(unittest.TestCase):
    def test_canonical_links(self):
        stories = ["12345", "abc-DEF", "https://ficbook.net/readfic/7/10#part", "https://www.ficbook.net/readfic/x",
                   "", "  ", "bad id", "https://example.com/readfic/1", "ficbook.net/readfic/1", "https://ficbook.net/authors/1"]
        authors = ["2", "https://ficbook.net/authors/4", "ficbook.net/authors/4/profile", "/authors/x/works",
                   "", "https://example.com/authors/1", "https://ficbook.net/readfic/1"]
        js_story, js_author = run_js([
            {"kind": "canonical", "fn": "canonicalStoryUrl", "values": stories},
            {"kind": "canonical", "fn": "canonicalAuthorWorksUrl", "values": authors},
        ])
        for values, js, fn in ((stories, js_story, canonical_story_url), (authors, js_author, canonical_author_works_url)):
            for value, got in zip(values, js):
                expected = python_result(lambda: fn(value))
                expected.pop("params", None)
                self.assertEqual(got, expected, value)

    def test_pages(self):
        notes = t("ru", "notes")
        cases = [
            ("story", STORY, "https://ficbook.net/readfic/7", lambda: story_dict(parse_story(STORY, "https://ficbook.net/readfic/7", "ru"))),
            ("story", SINGLE, "https://ficbook.net/readfic/3", lambda: story_dict(parse_story(SINGLE, "https://ficbook.net/readfic/3", "ru"))),
            ("story", RICH_STORY, "https://ficbook.net/readfic/9", lambda: story_dict(parse_story(RICH_STORY, "https://ficbook.net/readfic/9", "ru"))),
            ("story", '<html><div id="adultCoverWarning">18+</div></html>', "https://ficbook.net/readfic/9",
             lambda: story_dict(parse_story('<html><div id="adultCoverWarning">18+</div></html>', "https://ficbook.net/readfic/9"))),
            ("chapter", CHAPTER, "https://ficbook.net/readfic/7/10",
             lambda: asdict(parse_chapter_content(CHAPTER, "https://ficbook.net/readfic/7/10", "ru"))),
            ("chapter", RICH_CHAPTER, "https://ficbook.net/readfic/9/1",
             lambda: asdict(parse_chapter_content(RICH_CHAPTER, "https://ficbook.net/readfic/9/1", "ru"))),
            ("chapter", "<html><head><title>Проверка безопасности | Книга Фанфиков</title></head></html>", "https://ficbook.net/readfic/9/1",
             lambda: parse_chapter_content("<html><head><title>Проверка безопасности | Книга Фанфиков</title></head></html>", "x")),
            ("chapter", "<html><body>empty</body></html>", "https://ficbook.net/readfic/7/10",
             lambda: parse_chapter_content("<html><body>empty</body></html>", "https://ficbook.net/readfic/7/10")),
            ("works", WORKS, "https://ficbook.net/authors/4/profile/works", lambda: works_dict(WORKS, "https://ficbook.net/authors/4/profile/works")),
            ("works", WORKS, "https://ficbook.net/authors/4/profile/works?p=2#top", lambda: works_dict(WORKS, "https://ficbook.net/authors/4/profile/works?p=2#top")),
            ("series", SERIES, "https://ficbook.net/series/1", lambda: series_index(SERIES, "9")),
        ]
        js = run_js([
            {"kind": kind, "html": html, "url": url,
             "args": {"url": url, "notesLabel": notes, "chapterLabel": t("ru", "chapter"), "storyId": "9"}}
            for kind, html, url, _ in cases
        ])
        for (kind, html, url, call), got in zip(cases, js):
            with self.subTest(kind=kind, url=url, html=html[:40]):
                self.assertEqual(got, python_result(call))

    def test_books(self):
        story = parse_story(RICH_STORY, "https://ficbook.net/readfic/9", "en")
        story.chapters[0].paragraphs = parse_chapter_content(RICH_CHAPTER, story.chapters[0].url, "en").paragraphs
        story.chapters[1].paragraphs = ["<i>Broken <b>nesting</i></b> &amp; text", "Plain", "  "]
        story.series_index = 2
        story.cover_jpeg = b"\xff\xd8\xff\xe0" + bytes(range(256)) * 3
        bare = parse_story(SINGLE, "https://ficbook.net/readfic/3", "en")
        for language in ("en", "ru"):
            labels = {key: value for key, value in TEXT[language].items() if isinstance(value, str)}
            for item in (story, bare):
                with self.subTest(language=language, story=item.title):
                    cover = base64.b64encode(item.cover_jpeg).decode() if item.cover_jpeg else None
                    (got,) = run_js([{
                        "kind": "books", "story": story_dict(item), "labels": labels, "cover": cover,
                        "version": __version__, "today": date.today().isoformat(),
                    }])
                    self.assertEqual(got["txt"], render(item, language))
                    self.assertEqual(got["fb2"], build_fb2(item, language))
                    self.assertEqual(got["stem"], file_stem(item))
                    expected = zipfile.ZipFile(io.BytesIO(build_epub(item, language)))
                    actual = zipfile.ZipFile(io.BytesIO(base64.b64decode(got["epub"])))
                    self.assertIsNone(actual.testzip())
                    self.assertEqual(actual.namelist(), expected.namelist())
                    self.assertEqual(actual.getinfo("mimetype").compress_type, zipfile.ZIP_STORED)
                    for name in expected.namelist():
                        self.assertEqual(actual.read(name), expected.read(name), name)


def works_dict(html: str, url: str) -> dict:
    name, works, nxt = parse_author_works(html, url)
    return {"name": name, "works": [asdict(work) for work in works], "next": nxt}


if __name__ == "__main__":
    unittest.main()
