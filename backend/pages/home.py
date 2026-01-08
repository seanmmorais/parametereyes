from __future__ import annotations

import logging
from fastapi import APIRouter

logger = logging.getLogger("parametereyes.pages.home")

router = APIRouter()

@router.get("/health")
def health() -> dict:
    logger.debug("health() called")
    out = {"status": "ok"}
    logger.debug("health() returning %s", out)
    return out
