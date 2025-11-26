from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Body
from pydantic import BaseModel, Field

from src.services.sources.gutendex import GutendexService
from src.services.sources.internet_archive import InternetArchiveService
from src.services.downloads import DownloadManager

router = APIRouter(prefix="/books", tags=["Books"])

class SearchRequest(BaseModel):
    source: str = Field(..., description="Source repository to search, e.g., 'gutenberg' or 'archive'")
    q: str = Field(..., description="Query string for searching books.")
    page: int = Field(1, description="Page number for pagination (1-based).")
    page_size: int = Field(20, description="Number of results per page.")

class BookItem(BaseModel):
    source: str = Field(..., description="Source identifier.")
    book_id: str = Field(..., description="Book identifier within the source.")
    title: str = Field(..., description="Book title.")
    authors: List[str] = Field(default_factory=list, description="List of author names.")
    cover_url: Optional[str] = Field(None, description="URL to cover image if available.")
    description: Optional[str] = Field(None, description="Short description/summary if available.")

class SearchResponse(BaseModel):
    total: int = Field(..., description="Total results if known, else estimated/0.")
    items: List[BookItem] = Field(default_factory=list, description="Search results.")

class BookDetail(BaseModel):
    source: str
    book_id: str
    title: str
    authors: List[str] = Field(default_factory=list)
    cover_url: Optional[str] = None
    description: Optional[str] = None
    download_options: List[str] = Field(default_factory=list, description="Available formats for download (e.g., text, html, epub)")

def _get_source_service(source: str):
    s = source.lower()
    if s in ["gutenberg", "gutendex", "pg"]:
        return GutendexService()
    if s in ["archive", "internetarchive", "ia"]:
        return InternetArchiveService()
    raise HTTPException(status_code=400, detail=f"Unsupported source '{source}'")

# PUBLIC_INTERFACE
@router.get("/search", response_model=SearchResponse, summary="Search books", description="Search open-source repositories for books.")
def search_books(
    source: str = Query(..., description="Source to search: gutenberg|archive"),
    q: str = Query(..., description="Query text"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
):
    """
    Search across a specified source for books matching a query.
    """
    svc = _get_source_service(source)
    result = svc.search(q=q, page=page, page_size=page_size)
    return SearchResponse(**result)

# PUBLIC_INTERFACE
@router.get("/{book_id}", response_model=BookDetail, summary="Get book details", description="Fetch a single book's details by source and book_id.")
def get_book_details(
    book_id: str,
    source: str = Query(..., description="Source of the book: gutenberg|archive"),
):
    """
    Get detailed information for a single book by source and ID.
    """
    svc = _get_source_service(source)
    detail = svc.get_book_details(book_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Book not found")
    return BookDetail(**detail)

class DownloadRequest(BaseModel):
    source: str = Field(..., description="Source of the book: gutenberg|archive")
    format: Optional[str] = Field(None, description="Preferred format: text|html|epub (if available). Defaults to best effort.")

class DownloadResponse(BaseModel):
    job_id: str = Field(..., description="Job ID to track download and normalization progress.")

# PUBLIC_INTERFACE
@router.post("/{book_id}/download", response_model=DownloadResponse, summary="Request book download", description="Start a download job for a book by source and ID.")
def request_download(
    book_id: str,
    payload: DownloadRequest = Body(...),
):
    """
    Creates a background job that downloads the book from the source and normalizes it into chapters.
    """
    svc = _get_source_service(payload.source)
    dm = DownloadManager()
    job_id = dm.enqueue_download(source=payload.source, book_id=book_id, source_service=svc, preferred_format=payload.format)
    return DownloadResponse(job_id=job_id)
