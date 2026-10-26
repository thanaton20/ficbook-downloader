"""Turn ficbook story HTML into a story object."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from ficbook_dl.errors import AgeCheck, InvalidLink, MissingText, SecurityCheck

_STORY_PATH = re.compile(r"^/readfic/([^/]+)")
_AUTHOR_PATH = re.compile(r"^/authors/[^/]+/?$")
_SECURITY_TITLE = "<title>Проверка безопасности"


@dataclass
class Chapter:
    title: str
    url: str
    body: str | None = None


@dataclass
class Story:
    story_id: str
    title: str
    author: str
    url: str
    description: str = ""
    details: str = ""
    chapters: list[Chapter] = field(default_factory=list)


def canonical_story_url(value: str) -> str:
    """Accept a story id or any /readfic/<id> link and return the story URL."""
    raw = value.strip()
    if not raw:
        raise InvalidLink("Pass a ficbook story link, like https://ficbook.net/readfic/12345.")

    if "://" not in raw and "/" not in raw:
        if not re.fullmatch(r"[0-9A-Za-z-]+", raw):
            raise InvalidLink(f"Not a ficbook story link: {value}")
        return f"https://ficbook.net/readfic/{raw}"

    parsed = urlparse(raw)
    host = parsed.netloc.lower().removeprefix("www.")
    if host != "ficbook.net":
        raise InvalidLink(f"Not a ficbook story link: {value}")
    match = _STORY_PATH.match(parsed.path)
    if not match:
        raise InvalidLink(f"Not a ficbook story link: {value}")
    return f"https://ficbook.net/readfic/{match.group(1)}"


def parse_story(html: str, page_url: str) -> Story:
    _reject_security_page(html)
    soup = BeautifulSoup(html, "html.parser")
    story_url = canonical_story_url(page_url)
    story_id = urlparse(story_url).path.rsplit("/", 1)[-1]
    title = _text(soup.select_one("h1.heading, h1")) or story_id
    authors = _authors(soup)
    chapters = _chapters(soup, story_id)
    if not chapters:
        body = _chapter_text(soup)
        if body:
            heading = _text(soup.select_one("h2")) or title
            chapters = [Chapter(title=heading, url=story_url, body=body)]
        elif soup.select_one("#adultCoverWarning"):
            raise AgeCheck(
                "Ficbook is showing an age check instead of the text for " + story_url
            )
        else:
            raise MissingText(f"No chapters or text found at {story_url}")

    return Story(
        story_id=story_id,
        title=title,
        author=", ".join(authors) or "Unknown",
        url=story_url,
        description=_text(soup.select_one("[itemprop='description']")),
        details=_details(soup),
        chapters=chapters,
    )


def parse_chapter(html: str, chapter_url: str) -> str:
    _reject_security_page(html)
    soup = BeautifulSoup(html, "html.parser")
    body = _chapter_text(soup)
    if body:
        return body
    if soup.select_one("#adultCoverWarning"):
        raise AgeCheck(
            "Ficbook is showing an age check instead of the text for " + chapter_url
        )
    raise MissingText(f"No chapter text at {chapter_url}")


def render(story: Story) -> str:
    lines = [story.title, story.author, story.url]
    if story.details:
        lines.append(story.details)
    lines.append("")
    if story.description:
        lines.extend([story.description, ""])
    for index, chapter in enumerate(story.chapters):
        if index:
            lines.append("")
        lines.extend([chapter.title, "", chapter.body or ""])
    return "\n".join(lines).rstrip() + "\n"


def filename(story: Story) -> str:
    raw = f"{story.title} — {story.author}"
    cleaned = re.sub(r'[\\/:*?"<>|]', " ", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(".")
    return f"{(cleaned[:120] or story.story_id)}.txt"


def _reject_security_page(html: str) -> None:
    if _SECURITY_TITLE in html[:2000]:
        raise SecurityCheck(
            "Ficbook returned a security check instead of the story page."
        )


def _chapters(soup: BeautifulSoup, story_id: str) -> list[Chapter]:
    chapters: list[Chapter] = []
    seen: set[str] = set()
    for anchor in soup.select("ul.list-of-fanfic-parts a.part-link"):
        href = anchor.get("href") or ""
        url = _without_fragment(urljoin("https://ficbook.net", href))
        path = urlparse(url).path
        if not path.startswith(f"/readfic/{story_id}/"):
            continue
        if url in seen:
            continue
        seen.add(url)
        title = _text(anchor.select_one("h3")) or _text(anchor) or f"Part {len(chapters) + 1}"
        chapters.append(Chapter(title=title, url=url))
    return chapters


def _authors(soup: BeautifulSoup) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select("a.word-break[href*='/authors/'], a[itemprop='author']"):
        href = urlparse(anchor.get("href") or "").path
        if not _AUTHOR_PATH.match(href) or href in seen:
            continue
        name = _text(anchor)
        if not name:
            continue
        seen.add(href)
        names.append(name)
    return names


def _details(soup: BeautifulSoup) -> str:
    rating = _text(soup.select_one("[class*='ds-label-rating-']"))
    status = _text(soup.select_one("[class*='ds-label-status-']"))
    return " · ".join(part for part in (rating, status) if part)


def _chapter_text(soup: BeautifulSoup) -> str | None:
    node = (
        soup.select_one("#content")
        or soup.select_one(".part_text")
        or soup.select_one("[itemprop='articleBody']")
    )
    if node is None:
        return None
    for bad in node.select("script, style"):
        bad.decompose()
    text = node.get_text().replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text or None


def _text(node) -> str:
    if node is None:
        return ""
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def _without_fragment(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment=""))
