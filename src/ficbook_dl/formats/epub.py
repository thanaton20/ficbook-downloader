"""EPUB 3 with one file per chapter, plus series and cover metadata."""

from __future__ import annotations

import html
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from bs4 import BeautifulSoup

from ficbook_dl.i18n import t
from ficbook_dl.parse import Story

_STYLE = """
body { font-family: Georgia, "Times New Roman", serif; line-height: 1.45; margin: 1em; }
h1 { font-size: 1.4em; text-align: center; margin: 1.2em 0 1em; page-break-before: always; }
p { margin: 0.35em 0; text-indent: 1.15em; }
p.note { font-style: italic; text-indent: 0; }
.cover { text-align: center; margin: 0; text-indent: 0; }
.cover img { max-width: 100%; height: auto; }
"""


def write_epub(story: Story, path: Path, language: str = "en") -> None:
    path.write_bytes(build_epub(story, language))


def build_epub(story: Story, language: str = "en") -> bytes:
    import io

    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        info = ZipInfo("mimetype")
        info.compress_type = ZIP_STORED
        archive.writestr(info, "application/epub+zip")
        _add(archive, "META-INF/container.xml", _container())
        _add(archive, "OEBPS/style.css", _STYLE.strip() + "\n")
        _add(archive, "OEBPS/nav.xhtml", _nav(story))
        _add(archive, "OEBPS/toc.ncx", _ncx(story))
        if story.cover_jpeg:
            archive.writestr("OEBPS/cover.jpg", story.cover_jpeg)
            _add(archive, "OEBPS/cover.xhtml", _cover_page(story))
        for index, chapter in enumerate(story.chapters, start=1):
            _add(archive, f"OEBPS/chapter-{index:03d}.xhtml", _chapter_page(chapter.title, chapter.paragraphs))
        _add(archive, "OEBPS/content.opf", _opf(story, language))
    return buffer.getvalue()


def _add(archive: ZipFile, name: str, text: str) -> None:
    info = ZipInfo(name)
    info.compress_type = ZIP_DEFLATED
    archive.writestr(info, text.encode("utf-8"))


def _container() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def _opf(story: Story, language: str = "en") -> str:
    creators = []
    for index, name in enumerate(story.authors or [story.author], start=1):
        creators.append(f'<dc:creator id="author-{index}">{_xml(name)}</dc:creator>')
        creators.append(
            f'<meta refines="#author-{index}" property="role" scheme="marc:relators">aut</meta>'
        )
    for index, name in enumerate(story.translators, start=1):
        creators.append(f'<dc:contributor id="translator-{index}">{_xml(name)}</dc:contributor>')
        creators.append(
            f'<meta refines="#translator-{index}" property="role" scheme="marc:relators">trl</meta>'
        )
    subjects = []
    for value in [*story.fandoms, *story.directions, *story.pairings, *story.tags]:
        if value:
            subjects.append(f"<dc:subject>{_xml(value)}</dc:subject>")
    series = ""
    if story.series_name:
        series = (
            f'<meta property="belongs-to-collection" id="series">{_xml(story.series_name)}</meta>'
            '<meta refines="#series" property="collection-type">series</meta>'
            f'<meta name="calibre:series" content="{_attr(story.series_name)}"/>'
        )
        if story.series_index:
            series += (
                f'<meta refines="#series" property="group-position">{story.series_index}</meta>'
                f'<meta name="calibre:series_index" content="{story.series_index}"/>'
            )
    cover_meta = ""
    cover_item = ""
    cover_spine = ""
    if story.cover_jpeg:
        cover_meta = '<meta name="cover" content="cover-image"/>'
        cover_item = (
            '<item id="cover-image" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>'
            '<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>'
        )
        cover_spine = '<itemref idref="cover"/>'
    manifest_chapters = []
    spine_chapters = []
    for index in range(1, len(story.chapters) + 1):
        manifest_chapters.append(
            f'<item id="chapter-{index}" href="chapter-{index:03d}.xhtml" media-type="application/xhtml+xml"/>'
        )
        spine_chapters.append(f'<itemref idref="chapter-{index}"/>')
    description = _annotation_text(story, language)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="3.0" xml:lang="{_xml(story.language)}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{_xml(story.url)}</dc:identifier>
    <dc:title>{_xml(story.title)}</dc:title>
    {chr(10).join(creators)}
    <dc:language>{_xml(story.language)}</dc:language>
    <dc:description>{_xml(description)}</dc:description>
    <dc:source>{_xml(story.url)}</dc:source>
    <dc:publisher>ficbook.net</dc:publisher>
    {chr(10).join(subjects)}
    {series}
    {cover_meta}
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="style" href="style.css" media-type="text/css"/>
    {cover_item}
    {chr(10).join(manifest_chapters)}
  </manifest>
  <spine toc="ncx">
    {cover_spine}
    {chr(10).join(spine_chapters)}
  </spine>
</package>
"""


def _nav(story: Story) -> str:
    items = []
    for index, chapter in enumerate(story.chapters, start=1):
        items.append(f'<li><a href="chapter-{index:03d}.xhtml">{_xml(chapter.title)}</a></li>')
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{_xml(story.language)}">
  <head><title>{_xml(story.title)}</title></head>
  <body>
    <nav epub:type="toc" id="toc">
      <h1>{_xml(story.title)}</h1>
      <ol>
        {chr(10).join(items)}
      </ol>
    </nav>
  </body>
</html>
"""


def _ncx(story: Story) -> str:
    points = []
    for index, chapter in enumerate(story.chapters, start=1):
        points.append(
            f"""<navPoint id="chapter-{index}" playOrder="{index}">
      <navLabel><text>{_xml(chapter.title)}</text></navLabel>
      <content src="chapter-{index:03d}.xhtml"/>
    </navPoint>"""
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{_attr(story.url)}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{_xml(story.title)}</text></docTitle>
  <navMap>
    {chr(10).join(points)}
  </navMap>
</ncx>
"""


def _cover_page(story: Story) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{_xml(story.language)}">
  <head>
    <title>{_xml(story.title)}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
  </head>
  <body>
    <p class="cover"><img src="cover.jpg" alt="{_attr(story.title)}"/></p>
  </body>
</html>
"""


def _chapter_page(title: str, paragraphs: list[str]) -> str:
    blocks = [f"<h1>{_xml(title)}</h1>"]
    for paragraph in paragraphs:
        if paragraph.strip():
            blocks.append(_paragraph(paragraph))
    body = "\n".join(blocks)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>{_xml(title)}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
  </head>
  <body>
    {body}
  </body>
</html>
"""


def _paragraph(fragment: str) -> str:
    wrapped = f"<p>{fragment}</p>"
    try:
        ElementTree.fromstring(f"<body>{wrapped}</body>")
    except ElementTree.ParseError:
        text = BeautifulSoup(fragment, "html.parser").get_text()
        wrapped = f"<p>{html.escape(text)}</p>"
    return wrapped


def _annotation_text(story: Story, language: str = "en") -> str:
    parts = [story.description]
    if story.dedication:
        parts.append(f"{t(language, 'dedication')}: " + story.dedication)
    if story.notes:
        parts.append(story.notes)
    return "\n\n".join(part for part in parts if part)


def _xml(value: str) -> str:
    return html.escape(value or "", quote=False)


def _attr(value: str) -> str:
    return html.escape(value or "", quote=True)
