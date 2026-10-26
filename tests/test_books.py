import io
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

from ficbook_dl.download import save_story
from ficbook_dl.formats.epub import build_epub
from ficbook_dl.formats.fb2 import build_fb2
from ficbook_dl.parse import Chapter, Story


def tiny_jpeg() -> bytes:
    from PIL import Image

    image = Image.new("RGB", (12, 16), (30, 60, 90))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def sample() -> Story:
    return Story(
        story_id="9",
        title="Ink",
        author="Daniel May",
        url="https://ficbook.net/readfic/9",
        description="A description.",
        authors=["Daniel May"],
        translators=["Plush"],
        series_name="Fresh Ink",
        series_index=2,
        fandoms=["Originals"],
        tags=["Romance"],
        rating="NC-21",
        cover_jpeg=tiny_jpeg(),
        chapters=[
            Chapter(title="One", url="https://ficbook.net/readfic/9/1", paragraphs=["Alpha", "Hello <i>there</i>"]),
            Chapter(title="Two", url="https://ficbook.net/readfic/9/2", paragraphs=["Omega"]),
        ],
    )


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class BookTests(unittest.TestCase):
    def test_epub_has_chapters_series_author_and_cover(self):
        data = build_epub(sample())
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            self.assertEqual(names[0], "mimetype")
            self.assertEqual(archive.getinfo("mimetype").compress_type, zipfile.ZIP_STORED)
            self.assertEqual(archive.read("mimetype"), b"application/epub+zip")
            opf = archive.read("OEBPS/content.opf").decode("utf-8")
            first = archive.read("OEBPS/chapter-001.xhtml").decode("utf-8")
            second = archive.read("OEBPS/chapter-002.xhtml").decode("utf-8")
            self.assertIn("OEBPS/cover.jpg", names)
            self.assertGreater(len(archive.read("OEBPS/cover.jpg")), 100)
        self.assertIn("<dc:creator id=\"author-1\">Daniel May</dc:creator>", opf)
        self.assertIn('property="role" scheme="marc:relators">aut</meta>', opf)
        self.assertIn('property="role" scheme="marc:relators">trl</meta>', opf)
        self.assertIn('<meta name="calibre:series" content="Fresh Ink"/>', opf)
        self.assertIn('<meta name="calibre:series_index" content="2"/>', opf)
        self.assertIn('property="group-position">2</meta>', opf)
        self.assertIn('name="cover" content="cover-image"', opf)
        self.assertIn("<h1>One</h1>", first)
        self.assertIn("<p>Alpha</p>", first)
        self.assertIn("<i>there</i>", first)
        self.assertNotIn("Omega", first)
        self.assertIn("<h1>Two</h1>", second)
        self.assertIn("<p>Omega</p>", second)
        self.assertNotIn("Alpha", second)
        ElementTree.fromstring(opf)
        ElementTree.fromstring(first)

    def test_fb2_has_chapters_series_author_and_cover(self):
        root = ElementTree.fromstring(build_fb2(sample()))
        tags = [local(node.tag) for node in root.iter()]
        self.assertIn("author", tags)
        self.assertIn("translator", tags)
        self.assertIn("sequence", tags)
        self.assertIn("coverpage", tags)
        self.assertIn("binary", tags)
        sections = [node for node in root.iter() if local(node.tag) == "section"]
        self.assertEqual(len(sections), 2)
        titles = []
        for section in sections:
            title = next(child for child in section.iter() if local(child.tag) == "p")
            titles.append(title.text)
        self.assertEqual(titles, ["One", "Two"])
        sequence = next(node for node in root.iter() if local(node.tag) == "sequence")
        self.assertEqual(sequence.attrib["name"], "Fresh Ink")
        self.assertEqual(sequence.attrib["number"], "2")
        author = next(node for node in root.iter() if local(node.tag) == "author")
        self.assertEqual(next(node.text for node in author if local(node.tag) == "first-name"), "Daniel")
        self.assertEqual(next(node.text for node in author if local(node.tag) == "last-name"), "May")
        first_section = "".join(root.itertext())
        self.assertIn("Alpha", first_section)
        emphasis = [node for node in root.iter() if local(node.tag) == "emphasis"]
        self.assertEqual(emphasis[0].text, "there")

    def test_save_writes_all_formats(self):
        with TemporaryDirectory() as folder:
            paths = save_story(sample(), Path(folder))
            self.assertEqual([path.suffix for path in paths], [".txt", ".epub", ".fb2"])
            for path in paths:
                self.assertTrue(path.exists())
                self.assertGreater(path.stat().st_size, 80)


if __name__ == "__main__":
    unittest.main()
