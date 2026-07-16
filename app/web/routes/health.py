from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import check_database_connection, get_db
from app.services.system_health import collect_health

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> JSONResponse:
    db_ok = await check_database_connection()
    if not db_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "database": "down"},
        )
    return JSONResponse(content={"status": "ok", "database": "up"})


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    payload = await collect_health(db)
    code = status.HTTP_200_OK
    if payload["status"] == "degraded":
        code = status.HTTP_200_OK
    elif payload["status"] == "unavailable":
        code = status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=payload)
