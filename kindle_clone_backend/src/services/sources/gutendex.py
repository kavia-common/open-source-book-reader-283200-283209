from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.utils.http_client import HttpClient

GUTENDEX_BASE = "https://gutendex.com/books/"

class GutendexService:
    """
    Service for interacting with Gutendex (Project Gutenberg).
    """

    def __init__(self) -> None:
        self.http = HttpClient()

    # PUBLIC_INTERFACE
    def search(self, q: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        Search Gutendex books.
        """
        params = {"search": q, "page": page}
        data = self.http.get_json(GUTENDEX_BASE, params=params)
        items: List[Dict[str, Any]] = []
        for b in data.get("results", []):
            book_id = str(b.get("id"))
            title = b.get("title", "")
            authors = [a.get("name") for a in b.get("authors", []) if a.get("name")]
            cover = (b.get("formats", {}) or {}).get("image/jpeg")
            items.append({
                "source": "gutenberg",
                "book_id": book_id,
                "title": title,
                "authors": authors,
                "cover_url": cover,
                "description": None,
            })
        total = data.get("count", 0)
        return {"total": total, "items": items}

    # PUBLIC_INTERFACE
    def get_book_details(self, book_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a single Gutendex book.
        """
        url = f"{GUTENDEX_BASE}{book_id}"
        b = self.http.get_json(url)
        if not b or "id" not in b:
            return None
        title = b.get("title", "")
        authors = [a.get("name") for a in b.get("authors", []) if a.get("name")]
        cover = (b.get("formats", {}) or {}).get("image/jpeg")
        available_formats = list((b.get("formats") or {}).keys())
        # normalize into 'text','html','epub' if present
        dl_opts: List[str] = []
        if any("text/plain" in f for f in available_formats):
            dl_opts.append("text")
        if any("text/html" in f for f in available_formats):
            dl_opts.append("html")
        if any("application/epub" in f for f in available_formats):
            dl_opts.append("epub")
        return {
            "source": "gutenberg",
            "book_id": str(b.get("id")),
            "title": title,
            "authors": authors,
            "cover_url": cover,
            "description": None,
            "download_options": dl_opts,
        }

    # PUBLIC_INTERFACE
    def get_download(self, book_id: str, preferred_format: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a direct download URL and inferred content type for a book.
        """
        url = f"{GUTENDEX_BASE}{book_id}"
        b = self.http.get_json(url)
        formats: Dict[str, str] = b.get("formats", {}) if isinstance(b.get("formats", {}), dict) else {}
        # Choose format
        order = []
        if preferred_format:
            pf = preferred_format.lower()
            if pf == "html":
                order = ["text/html; charset=utf-8", "text/html"]
            elif pf == "text":
                order = ["text/plain; charset=utf-8", "text/plain"]
            elif pf == "epub":
                order = ["application/epub+zip"]
        if not order:
            order = ["text/html; charset=utf-8", "text/html", "text/plain; charset=utf-8", "text/plain"]
        for key in order:
            if key in formats and formats[key]:
                return {"url": formats[key], "type": "html" if "html" in key else ("text" if "text/plain" in key else "epub")}
        # fallback any
        for k, v in formats.items():
            if v:
                t = "html" if "html" in k else ("text" if "text/plain" in k else "epub" if "epub" in k else "bin")
                return {"url": v, "type": t}
        raise ValueError("No downloadable format found")
