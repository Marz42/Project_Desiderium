import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db import dispose_engine
from app.logging_config import configure_logging
from app.web.routes.health import router as health_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "Starting %s",
        settings.app_name,
        extra={"service": "web", "component": "lifespan", "environment": settings.environment},
    )
    yield
    await dispose_engine()
    logger.info(
        "Stopped %s",
        settings.app_name,
        extra={"service": "web", "component": "lifespan"},
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health_router)
    return app


app = create_app()
