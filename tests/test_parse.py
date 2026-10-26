import unittest

from ficbook_dl.errors import AgeCheck, InvalidLink, MissingText, SecurityCheck
from ficbook_dl.parse import canonical_story_url, parse_chapter, parse_story, render

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
        self.assertIsNone(story.chapters[0].body)

    def test_single_page_story_keeps_its_text(self):
        story = parse_story(SINGLE, "https://ficbook.net/readfic/3")
        self.assertEqual(story.chapters[0].body, "Lone chapter.")
        text = render(story)
        self.assertIn("Only One\nBea\nhttps://ficbook.net/readfic/3", text)
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

    def test_missing_chapter_text(self):
        with self.assertRaises(MissingText):
            parse_chapter("<html><body>empty</body></html>", "https://ficbook.net/readfic/7/10")


if __name__ == "__main__":
    unittest.main()
