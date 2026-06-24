"""
Web UI routes — return HTML for browser use via HTMX.

Auth flow:
  First run: any protected route → /setup (create password)
  Normal:    any protected route → /auth/login (enter password)
Navigation: HTMX swaps #main-content; Alpine.js controls the viewer modal.

REST API remains at /api/* (for Flutter mobile app).
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from admin_auth import OWNER_ID, is_setup_done, set_password, verify_password
from api.middleware import SESSION_MAX_AGE, SESSION_SECURE, sign_token, verify_token
from cdr.sanitize import CorruptedInput, UnsupportedFileType, sanitize
from storage import get_storage
from storage.interface import StorageBackend

_MAX_UPLOAD = 25 * 1024 * 1024  # 25 MB

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


# ── first-run setup ───────────────────────────────────────────────────────────

_MIN_PASSWORD_LEN = 8


@router.get("/setup", response_class=HTMLResponse)
async def setup_get(request: Request) -> Response:
    if is_setup_done():
        return RedirectResponse("/auth/login", status_code=302)
    return templates.TemplateResponse(request, "setup.html", {})


@router.post("/setup")
async def setup_post(
    request: Request,
    password: str = Form(...),
    confirm: str = Form(...),
) -> Response:
    if is_setup_done():
        return RedirectResponse("/auth/login", status_code=302)
    if len(password) < _MIN_PASSWORD_LEN:
        return templates.TemplateResponse(
            request, "setup.html",
            {"error": f"Password must be at least {_MIN_PASSWORD_LEN} characters."},
            status_code=422,
        )
    if password != confirm:
        return templates.TemplateResponse(
            request, "setup.html",
            {"error": "Passwords do not match."},
            status_code=422,
        )
    set_password(password)
    return RedirectResponse("/auth/login", status_code=303)


# ── auth ──────────────────────────────────────────────────────────────────────

@router.get("/auth/login", response_class=HTMLResponse)
async def auth_login(request: Request) -> Response:
    if not is_setup_done():
        return RedirectResponse("/setup", status_code=302)
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/auth/login")
async def auth_login_post(
    request: Request,
    password: str = Form(...),
) -> Response:
    if not is_setup_done():
        return RedirectResponse("/setup", status_code=302)
    if not verify_password(password):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Incorrect password."},
            status_code=401,
        )
    r = RedirectResponse("/", status_code=303)
    _set_session(r, sign_token(OWNER_ID))
    return r


@router.post("/auth/logout")
async def auth_logout() -> RedirectResponse:
    r = RedirectResponse("/auth/login", status_code=303)
    r.delete_cookie("gb_session")
    return r


# ── pages ─────────────────────────────────────────────────────────────────────

def _login_or_setup() -> str:
    return "/setup" if not is_setup_done() else "/auth/login"


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    user_id: str | None = Depends(_optional_user),
    storage: StorageBackend = Depends(get_storage),
) -> Response:
    if not user_id:
        return RedirectResponse(_login_or_setup(), status_code=302)
    ctx = _dash_ctx(user_id, storage)
    if _htmx(request):
        return templates.TemplateResponse(request, "partials/_dashboard.html", ctx)
    return templates.TemplateResponse(request, "dashboard.html", ctx)


@router.get("/folder/{source}", response_class=HTMLResponse)
async def folder(
    source: str,
    request: Request,
    user_id: str | None = Depends(_optional_user),
    storage: StorageBackend = Depends(get_storage),
) -> Response:
    if not user_id:
        return RedirectResponse(_login_or_setup(), status_code=302)
    if not _htmx(request):
        return RedirectResponse("/", status_code=302)
    all_files = storage.list(user_id, "pending") + storage.list(user_id, "saved")
    return templates.TemplateResponse(request, "partials/_folder.html", {
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
        return RedirectResponse("/", status_code=302)
    try:
        _, meta = storage.get(user_id, file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "partials/_viewer.html", {
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
    return templates.TemplateResponse(request, "partials/_dashboard.html", _dash_ctx(user_id, storage))


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
    return templates.TemplateResponse(request, "partials/_dashboard.html", _dash_ctx(user_id, storage))


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
    return templates.TemplateResponse(request, "partials/_dashboard.html", {
        "pending": [], "saved": [],
    })


# ── manual upload (HTMX file-input → FAB) ────────────────────────────────────

@router.post("/upload", response_class=HTMLResponse)
async def web_upload(
    request: Request,
    user_id: str | None = Depends(_optional_user),
    storage: StorageBackend = Depends(get_storage),
    file: UploadFile = File(default=None),
) -> Response:
    if not user_id:
        return RedirectResponse("/auth/login", status_code=303)
    if file is None:
        return RedirectResponse("/", status_code=303)
    raw = await file.read(_MAX_UPLOAD + 1)
    if len(raw) > _MAX_UPLOAD:
        ctx = {**_dash_ctx(user_id, storage), "error": "File exceeds 25 MB limit."}
        return templates.TemplateResponse(request, "partials/_dashboard.html", ctx)
    try:
        clean_bytes, report = sanitize(raw)
    except UnsupportedFileType:
        ctx = {**_dash_ctx(user_id, storage), "error": "Unsupported file type. JPEG, PNG, and WebP only."}
        return templates.TemplateResponse(request, "partials/_dashboard.html", ctx)
    except CorruptedInput:
        ctx = {**_dash_ctx(user_id, storage), "error": "File appears corrupted and could not be processed."}
        return templates.TemplateResponse(request, "partials/_dashboard.html", ctx)
    metadata = {
        "file_id": str(uuid.uuid4()),
        "user_id": user_id,
        "source": "share_sheet",
        "source_format": report["source_format"],
        "stripped": report["stripped"],
        "output_format": report["output_format"],
        "dimensions": report["dimensions"],
    }
    storage.save(user_id, clean_bytes, metadata)
    ctx = _dash_ctx(user_id, storage)
    if _htmx(request):
        return templates.TemplateResponse(request, "partials/_dashboard.html", ctx)
    return RedirectResponse("/", status_code=303)


# ── helpers ───────────────────────────────────────────────────────────────────

def _dash_ctx(user_id: str, storage: StorageBackend) -> dict:
    return {
        "pending": storage.list(user_id, "pending"),
        "saved":   storage.list(user_id, "saved"),
    }
