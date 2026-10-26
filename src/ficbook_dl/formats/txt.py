"""Plain-text export with the book fields in the header."""

from __future__ import annotations

from pathlib import Path

from ficbook_dl.i18n import t
from ficbook_dl.parse import Story


def render(story: Story, language: str = "en") -> str:
    lines = [story.title, f"{t(language, 'author')}: {story.author}", story.url]
    if story.translators:
        lines.append(f"{t(language, 'translator')}: " + ", ".join(story.translators))
    if story.series_name:
        number = f" ({story.series_index})" if story.series_index else ""
        lines.append(f"{t(language, 'series')}: {story.series_name}{number}")
    if story.fandoms:
        lines.append(f"{t(language, 'fandom')}: " + ", ".join(story.fandoms))
    if story.directions:
        lines.append(f"{t(language, 'direction')}: " + ", ".join(story.directions))
    if story.pairings:
        lines.append(f"{t(language, 'characters')}: " + ", ".join(story.pairings))
    if story.rating or story.status:
        lines.append(" · ".join(part for part in (story.rating, story.status) if part))
    if story.tags:
        lines.append(f"{t(language, 'tags')}: " + ", ".join(story.tags))
    lines.append("")
    if story.description:
        lines.extend([story.description, ""])
    if story.dedication:
        lines.extend([f"{t(language, 'dedication')}: {story.dedication}", ""])
    if story.notes:
        lines.extend([f"{t(language, 'notes')}: {story.notes}", ""])
    for index, chapter in enumerate(story.chapters):
        if index:
            lines.append("")
        lines.extend([chapter.title, "", chapter.body])
    return "\n".join(lines).rstrip() + "\n"


def write_txt(story: Story, path: Path, language: str = "en") -> None:
    path.write_text(render(story, language), encoding="utf-8")
