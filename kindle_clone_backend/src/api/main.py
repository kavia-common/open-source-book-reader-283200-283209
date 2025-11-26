from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_config  # ensure config is loaded and available
from src.api.routers import router as api_router

app = FastAPI(
    title="Kindle Clone Backend",
    description="Backend API for managing book retrieval, library, bookmarks, and content serving.",
    version="0.1.0",
    openapi_tags=[
        {"name": "System", "description": "System and health endpoints"},
        {"name": "Books", "description": "Search and retrieve book details"},
        {"name": "Downloads", "description": "Download job management"},
        {"name": "Content", "description": "Serve normalized book content"},
        {"name": "Cache", "description": "Cache and content storage operations"},
    ],
)

# Read config to initialize content root directory on startup
_cfg = get_config()
# The cache module will create directories lazily when used.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(api_router)
