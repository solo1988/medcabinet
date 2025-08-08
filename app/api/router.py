from fastapi import APIRouter

from app.api.web import router as web_router
from app.api.images import router as images_router
from app.api.applications import router as applications_router
from app.api.medicine import router as medicine_router

router = APIRouter()
router.include_router(web_router)
router.include_router(images_router)
router.include_router(applications_router)
router.include_router(medicine_router)
