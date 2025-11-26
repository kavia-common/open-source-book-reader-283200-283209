from __future__ import annotations

import threading
import uuid
from typing import Any, Dict, Optional
from pathlib import Path

from src.core.config import get_config
from src.db.cache import FilesystemCache
from src.services.normalize import Normalizer

_jobs_lock = threading.Lock()
_jobs: Dict[str, Dict[str, Any]] = {}

def _set_job(job_id: str, **kwargs: Any) -> None:
    with _jobs_lock:
        if job_id not in _jobs:
            _jobs[job_id] = {"job_id": job_id, "status": "queued", "progress": 0, "error": None}
        _jobs[job_id].update(kwargs)

def _get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _jobs_lock:
        return dict(_jobs.get(job_id)) if job_id in _jobs else None

class DownloadManager:
    """
    In-process download manager that spawns a thread per download job.
    Suitable for demo/single-instance deployments.
    """

    def __init__(self) -> None:
        self.cache = FilesystemCache()
        cfg = get_config()
        self.norm_root = Path(cfg.content_root) / "normalized"

    # PUBLIC_INTERFACE
    def enqueue_download(self, source: str, book_id: str, source_service: Any, preferred_format: Optional[str] = None) -> str:
        """
        Create a new job and start a worker thread to download and normalize content.
        """
        job_id = str(uuid.uuid4())
        _set_job(job_id, status="queued", progress=0, error=None)

        def worker():
            try:
                _set_job(job_id, status="running", progress=5)
                # Resolve download info
                info = source_service.get_download(book_id, preferred_format=preferred_format)
                url = info["url"]
                kind = info["type"]
                # Download bytes
                from src.utils.http_client import HttpClient
                http = HttpClient(timeout=60.0)
                data = http.get_bytes(url)
                _set_job(job_id, progress=40)
                # Store raw asset
                filename = f"book.{ 'html' if kind=='html' else ('txt' if kind=='text' else 'bin') }"
                path = self.cache.put_asset(source, book_id, filename, data)
                _set_job(job_id, progress=60)
                # Normalize into chapters
                norm = Normalizer()
                norm.normalize(source=source, book_id=book_id, kind=kind, src_path=path)
                _set_job(job_id, progress=100, status="done")
            except Exception as e:
                _set_job(job_id, status="error", error=str(e))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return job_id

    # PUBLIC_INTERFACE
    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status dict for a given job if present.
        """
        return _get_job(job_id)
