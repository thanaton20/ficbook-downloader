import unittest

from ficbook_dl.errors import AgeCheck, InvalidLink, MissingText, SecurityCheck
from ficbook_dl.formats.txt import render
from ficbook_dl.parse import canonical_story_url, parse_chapter, parse_story, series_index

STORY = """
<html><head><title>Story</title></head><body>
<h1 class="heading">Sample Story</h1>
<a class="word-break" href="/authors/7">Ada</a>
<div itemprop="description">A short description.</div>
<div class="ds-label ds-label-rating-PG-13">PG-13</div>
<div class="ds-label ds-label-status-finished">Finished</div>
<ul class="list-of-fanfic-parts">
  <li class="part"><a class="part-link" href="/readfic/7/10#part_content"><h3>One</h3></a></li>
  <li class="part"><a class="part-link" href="/readfic/7/11#part_content"><h3>Two</h3></a></li>
  <li class="part"><a href="/authors/7">Ada</a></li>
</ul>
</body></html>
"""

CHAPTER = """
<html><body>
<div id="content" class="part_text">Hello\r\n\r\nThere.</div>
</body></html>
"""

SINGLE = """
<html><body>
<h1 class="heading">Only One</h1>
<a class="word-break" href="/authors/3">Bea</a>
<h2>Chapter</h2>
<div id="content">Lone chapter.</div>
</body></html>
"""


