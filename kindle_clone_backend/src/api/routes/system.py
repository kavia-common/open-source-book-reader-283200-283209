from fastapi import APIRouter

router = APIRouter(tags=["System"])

# PUBLIC_INTERFACE
@router.get("/", summary="Health Check", description="Simple health check endpoint that returns service status.")
def health_check():
    """
    Returns a static health status for the service.
    """
    return {"message": "Healthy"}
