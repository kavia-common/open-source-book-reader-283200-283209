from __future__ import annotations

import httpx
from typing import Any, Dict, Optional

DEFAULT_TIMEOUT = 20.0

class HttpClient:
    """
    Thin wrapper around httpx for simple GET requests with sensible defaults.
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout

    # PUBLIC_INTERFACE
    def get_json(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Perform a GET request and parse JSON response."""
        with httpx.Client(timeout=self._timeout, headers=headers) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            return r.json()

    # PUBLIC_INTERFACE
    def get_bytes(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> bytes:
        """Perform a GET request and return raw bytes."""
        with httpx.Client(timeout=self._timeout, headers=headers) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            return r.content
