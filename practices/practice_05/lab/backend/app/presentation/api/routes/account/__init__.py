from fastapi import APIRouter

from .find import router as find_router
from .me import router as me_router

router = APIRouter(prefix="/account", tags=["account"])
router.include_router(me_router)
router.include_router(find_router)
