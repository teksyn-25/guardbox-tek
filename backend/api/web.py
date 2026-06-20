"""
Web UI routes — return HTML for browser use via HTMX.

Auth flow: GET /auth/login → Telegram OAuth → GET /auth/callback → HttpOnly cookie.
Navigation: HTMX swaps #main-content; Alpine.js controls the viewer modal.

REST API remains at /api/* (unchanged for Capacitor).
"""

import base64
import json
import os
from urllib.parse import quote

from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from api.auth import TelegramLoginPayload, verify_telegram_hash
from api.middleware import SESSION_MAX_AGE, SESSION_SECURE, sign_token, verify_token
from storage import get_storage
from storage.interface import StorageBackend

router = APIRouter()
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

_SOURCE_LABEL = {"telegram_bot": "Telegram", "share_sheet": "WhatsApp"}


def _file_hue(file_id: str) -> int:
    h = 0
    for c in file_id:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return h % 360


templates.env.globals.update(source_label=_SOURCE_LABEL, file_hue=_file_hue)


def _optional_user(gb_session: str | None = Cookie(default=None)) -> str | None:
    if not gb_session:
        return None
    try:
        return verify_token(gb_session)
    except HTTPException:
        return None


def _htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _set_session(response: Response, token: str) -> None:
    response.set_cookie(
        "gb_session", token,
        httponly=True,
        secure=SESSION_SECURE,
        samesite="strict",
        max_age=SESSION_MAX_AGE,
    )


# ── auth ──────────────────────────────────────────────────────────────────────

@router.get("/auth/login")
async def auth_login() -> RedirectResponse:
    bot_id = os.environ["TELEGRAM_BOT_ID"]
    origin = os.environ["GUARDBOX_BASE_URL"].rstrip("/")
    callback = f"{origin}/auth/callback"
    url = (
        f"https://oauth.telegram.org/auth"
        f"?bot_id={bot_id}"
        f"&origin={quote(origin, safe='')}"
        f"&return_to={quote(callback, safe='')}"
    )
    return RedirectResponse(url, status_code=302)


@router.get("/auth/callback")
async def auth_callback(tgAuthResult: str) -> RedirectResponse:
    padding = (4 - len(tgAuthResult) % 4) % 4
    try:
        data = json.loads(base64.urlsafe_b64decode(tgAuthResult + "=" * padding))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid auth response")
    verify_telegram_hash(TelegramLoginPayload(**data))
    token = sign_token(str(data["id"]))
    r = RedirectResponse("/", status_code=302)
    _set_session(r, token)
    return r


@router.post("/auth/logout")
async def auth_logout() -> RedirectResponse:
    r = RedirectResponse("/auth/login", status_code=303)
    r.delete_cookie("gb_session")
    return r


# ── pages ─────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    user_id: str | None = Depends(_optional_user),
    storage: StorageBackend = Depends(get_storage),
) -> Response:
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)
    ctx = _dash_ctx(request, user_id, storage)
    if _htmx(request):
        return templates.TemplateResponse("partials/_dashboard.html", ctx)
    return templates.TemplateResponse("dashboard.html", ctx)


@router.get("/folder/{source}", response_class=HTMLResponse)
async def folder(
    source: str,
    request: Request,
    user_id: str | None = Depends(_optional_user),
    storage: StorageBackend = Depends(get_storage),
) -> Response:
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)
    if not _htmx(request):
        return RedirectResponse("/")
    all_files = storage.list(user_id, "pending") + storage.list(user_id, "saved")
    return templates.TemplateResponse("partials/_folder.html", {
        "request": request,
        "source": source,
        "files": [f for f in all_files if f.get("source") == source],
    })


@router.get("/files/{file_id}/viewer", response_class=HTMLResponse)
async def viewer(
    file_id: str,
    request: Request,
    user_id: str | None = Depends(_optional_user),
    storage: StorageBackend = Depends(get_storage),
) -> Response:
    if not user_id:
        raise HTTPException(status_code=401)
    if not _htmx(request):
        return RedirectResponse("/")
    try:
        _, meta = storage.get(user_id, file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("partials/_viewer.html", {
        "request": request,
        "file": meta,
    })


# ── mutations (HTMX — return updated dashboard partial) ──────────────────────

@router.post("/files/{file_id}/save", response_class=HTMLResponse)
async def web_save(
    file_id: str,
    request: Request,
    user_id: str | None = Depends(_optional_user),
    storage: StorageBackend = Depends(get_storage),
) -> Response:
    if not user_id:
        raise HTTPException(status_code=401)
    try:
        storage.move(user_id, file_id, "saved")
    except FileNotFoundError:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("partials/_dashboard.html", _dash_ctx(request, user_id, storage))


@router.delete("/files/{file_id}", response_class=HTMLResponse)
async def web_delete(
    file_id: str,
    request: Request,
    user_id: str | None = Depends(_optional_user),
    storage: StorageBackend = Depends(get_storage),
) -> Response:
    if not user_id:
        raise HTTPException(status_code=401)
    try:
        storage.delete(user_id, file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("partials/_dashboard.html", _dash_ctx(request, user_id, storage))


@router.delete("/files", response_class=HTMLResponse)
async def web_clear_all(
    request: Request,
    user_id: str | None = Depends(_optional_user),
    storage: StorageBackend = Depends(get_storage),
) -> Response:
    if not user_id:
        raise HTTPException(status_code=401)
    for state in ("pending", "saved"):
        for meta in storage.list(user_id, state):
            storage.delete(user_id, meta["file_id"])
    return templates.TemplateResponse("partials/_dashboard.html", {
        "request": request, "pending": [], "saved": [],
    })


# ── helpers ───────────────────────────────────────────────────────────────────

def _dash_ctx(request: Request, user_id: str, storage: StorageBackend) -> dict:
    return {
        "request": request,
        "pending": storage.list(user_id, "pending"),
        "saved":   storage.list(user_id, "saved"),
    }
