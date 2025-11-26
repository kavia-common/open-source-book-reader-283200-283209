from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from src.core.config import get_config

router = APIRouter(prefix="/content", tags=["Content"])

class ChapterInfo(BaseModel):
    id: str = Field(..., description="Chapter id (filename without extension).")
    title: Optional[str] = Field(None, description="Chapter title if available.")
    href: str = Field(..., description="Relative URL to fetch chapter.")

class ManifestResponse(BaseModel):
    source: str
    book_id: str
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    chapters: List[ChapterInfo] = Field(default_factory=list)

def _book_dir(source: str, book_id: str) -> Path:
    cfg = get_config()
    return Path(cfg.content_root) / "normalized" / source / book_id

# PUBLIC_INTERFACE
@router.get("/{source}/{book_id}/manifest", response_model=ManifestResponse, summary="Get content manifest", description="Provides manifest of normalized chapters for a given book.")
def get_manifest(source: str, book_id: str):
    """
    Return a simple manifest with chapter list for a normalized book under CONTENT_ROOT/normalized/{source}/{book_id}.
    """
    base = _book_dir(source, book_id)
    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Manifest not found")

    try:
        import json
        with manifest_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Basic validation
        data["source"] = source
        data["book_id"] = book_id
        chapters = data.get("chapters", [])
        data["chapters"] = [
            {
                "id": c.get("id") or c.get("href", "").rsplit(".", 1)[0],
                "title": c.get("title"),
                "href": f"/content/{source}/{book_id}/chapters/{c.get('id') or c.get('href', '').rsplit('.',1)[0]}",
            }
            for c in chapters
        ]
        return ManifestResponse(**data)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read manifest")

# PUBLIC_INTERFACE
@router.get("/{source}/{book_id}/chapters/{chapter_id}", summary="Get chapter content", description="Returns the HTML content of a specific chapter.")
def get_chapter(source: str, book_id: str, chapter_id: str):
    """
    Serve chapter HTML as text/html from normalized content.
    """
    base = _book_dir(source, book_id)
    chapter_path = base / "chapters" / f"{chapter_id}.html"
    if not chapter_path.exists():
        raise HTTPException(status_code=404, detail="Chapter not found")
    try:
        html = chapter_path.read_text(encoding="utf-8")
        return Response(content=html, media_type="text/html")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read chapter")
