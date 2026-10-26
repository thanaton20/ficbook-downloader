"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ficbook_dl.client import Client
from ficbook_dl.download import FORMATS, download_story, save_story
from ficbook_dl.errors import FicbookError, message
from ficbook_dl.i18n import normalize_language, t


def main(argv: list[str] | None = None) -> int:
    language = _language(argv)
    parser = _parser(language)
    args = parser.parse_args(argv)
    language = normalize_language(args.lang)

    if args.gui:
        from ficbook_dl.gui import main as gui_main

        gui_main()
        return 0
    if not args.links:
        parser.error(t(language, "cli_need_link"))

    formats = _formats(args.format, language)
    client = Client(delay=args.delay)
    failed = 0
    for link in args.links:
        try:
            story = download_story(client, link, on_chapter=_report_chapter, language=language)
            paths = save_story(story, args.out, formats, language)
        except FicbookError as exc:
            failed += 1
            print(t(language, "error_line", message=message(exc, language)), file=sys.stderr)
            continue
        except Exception as exc:
            failed += 1
            print(t(language, "error_line", message=f"{link}: {exc}"), file=sys.stderr)
            continue
        for path in paths:
            print(t(language, "saved_line", path=path, count=len(story.chapters)))
    return 1 if failed else 0


def _language(argv: list[str] | None) -> str:
    preview = argparse.ArgumentParser(add_help=False)
    preview.add_argument("--lang", default=None)
    known, _rest = preview.parse_known_args(argv)
    return normalize_language(known.lang)


def _parser(language: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ficbook-dl", description=t(language, "cli_description"))
    parser.add_argument("links", nargs="*", help=t(language, "cli_links"))
    parser.add_argument("-o", "--out", type=Path, default=Path("stories"), help=t(language, "cli_out"))
    parser.add_argument("--delay", type=float, default=1.5, help=t(language, "cli_delay"))
    parser.add_argument("--format", default="txt,epub,fb2", help=t(language, "cli_format"))
    parser.add_argument("--gui", action="store_true", help=t(language, "cli_gui"))
    parser.add_argument("--lang", default=None, help=t(language, "cli_lang"))
    return parser


def _formats(value: str, language: str) -> list[str]:
    formats = [item.strip().lower() for item in value.split(",") if item.strip()]
    unknown = [item for item in formats if item not in FORMATS]
    if unknown or not formats:
        raise SystemExit(t(language, "cli_bad_format"))
    return formats


def _report_chapter(index: int, total: int, title: str) -> None:
    print(f"  {index}/{total} {title}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
