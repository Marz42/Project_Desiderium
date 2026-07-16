"""Shared FastAPI dependencies for the admin web UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from app.config import get_settings
from app.web.csrf import validate_csrf_token
from app.web.session import get_csrf_token, get_session_data

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def flash_redirect(url: str, message: str, *, error: bool = False) -> RedirectResponse:
    sep = "&" if "?" in url else "?"
    flash_type = "error" if error else "success"
    return RedirectResponse(f"{url}{sep}flash={message}&flash_type={flash_type}", status_code=303)


def verify_csrf(
    request: Request,
    *,
    form_token: str | None = None,
) -> None:
    settings = get_settings()
    if not settings.manager_password:
        return

    session = get_session_data(request)
    submitted = request.headers.get("X-CSRF-Token") or form_token
    if not validate_csrf_token(session.get("csrf_token"), submitted):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


async def verify_csrf_form(request: Request, csrf_token: str = Form("")) -> None:
    verify_csrf(request, form_token=csrf_token)
