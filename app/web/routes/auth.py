"""Manager login and logout."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.responses import RedirectResponse

from app.config import get_settings
from app.web.csrf import generate_csrf_token
from app.web.deps import TEMPLATES, verify_csrf
from app.web.session import SESSION_COOKIE, sign_session

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, next: str = "/candidates", error: str | None = None):
    settings = get_settings()
    if not settings.manager_password:
        return RedirectResponse(next or "/candidates", status_code=303)
    return TEMPLATES.TemplateResponse(
        request,
        "auth/login.html",
        {"next": next, "error": error},
    )


@router.post("/login")
async def login_submit(
    request: Request,
    password: str = Form(...),
    next: str = Form("/candidates"),
):
    settings = get_settings()
    if not settings.manager_password or password != settings.manager_password:
        return RedirectResponse(f"/login?next={next}&error=1", status_code=303)

    token = sign_session(
        {"authenticated": True, "csrf_token": generate_csrf_token()},
        settings.secret_key,
    )
    response = RedirectResponse(next or "/candidates", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return response


@router.post("/logout")
async def logout(request: Request, csrf_token: str = Form("")):
    verify_csrf(request, form_token=csrf_token)
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
