from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.core.config import get_config
from src.utils.text import basic_text_cleanup

class Normalizer:
    """
    Convert raw text/html content into a simple set of chapter HTML files and a manifest.json
    stored under CONTENT_ROOT/normalized/{source}/{book_id}/
    """

    def __init__(self) -> None:
        cfg = get_config()
        self.root = Path(cfg.content_root) / "normalized"
        self.root.mkdir(parents=True, exist_ok=True)

    # PUBLIC_INTERFACE
    def normalize(self, source: str, book_id: str, kind: str, src_path: Path) -> None:
        """
        Normalize the downloaded content into chapters.
        For 'text' and 'html' kinds, produce naive chapters every ~2000 characters as separate HTML files.
        """
        book_dir = self.root / source / book_id
        chapters_dir = book_dir / "chapters"
        chapters_dir.mkdir(parents=True, exist_ok=True)

        raw = src_path.read_text(encoding="utf-8", errors="ignore")
        if kind == "text":
            content = f"<pre>{basic_text_cleanup(raw)}</pre>"
        elif kind == "html":
            # Use content directly, but ensure minimal cleanup
            content = raw.strip()
        else:
            # Fallback: store as binary note page
            content = "<p>Downloaded format not directly supported for inline reading. Please re-download as text or html.</p>"

        # Simple chunking by size to simulate chapters
        CHUNK = 2000
        chunks: List[str] = []
        i = 0
        while i < len(content):
            chunks.append(content[i:i+CHUNK])
            i += CHUNK

        chapters_meta: List[Dict[str, Any]] = []
        for idx, chunk in enumerate(chunks, start=1):
            chap_id = f"ch{idx}"
            html = f"<!doctype html><html><head><meta charset='utf-8'><title>Chapter {idx}</title></head><body>{chunk}</body></html>"
            (chapters_dir / f"{chap_id}.html").write_text(html, encoding="utf-8")
            chapters_meta.append({"id": chap_id, "title": f"Chapter {idx}", "href": f"{chap_id}.html"})

        manifest = {
            "title": None,
            "authors": [],
            "chapters": chapters_meta,
        }
        (book_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
