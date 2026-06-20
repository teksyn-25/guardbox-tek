"""
Tests for web UI routes — HTML responses via HTMX + Jinja2.

Auth uses HttpOnly cookie (gb_session). HTMX requests carry HX-Request: true.
Storage is overridden with a real LocalStorage backed by tmp_path.
"""

import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

from app import app
from api.middleware import sign_token
from storage import get_storage
from storage.local import LocalStorage

_BOT_TOKEN = "test-bot-token"
_USER = "web_test_user"
_SESSION_SECRET = "test-secret-do-not-use"
_BOT_ID = "99999999"
_BASE_URL = "https://guardbox.example.com"


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET",      _SESSION_SECRET)
    monkeypatch.setenv("BOT_TOKEN",           _BOT_TOKEN)
    monkeypatch.setenv("TELEGRAM_BOT_ID",     _BOT_ID)
    monkeypatch.setenv("GUARDBOX_BASE_URL",   _BASE_URL)
    monkeypatch.setenv("SESSION_SECURE_COOKIE", "false")


@pytest.fixture
def storage(tmp_path):
    local = LocalStorage(root=str(tmp_path))
    app.dependency_overrides[get_storage] = lambda: local
    yield local
    app.dependency_overrides.clear()


@pytest.fixture
def client(storage):
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def session_cookie():
    return {"gb_session": sign_token(_USER)}


@pytest.fixture(scope="module")
def tiny_png():
    import pyvips
    return pyvips.Image.black(8, 8, bands=3).write_to_buffer(".png")


def _meta(file_id: str, source: str = "telegram_bot") -> dict:
    return {
        "file_id": file_id,
        "user_id": _USER,
        "source": source,
        "source_format": "jpeg",
        "stripped": ["EXIF"],
        "output_format": "png",
        "dimensions": [8, 8],
    }


