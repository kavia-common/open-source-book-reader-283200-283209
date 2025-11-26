from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.utils.http_client import HttpClient

# Simple IA endpoints
SEARCH_URL = "https://archive.org/advancedsearch.php"
DETAILS_URL = "https://archive.org/metadata/{identifier}"

class InternetArchiveService:
    """
    Minimal Internet Archive integration using metadata and advancedsearch.
    """

    def __init__(self) -> None:
        self.http = HttpClient()

    # PUBLIC_INTERFACE
    def search(self, q: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        Search Internet Archive texts collection.
        """
        params = {
            "q": q,
            "fl[]": ["identifier", "title", "creator", "mediatype"],
            "rows": page_size,
            "page": page,
            "output": "json",
        }
        data = self.http.get_json(SEARCH_URL, params=params)
        response = data.get("response", {})
        docs = response.get("docs", [])
        items: List[Dict[str, Any]] = []
        for d in docs:
            if d.get("mediatype") not in ["texts", "image", "data", "movies", "audio", "etree", "software"]:
                continue
            identifier = str(d.get("identifier"))
            title = d.get("title", "")
            creators = d.get("creator")
            if isinstance(creators, list):
                authors = [c for c in creators]
            elif isinstance(creators, str):
                authors = [creators]
            else:
                authors = []
            items.append({
                "source": "archive",
                "book_id": identifier,
                "title": title,
                "authors": authors,
                "cover_url": None,
                "description": None,
            })
        total = response.get("numFound", 0)
        return {"total": total, "items": items}

    # PUBLIC_INTERFACE
    def get_book_details(self, book_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a single IA item.
        """
        url = DETAILS_URL.format(identifier=book_id)
        data = self.http.get_json(url)
        if not data or "metadata" not in data:
            return None
        md = data.get("metadata", {})
        title = md.get("title", "")
        creators = md.get("creator")
        if isinstance(creators, list):
            authors = [c for c in creators]
        elif isinstance(creators, str):
            authors = [creators]
        else:
            authors = []
        # Simple download options guess (many IA items provide multiple files)
        dl_opts = ["text", "html", "epub"]
        return {
            "source": "archive",
            "book_id": book_id,
            "title": title,
            "authors": authors,
            "cover_url": None,
            "description": md.get("description"),
            "download_options": dl_opts,
        }

    # PUBLIC_INTERFACE
    def get_download(self, book_id: str, preferred_format: Optional[str] = None) -> Dict[str, Any]:
        """
        Try to pick a reasonable file to download from IA item's files list.
        """
        url = DETAILS_URL.format(identifier=book_id)
        data = self.http.get_json(url)
        files = data.get("files", []) if isinstance(data.get("files"), list) else []
        def pick(exts: List[str]) -> Optional[Dict[str, Any]]:
            for f in files:
                name = f.get("name", "")
                for ext in exts:
                    if name.lower().endswith(ext):
                        return {"url": f"https://archive.org/download/{book_id}/{name}", "type": "html" if ext in [".htm", ".html"] else ("text" if ext in [".txt"] else ("epub" if ext in [".epub"] else "bin"))}
            return None

        order = []
        if preferred_format:
            pf = preferred_format.lower()
            if pf == "html":
                order = [[".html", ".htm"], [".txt"], [".epub"]]
            elif pf == "text":
                order = [[".txt"], [".html", ".htm"], [".epub"]]
            elif pf == "epub":
                order = [[".epub"], [".html", ".htm"], [".txt"]]
        if not order:
            order = [[".html", ".htm"], [".txt"], [".epub"]]
        for group in order:
            cand = pick(group)
            if cand:
                return cand
        raise ValueError("No suitable file found for download")
