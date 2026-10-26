"""FictionBook 2.0 with author, series, cover, and one section per chapter."""

from __future__ import annotations

import base64
import html
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString

from ficbook_dl import __version__
from ficbook_dl.parse import Story


def write_fb2(story: Story, path: Path) -> None:
    path.write_text(build_fb2(story), encoding="utf-8")


def build_fb2(story: Story) -> str:
    authors = "\n".join(_person("author", name) for name in (story.authors or [story.author]))
    translators = "\n".join(_person("translator", name) for name in story.translators)
    sequence = ""
    if story.series_name:
        number = f' number="{story.series_index}"' if story.series_index else ""
        sequence = f'<sequence name="{_attr(story.series_name)}"{number}/>'
    keywords = ", ".join(
        value
        for value in [
            *story.fandoms,
            *story.directions,
            *story.pairings,
            *story.tags,
            story.rating,
            story.status,
        ]
        if value
    )
    annotation = _annotation(story)
    cover = ""
    binary = ""
    if story.cover_jpeg:
        cover = '<coverpage><image l:href="#cover.jpg"/></coverpage>'
        encoded = base64.b64encode(story.cover_jpeg).decode("ascii")
        wrapped = "\n".join(encoded[i : i + 76] for i in range(0, len(encoded), 76))
        binary = f'<binary id="cover.jpg" content-type="image/jpeg">{wrapped}</binary>'
    sections = "\n".join(_section(chapter.title, chapter.paragraphs) for chapter in story.chapters)
    today = date.today().isoformat()
    return f"""<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">
  <description>
    <title-info>
      <genre>fanfiction</genre>
      {authors}
      {translators}
      <book-title>{_xml(story.title)}</book-title>
      {annotation}
      {cover}
      {sequence}
      <keywords>{_xml(keywords)}</keywords>
      <lang>{_xml(story.language)}</lang>
      <src-lang>{_xml(story.language)}</src-lang>
    </title-info>
    <document-info>
      <author><nickname>ficbook-downloader</nickname></author>
      <program-used>ficbook-downloader {__version__}</program-used>
      <date value="{today}">{today}</date>
      <src-url>{_xml(story.url)}</src-url>
      <id>{_xml(story.url)}</id>
    </document-info>
    <publish-info>
      <book-name>{_xml(story.title)}</book-name>
      <publisher>ficbook.net</publisher>
    </publish-info>
  </description>
  <body>
    {sections}
  </body>
  {binary}
</FictionBook>
"""


def _annotation(story: Story) -> str:
    paragraphs = _plain_paragraphs(story.description)
    if story.dedication:
        paragraphs.append("Посвящение: " + story.dedication)
    paragraphs.extend(_plain_paragraphs(story.notes))
    if not paragraphs:
        return ""
    inner = "\n".join(f"<p>{_xml(paragraph)}</p>" for paragraph in paragraphs)
    return f"<annotation>\n{inner}\n</annotation>"


def _section(title: str, paragraphs: list[str]) -> str:
    body = "\n".join(f"<p>{_fb2_inline(paragraph)}</p>" for paragraph in paragraphs if paragraph.strip())
    return f"""<section>
      <title><p>{_xml(title)}</p></title>
      {body}
    </section>"""


def _person(tag: str, name: str) -> str:
    parts = name.split()
    if len(parts) == 2 and all(_name_token(part) for part in parts):
        return (
            f"<{tag}><first-name>{_xml(parts[0])}</first-name>"
            f"<last-name>{_xml(parts[1])}</last-name></{tag}>"
        )
    return f"<{tag}><nickname>{_xml(name)}</nickname></{tag}>"


def _name_token(value: str) -> bool:
    return all(character.isalpha() or character in "-'" for character in value)


def _plain_paragraphs(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _fb2_inline(fragment: str) -> str:
    soup = BeautifulSoup(f"<span>{fragment}</span>", "html.parser")

    def walk(node) -> str:
        chunks: list[str] = []
        for child in node.children:
            if isinstance(child, NavigableString):
                chunks.append(_xml(str(child)))
                continue
            if child.name in ("i", "em"):
                chunks.append(f"<emphasis>{walk(child)}</emphasis>")
            elif child.name in ("b", "strong"):
                chunks.append(f"<strong>{walk(child)}</strong>")
            else:
                chunks.append(walk(child))
        return "".join(chunks)

    return walk(soup.span).strip()


def _xml(value: str) -> str:
    return html.escape(value or "", quote=False)


def _attr(value: str) -> str:
    return html.escape(value or "", quote=True)
