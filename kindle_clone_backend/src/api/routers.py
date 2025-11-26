from fastapi import APIRouter
from src.api.routes.system import router as system_router
from src.api.routes.books import router as books_router
from src.api.routes.downloads import router as downloads_router
from src.api.routes.content import router as content_router

router = APIRouter()
router.include_router(system_router)
router.include_router(books_router)
router.include_router(downloads_router)
router.include_router(content_router)
