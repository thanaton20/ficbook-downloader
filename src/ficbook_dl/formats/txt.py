"""Plain-text export with the book fields in the header."""

from __future__ import annotations

from pathlib import Path

from ficbook_dl.parse import Story


def render(story: Story) -> str:
    lines = [story.title, f"Author: {story.author}", story.url]
    if story.translators:
        lines.append("Translator: " + ", ".join(story.translators))
    if story.series_name:
        number = f" ({story.series_index})" if story.series_index else ""
        lines.append(f"Series: {story.series_name}{number}")
    if story.fandoms:
        lines.append("Fandom: " + ", ".join(story.fandoms))
    if story.directions:
        lines.append("Direction: " + ", ".join(story.directions))
    if story.pairings:
        lines.append("Characters: " + ", ".join(story.pairings))
    if story.rating or story.status:
        lines.append(" · ".join(part for part in (story.rating, story.status) if part))
    if story.tags:
        lines.append("Tags: " + ", ".join(story.tags))
    lines.append("")
    if story.description:
        lines.extend([story.description, ""])
    if story.dedication:
        lines.extend([f"Dedication: {story.dedication}", ""])
    if story.notes:
        lines.extend([f"Notes: {story.notes}", ""])
    for index, chapter in enumerate(story.chapters):
        if index:
            lines.append("")
        lines.extend([chapter.title, "", chapter.body])
    return "\n".join(lines).rstrip() + "\n"


def write_txt(story: Story, path: Path) -> None:
    path.write_text(render(story), encoding="utf-8")