class ParseTests(unittest.TestCase):
    def test_canonical_url_accepts_id_and_chapter_link(self):
        self.assertEqual(
            canonical_story_url("7"),
            "https://ficbook.net/readfic/7",
        )
        self.assertEqual(
            canonical_story_url("https://www.ficbook.net/readfic/7/10#part_content"),
            "https://ficbook.net/readfic/7",
        )

    def test_canonical_url_rejects_other_sites(self):
        with self.assertRaises(InvalidLink):
            canonical_story_url("https://example.com/readfic/7")

    def test_story_with_chapters_ignores_extra_links(self):
        story = parse_story(STORY, "https://ficbook.net/readfic/7")
        self.assertEqual(story.title, "Sample Story")
        self.assertEqual(story.author, "Ada")
        self.assertEqual(story.details, "PG-13 · Finished")
        self.assertEqual([chapter.title for chapter in story.chapters], ["One", "Two"])
        self.assertEqual(
            story.chapters[0].url,
            "https://ficbook.net/readfic/7/10",
        )
        self.assertEqual(story.chapters[0].paragraphs, [])

    def test_single_page_story_keeps_its_text(self):
        story = parse_story(SINGLE, "https://ficbook.net/readfic/3")
        self.assertEqual(story.chapters[0].body, "Lone chapter.")
        text = render(story)
        self.assertIn("Only One\nAuthor: Bea\nhttps://ficbook.net/readfic/3", text)
        self.assertIn("Lone chapter.", text)

    def test_chapter_normalizes_newlines(self):
        self.assertEqual(parse_chapter(CHAPTER, "https://ficbook.net/readfic/7/10"), "Hello\n\nThere.")

    def test_age_check_and_security_check(self):
        with self.assertRaises(AgeCheck):
            parse_story(
                '<html><div id="adultCoverWarning">18+</div></html>',
                "https://ficbook.net/readfic/9",
            )
        with self.assertRaises(SecurityCheck):
            parse_chapter(
                "<html><title>Проверка безопасности | Книга Фанфиков</title></html>",
                "https://ficbook.net/readfic/9/1",
            )

    def test_series_author_cover_and_paragraphs(self):
        html = """
        <html><head>
          <meta property="og:image" content="https://assets.teinon.net/assets/design/ogimage/socials_ru.png"/>
          <meta property="og:image" content="https://assets.teinon.net/fanfic-covers/m_cover.webp"/>
        </head><body>
        <section class="fanfic-hat">
          <h1 class="heading">Ink</h1>
          <a class="word-break" href="/authors/5">Plush</a>
          <div class="ds-label ds-label-translate">Перевод</div>
          <div class="ds-label ds-label-rating-NC-21">NC-21</div>
          <div class="ds-label ds-label-status-finished">Завершён</div>
          <div class="direction direction-slash">Слэш</div>
          <div class="promo"><div class="direction">Чужое</div></div>
          <div class="description word-break">
            <strong>Автор оригинала:</strong><div>Daniel May</div>
            <strong>Серия:</strong><div><a href="/series/20385">Свежий вкус</a></div>
            <strong>Фэндом:</strong><div><a href="/fanfiction/x">Ориджиналы</a></div>
            <strong>Пэйринг и персонажи:</strong><div><a href="/pairings/x">А/Б</a></div>
            <strong>Метки:</strong><div><a href="/tags/1">Романтика</a></div>
            <strong>Описание:</strong><div>Описание книги</div>
            <strong>Посвящение:</strong><div>Другу</div>
          </div>
        </section>
        <ul class="list-of-fanfic-parts">
          <li><a class="part-link" href="/readfic/9/1#part_content"><h3>Первая</h3></a></li>
          <li><a class="part-link" href="/readfic/9/2#part_content"><h3>Вторая</h3></a></li>
        </ul>
        </body></html>
        """
        story = parse_story(html, "https://ficbook.net/readfic/9")
        self.assertEqual(story.authors, ["Daniel May"])
        self.assertEqual(story.translators, ["Plush"])
        self.assertEqual(story.series_name, "Свежий вкус")
        self.assertEqual(story.series_url, "https://ficbook.net/series/20385")
        self.assertEqual(story.cover_url, "https://assets.teinon.net/fanfic-covers/m_cover.webp")
        self.assertEqual(story.fandoms, ["Ориджиналы"])
        self.assertEqual(story.tags, ["Романтика"])
        self.assertEqual(story.directions, ["Слэш"])
        self.assertEqual([chapter.title for chapter in story.chapters], ["Первая", "Вторая"])
        self.assertEqual(
            series_index(
                """
                <a class="visit-link" href="/readfic/8">Other</a>
                <a class="visit-link" href="/readfic/9">Ink</a>
                <a class="js-promo-fanfic" href="/readfic/100">Ad</a>
                """,
                "9",
            ),
            2,
        )

    def test_italic_across_lines_closes_on_each_paragraph(self):
        from ficbook_dl.parse import parse_chapter_content

        chapter = parse_chapter_content(
            "<div id='content'><i>Hello\nthere</i>\nNext</div>",
            "https://ficbook.net/readfic/1",
        )
        self.assertEqual(chapter.paragraphs, ["<i>Hello</i>", "<i>there</i>", "Next"])

    def test_italic_line_is_its_own_paragraph(self):
        body = parse_chapter(
            '<div id="content">Hello <i>there</i>\nNext</div>',
            "https://ficbook.net/readfic/7/10",
        )
        self.assertEqual(body, "Hello there\n\nNext")

    def test_author_works_skip_promos_and_find_next_page(self):
        from ficbook_dl.parse import canonical_author_works_url, parse_author_works

        html = """
        <html><head><title>Ada – profile</title></head><body>
        <h1>Ada</h1>
        <a class="visit-link" href="/readfic/10">First book</a>
        <a class="visit-link js-promo-fanfic" href="/readfic/99">Ad</a>
        <a class="visit-link" href="/readfic/10">First book</a>
        <a class="visit-link" href="/readfic/11">Second book</a>
        <a href="/authors/4/profile/works?p=2">2</a>
        </body></html>
        """
        self.assertEqual(
            canonical_author_works_url("https://ficbook.net/authors/4"),
            "https://ficbook.net/authors/4/profile/works",
        )
        name, works, nxt = parse_author_works(html, "https://ficbook.net/authors/4/profile/works")
        self.assertEqual(name, "Ada")
        self.assertEqual([work.title for work in works], ["First book", "Second book"])
        self.assertEqual(nxt, "https://ficbook.net/authors/4/profile/works?p=2")

    def test_author_works_covers_and_avatar(self):
        from ficbook_dl.parse import parse_author_avatar, parse_author_works

        html = """
        <html><head><title>Ada – profile</title></head><body>
        <a href="/authors/99"><img src="https://assets.teinon.net/avatars/other.png"></a>
        <a href="/authors/4"><img alt="Ada" src="https://assets.teinon.net/avatars/ada.webp"></a>
        <article class="fanfic-inline"><a class="visit-link" href="/readfic/10">One</a>
          <img src="https://assets.teinon.net/fanfic-covers/m_one.jpg"></article>
        <article class="fanfic-inline"><a class="visit-link" href="/readfic/11">Two</a></article>
        </body></html>
        """
        url = "https://ficbook.net/authors/4/profile/works"
        _, works, _ = parse_author_works(html, url)
        self.assertEqual([work.cover_url for work in works], ["https://assets.teinon.net/fanfic-covers/m_one.jpg", ""])
        self.assertEqual(parse_author_avatar(html, url), "https://assets.teinon.net/avatars/ada.webp")

    def test_promo_inside_chapter_text_is_skipped(self):
        body = parse_chapter(
            '<div id="content">Before<div class="fanfic-text-promo js-text-insert">'
            '<a class="js-promo-fanfic" href="/readfic/1">ПРОМО Other</a></div>After</div>',
            "https://ficbook.net/readfic/7/10",
        )
        self.assertEqual(body, "Before\n\nAfter")

    def test_missing_chapter_text(self):
        with self.assertRaises(MissingText):
            parse_chapter("<html><body>empty</body></html>", "https://ficbook.net/readfic/7/10")


if __name__ == "__main__":
    unittest.main()
