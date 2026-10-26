"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ficbook_dl.client import Client
from ficbook_dl.download import FORMATS, download_story, save_story
from ficbook_dl.errors import FicbookError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ficbook-dl",
        description="Save ficbook.net stories as txt, EPUB, and FB2 files.",
    )
    parser.add_argument(
        "links",
        nargs="*",
        help="Story links or ids, for example https://ficbook.net/readfic/12345",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("stories"),
        help="Directory for the files (default: stories)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Seconds to wait between requests (default: 1.5)",
    )
    parser.add_argument(
        "--format",
        default="txt,epub,fb2",
        help="Comma-separated formats: txt, epub, fb2 (default: all three)",
    )
    parser.add_argument("--gui", action="store_true", help="Open the Mac and Windows window")
    args = parser.parse_args(argv)

    if args.gui:
        from ficbook_dl.gui import main as gui_main

        gui_main()
        return 0
    if not args.links:
        parser.error("pass at least one story link, or use --gui")

    formats = _formats(args.format)
    client = Client(delay=args.delay)
    failed = 0
    for link in args.links:
        try:
            story = download_story(client, link, on_chapter=_report_chapter)
            paths = save_story(story, args.out, formats)
        except FicbookError as exc:
            failed += 1
            print(f"error: {exc}", file=sys.stderr)
            continue
        except Exception as exc:
            failed += 1
            print(f"error: {link}: {exc}", file=sys.stderr)
            continue
        for path in paths:
            print(f"saved {path} ({len(story.chapters)} chapters)")
    return 1 if failed else 0


def _formats(value: str) -> list[str]:
    formats = [item.strip().lower() for item in value.split(",") if item.strip()]
    unknown = [item for item in formats if item not in FORMATS]
    if unknown or not formats:
        raise SystemExit("Formats are txt, epub, and fb2.")
    return formats


def _report_chapter(index: int, total: int, title: str) -> None:
    print(f"  {index}/{total} {title}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
