"""Authentication middleware for single-manager admin access."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from app.config import get_settings
from app.web.session import get_session_data


class AuthMiddleware(BaseHTTPMiddleware):
    EXEMPT_PREFIXES = ("/health", "/login", "/docs", "/openapi.json", "/redoc")

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return await call_next(request)

        settings = get_settings()
        if not settings.manager_password:
            return await call_next(request)

        session = get_session_data(request)
        if session.get("authenticated"):
            request.state.session = session
            return await call_next(request)

        return RedirectResponse(f"/login?next={path}", status_code=303)
