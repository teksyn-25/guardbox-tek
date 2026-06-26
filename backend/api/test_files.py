"""
API endpoint tests.

Uses FastAPI's TestClient (sync) with dependency_overrides to inject
a real LocalStorage backed by pytest's tmp_path — no mocks for storage.
Session tokens are signed with a test SESSION_SECRET set via monkeypatch.
"""

import pytest
import pyvips
from api.middleware import sign_token
from app import app
from fastapi.testclient import TestClient
from storage import get_storage
from storage.local import LocalStorage

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_USER = "user_a"
_OTHER = "user_b"


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret-do-not-use-in-prod")


@pytest.fixture
def storage(tmp_path):
    local = LocalStorage(root=str(tmp_path))
    app.dependency_overrides[get_storage] = lambda: local
    yield local
    app.dependency_overrides.clear()


@pytest.fixture
def client(storage):
    return TestClient(app)


@pytest.fixture
def auth():
    return {"Authorization": f"Bearer {sign_token(_USER)}"}


@pytest.fixture(scope="module")
def tiny_png():
    return pyvips.Image.black(8, 8, bands=3).write_to_buffer(".png")


def _meta(file_id: str, user_id: str = _USER) -> dict:
    return {
        "file_id": file_id,
        "user_id": user_id,
        "source": "telegram_bot",
        "source_format": "jpeg",
        "stripped": [],
        "output_format": "png",
        "dimensions": [8, 8],
    }


# ── auth guard ────────────────────────────────────────────────────────────────


def test_no_auth_header_returns_401(client):
    """
    SECURITY BOUNDARY: Authentication required

    Threat: Unauthenticated request attempts to list files.
    Expected: 401 — no data returned, no information leaked.
    """
    assert client.get("/api/files?state=pending").status_code == 401


def test_invalid_token_returns_401(client):
    """
    SECURITY BOUNDARY: Token validation

    Threat: Attacker submits a forged or corrupted Bearer token.
    Expected: 401 — token rejected before any storage access.
    """
    r = client.get(
        "/api/files?state=pending", headers={"Authorization": "Bearer garbage"}
    )
    assert r.status_code == 401


def test_wrong_scheme_returns_401(client):
    """
    SECURITY BOUNDARY: Auth scheme enforcement

    Threat: Client sends Basic auth credentials instead of Bearer token.
    Expected: 401 — wrong scheme rejected outright.
    """
    r = client.get(
        "/api/files?state=pending", headers={"Authorization": "Basic dXNlcjpwYXNz"}
    )
    assert r.status_code == 401


# ── GET /files?state= ─────────────────────────────────────────────────────────


def test_list_pending_returns_200(client, storage, auth, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    assert client.get("/api/files?state=pending", headers=auth).status_code == 200


def test_list_pending_returns_list(client, storage, auth, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    r = client.get("/api/files?state=pending", headers=auth)
    assert isinstance(r.json(), list)


def test_list_returns_only_matching_state(client, storage, auth, tiny_png):
    storage.save(_USER, tiny_png, _meta("p1"))
    storage.save(_USER, tiny_png, _meta("s1"))
    storage.move(_USER, "s1", "saved")
    r = client.get("/api/files?state=pending", headers=auth)
    ids = [m["file_id"] for m in r.json()]
    assert ids == ["p1"]


def test_list_empty_returns_empty_list(client, auth):
    r = client.get("/api/files?state=pending", headers=auth)
    assert r.json() == []


def test_list_invalid_state_returns_422(client, auth):
    assert client.get("/api/files?state=infected", headers=auth).status_code == 422


def test_list_isolates_users(client, storage, auth, tiny_png):
    """
    SECURITY BOUNDARY: User isolation

    Threat: User A lists files and receives User B's file IDs in the response.
    Expected: List contains only files owned by the authenticated user.
    """
    storage.save(_OTHER, tiny_png, _meta("other_file", user_id=_OTHER))
    r = client.get("/api/files?state=pending", headers=auth)
    ids = [m["file_id"] for m in r.json()]
    assert "other_file" not in ids


# ── GET /files/{id} ───────────────────────────────────────────────────────────


def test_get_metadata_returns_200(client, storage, auth, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    assert client.get("/api/files/f1", headers=auth).status_code == 200


def test_get_metadata_returns_correct_file_id(client, storage, auth, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    r = client.get("/api/files/f1", headers=auth)
    assert r.json()["file_id"] == "f1"


def test_get_metadata_nonexistent_returns_404(client, auth):
    assert client.get("/api/files/no_such_file", headers=auth).status_code == 404


# ── GET /files/{id}/image ─────────────────────────────────────────────────────


def test_get_image_returns_200(client, storage, auth, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    assert client.get("/api/files/f1/image", headers=auth).status_code == 200


def test_get_image_content_type_is_png(client, storage, auth, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    r = client.get("/api/files/f1/image", headers=auth)
    assert r.headers["content-type"] == "image/png"


def test_get_image_bytes_start_with_png_magic(client, storage, auth, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    r = client.get("/api/files/f1/image", headers=auth)
    assert r.content[:8] == _PNG_MAGIC


def test_get_image_nonexistent_returns_404(client, auth):
    assert client.get("/api/files/no_such/image", headers=auth).status_code == 404


# ── POST /files/{id}/save ─────────────────────────────────────────────────────


def test_save_returns_204(client, storage, auth, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    assert client.post("/api/files/f1/save", headers=auth).status_code == 204


def test_save_moves_file_to_saved(client, storage, auth, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    client.post("/api/files/f1/save", headers=auth)
    saved_ids = [m["file_id"] for m in storage.list(_USER, "saved")]
    assert "f1" in saved_ids


def test_save_nonexistent_returns_404(client, auth):
    assert client.post("/api/files/no_such/save", headers=auth).status_code == 404


# ── DELETE /files/{id} ───────────────────────────────────────────────────────


def test_delete_returns_204(client, storage, auth, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    assert client.delete("/api/files/f1", headers=auth).status_code == 204


def test_delete_file_is_gone(client, storage, auth, tiny_png):
    storage.save(_USER, tiny_png, _meta("f1"))
    client.delete("/api/files/f1", headers=auth)
    assert client.get("/api/files/f1", headers=auth).status_code == 404


def test_delete_nonexistent_returns_404(client, auth):
    assert client.delete("/api/files/no_such", headers=auth).status_code == 404
