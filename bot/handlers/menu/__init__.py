"""Сборка роутеров меню `aida_max` в один общий router."""

from maxo import Router

from .navigation import router as navigation_router
from .selections import router as selections_router

router = Router()
router.include_router(navigation_router)
router.include_router(selections_router)
