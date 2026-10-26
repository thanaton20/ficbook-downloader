"""Fetch a story and write it to a text file."""

from __future__ import annotations

from pathlib import Path

from ficbook_dl.client import Client
from ficbook_dl.parse import Story, canonical_story_url, filename, parse_chapter, parse_story, render


def download_story(client: Client, link: str, on_chapter=None) -> Story:
    story_url = canonical_story_url(link)
    story = parse_story(client.get(story_url), story_url)
    total = len(story.chapters)
    for index, chapter in enumerate(story.chapters, start=1):
        if on_chapter:
            on_chapter(index, total, chapter.title)
        if chapter.body:
            continue
        chapter.body = parse_chapter(client.get(chapter.url), chapter.url)
    return story


def save_story(story: Story, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename(story)
    if path.exists() and story.url not in path.read_text(encoding="utf-8")[:500]:
        path = directory / f"{path.stem} [{story.story_id}].txt"
    path.write_text(render(story), encoding="utf-8")
    return path
