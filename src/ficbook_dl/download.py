"""Fetch a story and write txt, EPUB, and FB2 files."""

from __future__ import annotations

from pathlib import Path

from ficbook_dl.client import Client
from ficbook_dl.errors import Cancelled, described
from ficbook_dl.formats import WRITERS
from ficbook_dl.formats.cover import to_jpeg
from ficbook_dl.parse import (
    Story,
    canonical_story_url,
    file_stem,
    parse_chapter_content,
    parse_story,
    series_index,
)

FORMATS = ("txt", "epub", "fb2")


def download_story(client: Client, link: str, on_chapter=None, stop=None, language: str = "en") -> Story:
    if stop and stop():
        raise described(Cancelled, "stopped")
    story_url = canonical_story_url(link)
    story = parse_story(client.get(story_url), story_url, language)
    if story.series_url and story.series_index is None:
        try:
            story.series_index = series_index(client.get(story.series_url), story.story_id)
        except Exception:
            story.series_index = None
    if story.cover_url and not story.cover_jpeg:
        try:
            story.cover_jpeg = to_jpeg(client.get_bytes(story.cover_url))
        except Exception:
            story.cover_jpeg = None
    total = len(story.chapters)
    for index, chapter in enumerate(story.chapters, start=1):
        if stop and stop():
            raise described(Cancelled, "stopped")
        if on_chapter:
            on_chapter(index, total, chapter.title)
        if chapter.paragraphs:
            continue
        loaded = parse_chapter_content(client.get(chapter.url), chapter.url, language)
        chapter.paragraphs = loaded.paragraphs
    return story


def save_story(
    story: Story,
    directory: Path,
    formats: tuple[str, ...] | list[str] = FORMATS,
    language: str = "en",
) -> list[Path]:
    unknown = [fmt for fmt in formats if fmt not in WRITERS]
    if unknown:
        raise ValueError("Unknown format: " + ", ".join(unknown))
    directory.mkdir(parents=True, exist_ok=True)
    stem = _stem_for(story, directory)
    paths: list[Path] = []
    for fmt in formats:
        path = directory / f"{stem}.{fmt}"
        WRITERS[fmt](story, path, language)
        paths.append(path)
    return paths


def _stem_for(story: Story, directory: Path) -> str:
    stem = file_stem(story)
    existing = directory / f"{stem}.txt"
    if not existing.exists():
        return stem
    head = existing.read_text(encoding="utf-8", errors="ignore")[:800]
    if story.url in head:
        return stem
    return f"{stem} [{story.story_id}]"
