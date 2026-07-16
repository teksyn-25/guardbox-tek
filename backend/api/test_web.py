"""
Tests for web UI routes — HTML responses via HTMX + Jinja2.

Auth uses HttpOnly cookie (gb_session). HTMX requests carry HX-Request: true.
Storage is overridden with a real LocalStorage backed by tmp_path.
"""

import sys

import pytest
from api.middleware import sign_token
from app import app
from cdr.sanitize import sanitize  # noqa: F401 — registers cdr.sanitize in sys.modules
from fastapi.testclient import TestClient
from storage import get_storage
from storage.local import LocalStorage

# The module object — NOT `import cdr.sanitize`, whose `.sanitize` attr is the shadowing fn.
sanitize_mod = sys.modules["cdr.sanitize"]

_USER = "web_test_user"
_SESSION_SECRET = "test-secret-do-not-use"
_PASSWORD = "correcthorsebatterystaple"


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("SESSION_SECRET", _SESSION_SECRET)
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    monkeypatch.setenv("SESSION_SECURE_COOKIE", "false")
    import rate_limit

    rate_limit.reset()  # throttle state is a process global; isolate each test
    from admin_auth import set_password

    set_password(_PASSWORD)  # default state: password already configured


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


# ── GET /setup ────────────────────────────────────────────────────────────────


def test_setup_already_done_redirects_to_login(client):
    r = client.get("/setup")
    assert r.status_code == 302
    assert "/auth/login" in r.headers["location"]


def test_setup_not_done_returns_form(client, monkeypatch):
    monkeypatch.setattr("api.web.is_setup_done", lambda: False)
    r = client.get("/setup")
    assert r.status_code == 200
    assert 'name="password"' in r.text


# ── POST /setup ───────────────────────────────────────────────────────────────


def test_setup_post_valid_redirects_to_login(client, monkeypatch):
    monkeypatch.setattr("api.web.is_setup_done", lambda: False)
    r = client.post(
        "/setup", data={"password": "mynewpassword", "confirm": "mynewpassword"}
    )
    assert r.status_code == 303
    assert "/auth/login" in r.headers["location"]


def test_setup_post_mismatch_returns_422(client, monkeypatch):
    monkeypatch.setattr("api.web.is_setup_done", lambda: False)
    r = client.post("/setup", data={"password": "password1", "confirm": "password2"})
    assert r.status_code == 422
    assert "match" in r.text.lower()


def test_setup_post_too_short_returns_422(client, monkeypatch):
    monkeypatch.setattr("api.web.is_setup_done", lambda: False)
    r = client.post("/setup", data={"password": "short", "confirm": "short"})
    assert r.status_code == 422


# ── GET /auth/login ───────────────────────────────────────────────────────────


def test_auth_login_returns_200(client):
    r = client.get("/auth/login")
    assert r.status_code == 200


def test_auth_login_returns_html_form(client):
    r = client.get("/auth/login")
    assert "text/html" in r.headers["content-type"]
    assert 'name="password"' in r.text


def test_auth_login_redirects_to_setup_when_not_done(client, monkeypatch):
    monkeypatch.setattr("api.web.is_setup_done", lambda: False)
    r = client.get("/auth/login")
    assert r.status_code == 302
    assert "/setup" in r.headers["location"]


# ── POST /auth/login ──────────────────────────────────────────────────────────


def test_auth_login_correct_password_sets_cookie(client):
    r = client.post("/auth/login", data={"password": _PASSWORD})
    assert "gb_session" in r.cookies


def test_auth_login_correct_password_redirects_home(client):
    r = client.post("/auth/login", data={"password": _PASSWORD})
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_auth_login_wrong_password_returns_401(client):
    r = client.post("/auth/login", data={"password": "wrongpassword"})
    assert r.status_code == 401


def test_auth_login_wrong_password_shows_error(client):
    r = client.post("/auth/login", data={"password": "wrongpassword"})
    assert "Incorrect" in r.text