def _make_tg_auth_result(user_id: int = 12345) -> str:
    payload = {"id": user_id, "first_name": "Test", "auth_date": int(time.time())}
    secret = hashlib.sha256(_BOT_TOKEN.encode()).digest()
    data = {k: str(v) for k, v in payload.items()}
    check_str = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    payload["hash"] = hmac.new(secret, check_str.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()


# ── GET /auth/login ───────────────────────────────────────────────────────────

def test_auth_login_redirects(client):
    r = client.get("/auth/login")
    assert r.status_code == 302


def test_auth_login_redirects_to_telegram(client):
    r = client.get("/auth/login")
    assert "oauth.telegram.org" in r.headers["location"]


def test_auth_login_includes_bot_id(client):
    r = client.get("/auth/login")
    assert _BOT_ID in r.headers["location"]


# ── GET /auth/callback ────────────────────────────────────────────────────────

def test_auth_callback_valid_sets_cookie(client):
    r = client.get(f"/auth/callback?tgAuthResult={_make_tg_auth_result()}")
    assert "gb_session" in r.cookies


def test_auth_callback_valid_redirects_to_dashboard(client):
    r = client.get(f"/auth/callback?tgAuthResult={_make_tg_auth_result()}")
    assert r.status_code == 302
    assert r.headers["location"] == "/"


def test_auth_callback_invalid_data_returns_400(client):
    r = client.get("/auth/callback?tgAuthResult=bm90anNvbg")
    assert r.status_code == 400


def test_auth_callback_tampered_hash_returns_401(client):
    payload = {"id": 1, "first_name": "X", "auth_date": int(time.time()), "hash": "a" * 64}
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    r = client.get(f"/auth/callback?tgAuthResult={encoded}")
    assert r.status_code == 401


# ── POST /auth/logout ─────────────────────────────────────────────────────────

def test_auth_logout_redirects_to_login(client, session_cookie):
    r = client.post("/auth/logout", cookies=session_cookie)
    assert r.status_code == 303
    assert "/auth/login" in r.headers["location"]


def test_auth_logout_clears_cookie(client, session_cookie):
    r = client.post("/auth/logout", cookies=session_cookie)
    assert r.cookies.get("gb_session", "") == ""


# ── GET / (dashboard) ─────────────────────────────────────────────────────────

def test_index_without_auth_redirects_to_login(client):
    r = client.get("/")
    assert r.status_code == 302
    assert "/auth/login" in r.headers["location"]


def test_index_with_cookie_returns_200(client, session_cookie):
    r = client.get("/", cookies=session_cookie)
    assert r.status_code == 200


def test_index_returns_html(client, session_cookie):
    r = client.get("/", cookies=session_cookie)
    assert "text/html" in r.headers["content-type"]


def test_index_htmx_returns_partial(client, session_cookie):
    r = client.get("/", cookies=session_cookie, headers={"HX-Request": "true"})
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_index_shows_dashboard_content(client, session_cookie):
    r = client.get("/", cookies=session_cookie)
    body = r.text
    assert "Pending" in body or "Saved" in body or "GuardBox" in body


# ── GET /folder/{source} ──────────────────────────────────────────────────────

def test_folder_without_htmx_redirects(client, session_cookie):
    r = client.get("/folder/telegram_bot", cookies=session_cookie)
    assert r.status_code == 302


def test_folder_htmx_returns_200(client, session_cookie):
    r = client.get(
        "/folder/telegram_bot",
        cookies=session_cookie,
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200


def test_folder_htmx_returns_html(client, session_cookie):
    r = client.get(
        "/folder/share_sheet",
        cookies=session_cookie,
        headers={"HX-Request": "true"},
    )
    assert "text/html" in r.headers["content-type"]


def test_folder_without_auth_redirects(client):
    r = client.get("/folder/telegram_bot", headers={"HX-Request": "true"})
    assert r.status_code == 302


# ── GET /files/{id}/viewer ────────────────────────────────────────────────────

def test_viewer_without_auth_returns_401(client):
    r = client.get("/files/f1/viewer", headers={"HX-Request": "true"})
    assert r.status_code == 401


def test_viewer_without_htmx_redirects(client, session_cookie, storage, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    r = client.get("/files/f1/viewer", cookies=session_cookie)
    assert r.status_code == 302


def test_viewer_htmx_returns_200(client, session_cookie, storage, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    r = client.get(
        "/files/f1/viewer",
        cookies=session_cookie,
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200


def test_viewer_nonexistent_returns_404(client, session_cookie):
    r = client.get(
        "/files/no_such/viewer",
        cookies=session_cookie,
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 404


def test_viewer_shows_file_id(client, session_cookie, storage, tiny_png):
    storage.save(_USER, tiny_png, _meta("abc123"))
    r = client.get(
        "/files/abc123/viewer",
        cookies=session_cookie,
        headers={"HX-Request": "true"},
    )
    assert "abc123" in r.text


# ── POST /files/{id}/save ─────────────────────────────────────────────────────

def test_web_save_without_auth_returns_401(client):
    r = client.post("/files/f1/save")
    assert r.status_code == 401


def test_web_save_returns_200(client, session_cookie, storage, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    r = client.post("/files/f1/save", cookies=session_cookie)
    assert r.status_code == 200


def test_web_save_moves_to_saved(client, session_cookie, storage, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    client.post("/files/f1/save", cookies=session_cookie)
    saved_ids = [m["file_id"] for m in storage.list(_USER, "saved")]
    assert "f1" in saved_ids


def test_web_save_nonexistent_returns_404(client, session_cookie):
    r = client.post("/files/no_such/save", cookies=session_cookie)
    assert r.status_code == 404


def test_web_save_returns_html(client, session_cookie, storage, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    r = client.post("/files/f1/save", cookies=session_cookie)
    assert "text/html" in r.headers["content-type"]


# ── DELETE /files/{id} ────────────────────────────────────────────────────────

def test_web_delete_without_auth_returns_401(client):
    r = client.delete("/files/f1")
    assert r.status_code == 401


def test_web_delete_returns_200(client, session_cookie, storage, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    r = client.delete("/files/f1", cookies=session_cookie)
    assert r.status_code == 200


def test_web_delete_removes_file(client, session_cookie, storage, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    client.delete("/files/f1", cookies=session_cookie)
    assert storage.list(_USER, "pending") == []


def test_web_delete_nonexistent_returns_404(client, session_cookie):
    r = client.delete("/files/no_such", cookies=session_cookie)
    assert r.status_code == 404


def test_web_delete_returns_html(client, session_cookie, storage, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    r = client.delete("/files/f1", cookies=session_cookie)
    assert "text/html" in r.headers["content-type"]


# ── DELETE /files (clear all) ─────────────────────────────────────────────────

def test_web_clear_all_without_auth_returns_401(client):
    r = client.delete("/files")
    assert r.status_code == 401


def test_web_clear_all_returns_200(client, session_cookie):
    r = client.delete("/files", cookies=session_cookie)
    assert r.status_code == 200


def test_web_clear_all_removes_all_files(client, session_cookie, storage, tiny_png):
    storage.save(_USER, tiny_png, _meta("p1"))
    storage.save(_USER, tiny_png, _meta("p2"))
    storage.save(_USER, tiny_png, _meta("s1"))
    storage.move(_USER, "s1", "saved")
    client.delete("/files", cookies=session_cookie)
    assert storage.list(_USER, "pending") == []
    assert storage.list(_USER, "saved") == []


def test_web_clear_all_returns_html(client, session_cookie):
    r = client.delete("/files", cookies=session_cookie)
    assert "text/html" in r.headers["content-type"]
