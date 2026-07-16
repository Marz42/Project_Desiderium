"""Admin ops status dashboard API."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.ops_status import OpsStatusService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status")
async def admin_status(db: AsyncSession = Depends(get_db)) -> dict:
    service = OpsStatusService(db)
    return await service.get_status()
