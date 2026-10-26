"""Errors a caller can show as-is."""


class FicbookError(Exception):
    """Base error for a story that could not be saved."""


class InvalidLink(FicbookError):
    """The argument is not a ficbook story link or id."""


class SecurityCheck(FicbookError):
    """The site returned its bot check instead of a story page."""


class AgeCheck(FicbookError):
    """The story page is an age confirmation instead of the text."""


class MissingText(FicbookError):
    """A chapter page did not include readable text."""
