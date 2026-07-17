import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.db import dispose_engine
from app.logging_config import configure_logging
from app.services.config_validation import validate_runtime_config
from app.web.middleware import AuthMiddleware
from app.web.routes.admin_status import router as admin_status_router
from app.web.routes.auth import router as auth_router
from app.web.routes.brief import router as brief_router
from app.web.routes.candidates import router as candidates_router
from app.web.routes.health import router as health_router
from app.web.routes.history import router as history_router
from app.web.routes.performance import router as performance_router
from app.web.routes.trends import router as trends_router
from app.web.routes.watchlist import router as watchlist_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    validate_runtime_config(settings)
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
        version="0.10.0",
        lifespan=lifespan,
    )
    app.add_middleware(AuthMiddleware)
    app.include_router(health_router)
    app.include_router(admin_status_router)
    app.include_router(auth_router)
    app.include_router(candidates_router)
    app.include_router(trends_router)
    app.include_router(history_router)
    app.include_router(performance_router)
    app.include_router(brief_router)
    app.include_router(watchlist_router)

    @app.get("/")
    async def root():
        return RedirectResponse("/candidates", status_code=303)

    return app


app = create_app()
