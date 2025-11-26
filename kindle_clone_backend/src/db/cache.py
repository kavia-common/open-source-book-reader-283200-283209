"""
Filesystem-backed cache layer for storing book metadata and assets.

Structure on disk under CONTENT_ROOT:
  - CONTENT_ROOT/
      cache_index.json            # JSON index of metadata by source/book_id
      assets/
        <source>/
          <book_id>/
            <filename>            # arbitrary asset files (e.g., downloaded books, covers)
            ...

Index file schema (cache_index.json):
{
  "entries": {
    "<source>/<book_id>": {
      "metadata": { ... },        # arbitrary JSON-serializable dict
      "created_at": 1732654800    # epoch seconds of when metadata was cached
    },
    ...
  }
}

Features:
- Store and retrieve metadata with TTL validation.
- Store and retrieve binary/text assets per source/book_id and filename.
- Safe, concurrent-friendly index writes via write-to-temp-and-rename.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.core.config import get_config


INDEX_FILENAME = "cache_index.json"
ASSETS_DIRNAME = "assets"


@dataclass
class CacheStatus:
    """Represents the status of a cache lookup for metadata."""
    found: bool
    stale: bool
    metadata: Optional[Dict[str, Any]]


class FilesystemCache:
    """
    Filesystem-based cache that persists JSON metadata in an index file and
    assets as regular files under a hierarchical directory structure.
    """

    def __init__(self, root: Optional[str] = None, ttl_seconds: Optional[int] = None) -> None:
        cfg = get_config()
        self.root = Path(root or cfg.content_root)
        self.root.mkdir(parents=True, exist_ok=True)

        self.ttl_seconds = int(ttl_seconds if ttl_seconds is not None else cfg.cache_ttl_seconds)

        self.index_path = self.root / INDEX_FILENAME
        self.assets_root = self.root / ASSETS_DIRNAME
        self.assets_root.mkdir(parents=True, exist_ok=True)

        # Initialize index file if missing
        if not self.index_path.exists():
            self._write_index({"entries": {}})

    # INTERNAL UTILITIES

    def _read_index(self) -> Dict[str, Any]:
        try:
            with self.index_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"entries": {}}
        except json.JSONDecodeError:
            # If the file is corrupted, start fresh but do not delete immediately
            return {"entries": {}}

    def _write_index(self, data: Dict[str, Any]) -> None:
        # Write to a temp file and replace atomically to minimize corruption risks
        tmp_path = self.index_path.with_suffix(".json.tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.index_path)

    def _entry_key(self, source: str, book_id: str) -> str:
        return f"{source}/{book_id}"

    def _ensure_asset_dir(self, source: str, book_id: str) -> Path:
        path = self.assets_root / source / book_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    # PUBLIC API

    # PUBLIC_INTERFACE
    def put_metadata(self, source: str, book_id: str, metadata: Dict[str, Any]) -> None:
        """
        Store or update metadata for a given source + book_id.

        Args:
            source: Source identifier (e.g., 'gutenberg', 'archive').
            book_id: Unique identifier for the book within the source.
            metadata: JSON-serializable dictionary of metadata.

        Returns:
            None
        """
        index = self._read_index()
        entries = index.get("entries", {})
        entries[self._entry_key(source, book_id)] = {
            "metadata": metadata,
            "created_at": int(time.time()),
        }
        index["entries"] = entries
        self._write_index(index)

    # PUBLIC_INTERFACE
    def get_metadata(self, source: str, book_id: str) -> CacheStatus:
        """
        Retrieve metadata for a given source + book_id and indicate staleness by TTL.

        Args:
            source: Source identifier.
            book_id: Book identifier within the source.

        Returns:
            CacheStatus: Contains whether metadata was found, if it is stale, and the metadata itself.
        """
        index = self._read_index()
        key = self._entry_key(source, book_id)
        entry = index.get("entries", {}).get(key)
        if not entry:
            return CacheStatus(found=False, stale=False, metadata=None)

        created_at = int(entry.get("created_at", 0))
        stale = (int(time.time()) - created_at) > self.ttl_seconds
        metadata = entry.get("metadata")
        return CacheStatus(found=True, stale=stale, metadata=metadata)

    # PUBLIC_INTERFACE
    def put_asset(self, source: str, book_id: str, filename: str, data: bytes) -> Path:
        """
        Store an asset file for a given source + book_id.

        Args:
            source: Source identifier.
            book_id: Book identifier within the source.
            filename: Name of the asset file to store (e.g., 'book.epub', 'cover.jpg').
            data: Raw bytes to write.

        Returns:
            Path: The absolute path where the asset was stored.
        """
        asset_dir = self._ensure_asset_dir(source, book_id)
        file_path = asset_dir / filename
        with file_path.open("wb") as f:
            f.write(data)
        return file_path

    # PUBLIC_INTERFACE
    def get_asset_path(self, source: str, book_id: str, filename: str) -> Optional[Path]:
        """
        Get the path to a previously stored asset file if it exists.

        Args:
            source: Source identifier.
            book_id: Book identifier within the source.
            filename: Asset filename.

        Returns:
            Optional[Path]: Path if the file exists, otherwise None.
        """
        path = self.assets_root / source / book_id / filename
        return path if path.exists() else None

    # PUBLIC_INTERFACE
    def get_asset_bytes(self, source: str, book_id: str, filename: str) -> Optional[bytes]:
        """
        Read bytes of a stored asset file if it exists.

        Args:
            source: Source identifier.
            book_id: Book identifier within the source.
            filename: Asset filename.

        Returns:
            Optional[bytes]: File content as bytes if exists, otherwise None.
        """
        path = self.get_asset_path(source, book_id, filename)
        if not path:
            return None
        try:
            with path.open("rb") as f:
                return f.read()
        except OSError:
            return None

    # PUBLIC_INTERFACE
    def has_fresh_metadata(self, source: str, book_id: str) -> bool:
        """
        Check whether metadata exists and is not stale according to TTL.

        Args:
            source: Source identifier.
            book_id: Book identifier within the source.

        Returns:
            bool: True if metadata exists and is within TTL; False otherwise.
        """
        status = self.get_metadata(source, book_id)
        return status.found and not status.stale

    # PUBLIC_INTERFACE
    def purge_stale(self) -> Tuple[int, int]:
        """
        Remove stale metadata entries from the index. Does not delete assets.

        Returns:
            Tuple[int, int]: (num_total_entries, num_removed_stale_entries)
        """
        index = self._read_index()
        entries = index.get("entries", {})
        now = int(time.time())

        keys_to_remove = []
        for key, entry in entries.items():
            created_at = int(entry.get("created_at", 0))
            if (now - created_at) > self.ttl_seconds:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            entries.pop(key, None)

        index["entries"] = entries
        self._write_index(index)
        return (len(entries), len(keys_to_remove))
