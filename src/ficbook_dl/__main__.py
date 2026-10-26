"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ficbook_dl.client import Client
from ficbook_dl.download import download_story, save_story
from ficbook_dl.errors import FicbookError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ficbook-dl",
        description="Save ficbook.net stories as text files.",
    )
    parser.add_argument(
        "links",
        nargs="+",
        help="Story links or ids, for example https://ficbook.net/readfic/12345",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("stories"),
        help="Directory for the text files (default: stories)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Seconds to wait between requests (default: 1.5)",
    )
    args = parser.parse_args(argv)

    client = Client(delay=args.delay)
    failed = 0
    for link in args.links:
        try:
            story = download_story(client, link, on_chapter=_report_chapter)
            path = save_story(story, args.out)
        except FicbookError as exc:
            failed += 1
            print(f"error: {exc}", file=sys.stderr)
            continue
        except Exception as exc:
            failed += 1
            print(f"error: {link}: {exc}", file=sys.stderr)
            continue
        print(f"saved {path} ({len(story.chapters)} chapters)")
    return 1 if failed else 0


def _report_chapter(index: int, total: int, title: str) -> None:
    print(f"  {index}/{total} {title}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
