"""Errors a caller can show as-is."""

from __future__ import annotations


class FicbookError(Exception):
    """Base error for a story that could not be saved."""

    code = ""
    params: dict

    def __init__(self, message: str = "", **params) -> None:
        self.params = params
        super().__init__(message)


def described(cls: type[FicbookError], code: str, **params) -> FicbookError:
    from ficbook_dl.i18n import t

    exc = cls(t("en", code, **params), **params)
    exc.code = code
    return exc


def message(exc: BaseException, language: str) -> str:
    from ficbook_dl.i18n import t

    code = getattr(exc, "code", "")
    if code:
        return t(language, code, **getattr(exc, "params", {}))
    return str(exc)


class InvalidLink(FicbookError):
    """The argument is not a ficbook story link or id."""


class SecurityCheck(FicbookError):
    """The site returned its bot check instead of a story page."""


class AgeCheck(FicbookError):
    """The story page is an age confirmation instead of the text."""


class MissingText(FicbookError):
    """A chapter page did not include readable text."""


class Cancelled(FicbookError):
    """The user stopped the download."""
