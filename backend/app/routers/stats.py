from fastapi import APIRouter

from ..models import Stats
from ..store import store

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=Stats)
async def get_stats():
    return store.stats()
