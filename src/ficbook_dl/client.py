"""HTTP client for public ficbook story pages."""

from __future__ import annotations

import time

from curl_cffi import requests

from ficbook_dl.errors import SecurityCheck

_SECURITY_TITLE = "<title>Проверка безопасности"


class Client:
    """Fetch story HTML.

    Ficbook answers a plain Python HTTP client with a security check.
    curl_cffi presents a normal browser TLS fingerprint, so the same public
    pages come back as HTML. This does not launch a browser.
    """

    def __init__(self, delay: float = 1.5) -> None:
        if delay < 0:
            raise ValueError("delay must be zero or greater")
        self.delay = delay
        self._last = 0.0
        self._session = requests.Session(impersonate="chrome")

    def get(self, url: str) -> str:
        self._pause()
        response = self._session.get(url, timeout=40)
        text = response.text
        if response.status_code == 403 or _SECURITY_TITLE in text[:2000]:
            raise SecurityCheck(
                "Ficbook returned a security check instead of the story page."
            )
        response.raise_for_status()
        return text

    def get_bytes(self, url: str) -> bytes:
        self._pause()
        response = self._session.get(url, timeout=40)
        response.raise_for_status()
        return response.content

    def _pause(self) -> None:
        if self._last:
            remaining = self.delay - (time.monotonic() - self._last)
            if remaining > 0:
                time.sleep(remaining)
        self._last = time.monotonic()
