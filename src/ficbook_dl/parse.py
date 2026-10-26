"""Turn ficbook story HTML into a story object."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import escape
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup, NavigableString

from ficbook_dl.errors import AgeCheck, InvalidLink, MissingText, SecurityCheck, described
from ficbook_dl.i18n import t

_STORY_PATH = re.compile(r"^/readfic/([^/]+)")
_AUTHOR_PATH = re.compile(r"^/authors/[^/]+/?$")
_SECURITY_TITLE = "<title>Проверка безопасности"
_UI_LINES = {"Спойлеры", "Показать", "Скрыть", "Спойлер"}


@dataclass
class Chapter:
    title: str
    url: str
    paragraphs: list[str] = field(default_factory=list)

    @property
    def body(self) -> str:
        chunks = []
        for paragraph in self.paragraphs:
            text = BeautifulSoup(paragraph, "html.parser").get_text().strip()
            if text:
                chunks.append(text)
        return "\n\n".join(chunks)


@dataclass
class Story:
    story_id: str
    title: str
    author: str
    url: str
    description: str = ""
    details: str = ""
    chapters: list[Chapter] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    translators: list[str] = field(default_factory=list)
    series_name: str = ""
    series_index: int | None = None
    series_url: str = ""
    cover_url: str = ""
    cover_jpeg: bytes | None = None
    fandoms: list[str] = field(default_factory=list)
    pairings: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    directions: list[str] = field(default_factory=list)
    rating: str = ""
    status: str = ""
    dedication: str = ""
    notes: str = ""
    language: str = "ru"


def canonical_story_url(value: str) -> str:
    """Accept a story id or any /readfic/<id> link and return the story URL."""
    raw = value.strip()
    if not raw:
        raise described(InvalidLink, "empty_link")

    if "://" not in raw and "/" not in raw:
        if not re.fullmatch(r"[0-9A-Za-z-]+", raw):
            raise described(InvalidLink, "not_ficbook", value=value)
        return f"https://ficbook.net/readfic/{raw}"

    parsed = urlparse(raw)
    host = parsed.netloc.lower().removeprefix("www.")
    if host != "ficbook.net":
        raise described(InvalidLink, "not_ficbook", value=value)
    match = _STORY_PATH.match(parsed.path)
    if not match:
        raise described(InvalidLink, "not_ficbook", value=value)
    return f"https://ficbook.net/readfic/{match.group(1)}"


def parse_story(html: str, page_url: str, language: str = "en") -> Story:
    _reject_security_page(html)
    soup = BeautifulSoup(html, "html.parser")
    story_url = canonical_story_url(page_url)
    story_id = urlparse(story_url).path.rsplit("/", 1)[-1]
    header = soup.select_one("section.chapter-info") or soup.select_one(".fanfic-hat") or soup
    hat = soup.select_one(".fanfic-hat")
    info = None
    for root in (header, hat, soup):
        if root is None:
            continue
        info = root.select_one("div.description.word-break")
        if info is not None:
            break
    info = info or header
    title = _text(header.select_one("h1.heading, h1")) or _text(soup.select_one("h1")) or story_id
    posted_by = _authors(header) or _authors(hat or soup)
    originals = _split_names(_field_text(info, "Автор оригинала:"))
    if originals:
        authors = originals
        translators = [name for name in posted_by if name not in originals]
    else:
        authors = posted_by
        translators = []

    chapters = _chapters(soup, story_id)
    if not chapters:
        paragraphs = _chapter_paragraphs(soup, language)
        if paragraphs:
            heading = _text(header.select_one("h2") or soup.select_one("h2")) or title
            chapters = [Chapter(title=heading, url=story_url, paragraphs=paragraphs)]
        elif soup.select_one("#adultCoverWarning"):
            raise described(AgeCheck, "age_check", url=story_url)
        else:
            raise described(MissingText, "missing_story", url=story_url)

    rating = _text(header.select_one("[class*='ds-label-rating-']"))
    status = _text(header.select_one("[class*='ds-label-status-']"))
    directions = _unique(
        _text(node)
        for node in header.select("[class*='direction']")
        if _text(node) and node.find_parent(class_=re.compile(r"promo|fanfic-inline")) is None
    )
    series_name, series_url = _series(info)
    return Story(
        story_id=story_id,
        title=title,
        author=", ".join(authors) or "Unknown",
        url=story_url,
        description=_field_text(info, "Описание:"),
        details=" · ".join(part for part in (rating, status) if part),
        chapters=chapters,
        authors=authors,
        translators=translators,
        series_name=series_name,
        series_url=series_url,
        cover_url=_cover_url(soup),
        fandoms=_field_links(info, "Фэндом:"),
        pairings=_field_links(info, "Пэйринг и персонажи:"),
        tags=_field_links(info, "Метки:"),
        directions=directions,
        rating=rating,
        status=status,
        dedication=_field_text(info, "Посвящение:"),
        notes=_field_text(info, "Примечания:"),
    )


def parse_chapter(html: str, chapter_url: str) -> str:
    chapter = parse_chapter_content(html, chapter_url)
    return chapter.body


def parse_chapter_content(html: str, chapter_url: str, language: str = "en") -> Chapter:
    _reject_security_page(html)
    soup = BeautifulSoup(html, "html.parser")
    paragraphs = _chapter_paragraphs(soup, language)
    if paragraphs:
        title = _text(soup.select_one("h2")) or t(language, "chapter")
        return Chapter(title=title, url=chapter_url, paragraphs=paragraphs)
    if soup.select_one("#adultCoverWarning"):
        raise described(AgeCheck, "age_check", url=chapter_url)
    raise described(MissingText, "missing_chapter", url=chapter_url)


def series_index(html: str, story_id: str) -> int | None:
    """Return the 1-based position of a story on a ficbook series page."""
    soup = BeautifulSoup(html, "html.parser")
    seen: list[str] = []
    for anchor in soup.select("a.visit-link[href*='/readfic/']"):
        path = urlparse(urljoin("https://ficbook.net", anchor.get("href") or "")).path.rstrip("/")
        match = re.fullmatch(r"/readfic/([^/]+)", path)
        if not match:
            continue
        found = match.group(1)
        if found not in seen:
            seen.append(found)
    if story_id not in seen:
        return None
    return seen.index(story_id) + 1


def file_stem(story: Story) -> str:
    raw = f"{story.title} — {story.author}"
    cleaned = re.sub(r'[\\/:*?"<>|]', " ", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(".")
    return cleaned[:120] or story.story_id


def filename(story: Story) -> str:
    return f"{file_stem(story)}.txt"


def _reject_security_page(html: str) -> None:
    if _SECURITY_TITLE in html[:2000]:
        raise described(SecurityCheck, "security_check")


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


def _authors(root) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for anchor in root.select("a.word-break[href*='/authors/'], a[itemprop='author']"):
        href = urlparse(anchor.get("href") or "").path
        if not _AUTHOR_PATH.match(href) or href in seen:
            continue
        name = _text(anchor)
        if not name:
            continue
        seen.add(href)
        names.append(name)
    return names


def _series(root) -> tuple[str, str]:
    sibling = _field_node(root, "Серия:")
    if sibling is None:
        return "", ""
    link = sibling.find("a", href=True)
    if link is None:
        return _text(sibling), ""
    return _text(link), urljoin("https://ficbook.net", link["href"])


def _cover_url(soup: BeautifulSoup) -> str:
    for meta in soup.select("meta[property='og:image']"):
        content = (meta.get("content") or "").strip()
        if "/fanfic-covers/" in content:
            return content
    return ""


def _field_node(root, label: str):
    for strong in root.find_all("strong"):
        if _text(strong).startswith(label):
            return strong.find_next_sibling("div")
    return None


def _field_text(root, label: str) -> str:
    node = _field_node(root, label)
    if node is None:
        return ""
    lines = []
    for line in node.get_text("\n", strip=True).splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        if cleaned and cleaned not in _UI_LINES:
            lines.append(cleaned)
    return "\n".join(lines)


def _field_links(root, label: str) -> list[str]:
    node = _field_node(root, label)
    if node is None:
        return []
    names = [_text(anchor) for anchor in node.find_all("a") if _text(anchor)]
    return names or ([_field_text(root, label)] if _field_text(root, label) else [])


def _chapter_paragraphs(soup: BeautifulSoup, language: str = "en") -> list[str]:
    node = (
        soup.select_one("#content")
        or soup.select_one(".part_text")
        or soup.select_one("[itemprop='articleBody']")
    )
    paragraphs: list[str] = []
    note_label = f"<i>{escape(t(language, 'notes'))}</i>"
    head = _note_lines(soup.select_one("div.part-comment-top"))
    if head:
        paragraphs.append(note_label)
        paragraphs.extend(head)
    if node is not None:
        paragraphs.extend(_html_paragraphs(node))
    foot = _note_lines(soup.select_one("div.part-comment-bottom"))
    if foot:
        paragraphs.append(note_label)
        paragraphs.extend(foot)
    return paragraphs


def _note_lines(node) -> list[str]:
    if node is None:
        return []
    return [escape(line) for line in _plain_lines(node.get_text("\n"))]


def _html_paragraphs(node) -> list[str]:
    markup = _inline_markup(node)
    return [line.strip() for line in markup.split("\n") if line.strip()]


def _inline_markup(node) -> str:
    chunks: list[str] = []

    def walk(current) -> None:
        for child in getattr(current, "children", []):
            if isinstance(child, NavigableString):
                chunks.append(escape(str(child)).replace("\r\n", "\n").replace("\r", "\n"))
                continue
            name = child.name
            if name in ("script", "style"):
                continue
            if name == "br":
                chunks.append("\n")
                continue
            if name in ("i", "em", "b", "strong"):
                tag = "i" if name in ("i", "em") else "b"
                inner = _inline_markup(child)
                if inner.strip():
                    chunks.append(_balanced_tag(tag, inner))
                continue
            if name in ("p", "div", "li", "blockquote"):
                if chunks and not chunks[-1].endswith("\n"):
                    chunks.append("\n")
                walk(child)
                chunks.append("\n")
                continue
            walk(child)

    walk(node)
    return "".join(chunks)


def _balanced_tag(tag: str, inner: str) -> str:
    """Keep italics and bold inside a single paragraph.

    A letter on ficbook is often one <i> with a newline between sentences.
    Splitting that into paragraphs must close the tag on each line, or the
    EPUB page is not valid XML.
    """
    lines = inner.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    rendered = []
    for line in lines:
        stripped = line.strip()
        rendered.append(f"<{tag}>{stripped}</{tag}>" if stripped else "")
    return "\n".join(rendered)


def _plain_lines(text: str) -> list[str]:
    lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        cleaned = re.sub(r"\s+", " ", line).strip()
        if cleaned and cleaned not in _UI_LINES:
            lines.append(cleaned)
    return lines


def _split_names(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _unique(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _text(node) -> str:
    if node is None:
        return ""
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def _without_fragment(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment=""))


@dataclass
class AuthorWork:
    story_id: str
    title: str
    url: str


def canonical_author_works_url(value: str) -> str:
    """Accept an author profile link and return the works list URL."""
    raw = value.strip()
    if not raw:
        raise described(InvalidLink, "need_author")
    if "://" not in raw and "/" not in raw and re.fullmatch(r"[0-9A-Za-z-]+", raw):
        return f"https://ficbook.net/authors/{raw}/profile/works"

    parsed = urlparse(raw if "://" in raw else "https://ficbook.net/" + raw.lstrip("/"))
    host = parsed.netloc.lower().removeprefix("www.")
    if host != "ficbook.net":
        raise described(InvalidLink, "not_author", value=value)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] != "authors":
        raise described(InvalidLink, "not_author", value=value)
    return f"https://ficbook.net/authors/{parts[1]}/profile/works"


def parse_author_works(html: str, page_url: str) -> tuple[str, list[AuthorWork], str | None]:
    """Return the author name, the books on this page, and the next page URL."""
    _reject_security_page(html)
    soup = BeautifulSoup(html, "html.parser")
    name = _text(soup.select_one("h1")) or _author_name_from_title(soup)
    works: list[AuthorWork] = []
    seen: set[str] = set()
    for anchor in soup.select("a.visit-link[href*='/readfic/']"):
        classes = set(anchor.get("class") or [])
        if "js-promo-fanfic" in classes or "fanfic-promo-item" in classes:
            continue
        path = urlparse(urljoin("https://ficbook.net", anchor.get("href") or "")).path.rstrip("/")
        match = re.fullmatch(r"/readfic/([^/]+)", path)
        if not match or match.group(1) in seen:
            continue
        seen.add(match.group(1))
        title = _text(anchor) or match.group(1)
        works.append(
            AuthorWork(
                story_id=match.group(1),
                title=title,
                url=f"https://ficbook.net/readfic/{match.group(1)}",
            )
        )
    return name, works, _next_works_page(soup, page_url)


def _author_name_from_title(soup: BeautifulSoup) -> str:
    title = _text(soup.find("title"))
    return re.split(r"\s+[–—-]\s+", title, maxsplit=1)[0].strip()


def _next_works_page(soup: BeautifulSoup, page_url: str) -> str | None:
    parsed = urlparse(page_url)
    current = int(parse_qs(parsed.query).get("p", ["1"])[0] or "1")
    pages: set[int] = set()
    for anchor in soup.select("a[href*='/profile/works']"):
        query = parse_qs(urlparse(urljoin("https://ficbook.net", anchor.get("href") or "")).query)
        if "p" in query and query["p"][0].isdigit():
            pages.add(int(query["p"][0]))
    nxt = current + 1
    if nxt not in pages:
        return None
    query = parse_qs(parsed.query)
    query["p"] = [str(nxt)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True), fragment=""))