def test_auth_login_wrong_password_applies_progressive_delay(client, monkeypatch):
    # 2nd consecutive miss awaits 0.25s (1st is free) — brute-force throttle.
    slept = []

    async def _fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr("api.web.asyncio.sleep", _fake_sleep)
    client.post("/auth/login", data={"password": "wrongpassword"})  # 1st → 0s
    client.post("/auth/login", data={"password": "wrongpassword"})  # 2nd → 0.25s
    assert slept == [0.25]


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


# ── POST /upload (manual FAB upload) ─────────────────────────────────────────


def test_upload_without_auth_redirects_to_login(client, tiny_png):
    r = client.post("/upload", files={"file": ("img.png", tiny_png, "image/png")})
    assert r.status_code == 303
    assert "/auth/login" in r.headers["location"]


def test_upload_no_file_redirects_home(client, session_cookie):
    r = client.post("/upload", cookies=session_cookie)
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_upload_valid_png_returns_200(client, session_cookie, tiny_png):
    r = client.post(
        "/upload",
        files={"file": ("img.png", tiny_png, "image/png")},
        cookies=session_cookie,
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200


def test_upload_valid_png_stores_file(client, session_cookie, storage, tiny_png):
    client.post(
        "/upload",
        files={"file": ("img.png", tiny_png, "image/png")},
        cookies=session_cookie,
        headers={"HX-Request": "true"},
    )
    assert len(storage.list(_USER, "pending")) == 1


def test_upload_source_tagged_share_sheet(client, session_cookie, storage, tiny_png):
    client.post(
        "/upload",
        files={"file": ("img.png", tiny_png, "image/png")},
        cookies=session_cookie,
        headers={"HX-Request": "true"},
    )
    meta = storage.list(_USER, "pending")[0]
    assert meta["source"] == "share_sheet"


def test_upload_does_not_store_filename(client, session_cookie, storage, tiny_png):
    client.post(
        "/upload",
        files={"file": ("secret-name.png", tiny_png, "image/png")},
        cookies=session_cookie,
        headers={"HX-Request": "true"},
    )
    meta = storage.list(_USER, "pending")[0]
    assert "filename" not in meta
    assert "secret-name" not in str(meta)


def test_upload_returns_html(client, session_cookie, tiny_png):
    r = client.post(
        "/upload",
        files={"file": ("img.png", tiny_png, "image/png")},
        cookies=session_cookie,
        headers={"HX-Request": "true"},
    )
    assert "text/html" in r.headers["content-type"]


def test_upload_unsupported_type_returns_error(client, session_cookie):
    r = client.post(
        "/upload",
        files={"file": ("doc.pdf", b"%PDF-1.4 garbage", "application/pdf")},
        cookies=session_cookie,
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    assert "Unsupported" in r.text


def test_upload_too_large_returns_error(client, session_cookie):
    big = b"\xff\xd8\xff" + b"x" * (25 * 1024 * 1024 + 1)
    r = client.post(
        "/upload",
        files={"file": ("big.jpg", big, "image/jpeg")},
        cookies=session_cookie,
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    assert "25 MB" in r.text


def test_upload_oversized_dimensions_returns_error(client, session_cookie, monkeypatch):
    # Decompression-bomb guard: over-pixel image renders the error partial (200),
    # not an unhandled 500. Cap dropped below the 8×8 fixture.
    import pyvips

    monkeypatch.setattr(sanitize_mod, "MAX_PIXELS", 10)
    tiny = pyvips.Image.black(8, 8, bands=3).write_to_buffer(".png")
    r = client.post(
        "/upload",
        files={"file": ("img.png", tiny, "image/png")},
        cookies=session_cookie,
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    assert "dimensions" in r.text.lower()


def test_upload_non_htmx_redirects_home(client, session_cookie, tiny_png):
    r = client.post(
        "/upload",
        files={"file": ("img.png", tiny_png, "image/png")},
        cookies=session_cookie,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/"
