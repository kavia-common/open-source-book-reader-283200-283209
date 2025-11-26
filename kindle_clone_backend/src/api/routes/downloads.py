from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.downloads import DownloadManager

router = APIRouter(prefix="/downloads", tags=["Downloads"])

class JobStatusResponse(BaseModel):
    job_id: str = Field(..., description="Job identifier.")
    status: str = Field(..., description="queued|running|done|error")
    progress: int = Field(0, description="Progress in percentage 0-100.")
    error: str | None = Field(None, description="Error message if status=error.")

# PUBLIC_INTERFACE
@router.get("/{job_id}/status", response_model=JobStatusResponse, summary="Get download job status", description="Returns status and progress of a previously created download job.")
def get_job_status(job_id: str):
    """
    Retrieve the current status of a download/normalization job.
    """
    dm = DownloadManager()
    status = dm.get_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(**status)
