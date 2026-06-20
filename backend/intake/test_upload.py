"""
Tests for POST /files/upload — WhatsApp share-sheet intake.

Uses FastAPI's TestClient with a real LocalStorage (tmp_path) and a valid
session token. Verifies CDR runs, metadata is correct, and banned fields
(filename, size, timestamp) are never stored.
"""

import io

import pytest
from fastapi.testclient import TestClient

pyvips = pytest.importorskip("pyvips")

from app import app
from api.middleware import sign_token
from storage import get_storage
from storage.local import LocalStorage

_USER = "upload_user"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
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
def tiny_jpeg():
    return pyvips.Image.black(8, 8, bands=3).write_to_buffer(".jpg")


def _upload(client, auth, data: bytes, filename="test.jpg"):
    return client.post(
        "/api/files/upload",
        headers=auth,
        files={"file": (filename, io.BytesIO(data), "image/jpeg")},
    )


# ── success ───────────────────────────────────────────────────────────────────

def test_upload_returns_201(client, auth, tiny_jpeg):
    assert _upload(client, auth, tiny_jpeg).status_code == 201


def test_upload_returns_file_id(client, auth, tiny_jpeg):
    r = _upload(client, auth, tiny_jpeg)
    assert "file_id" in r.json()


def test_upload_file_appears_in_pending(client, auth, storage, tiny_jpeg):
    r = _upload(client, auth, tiny_jpeg)
    file_id = r.json()["file_id"]
    ids = [m["file_id"] for m in storage.list(_USER, "pending")]
    assert file_id in ids


def test_upload_source_is_share_sheet(client, auth, storage, tiny_jpeg):
    r = _upload(client, auth, tiny_jpeg)
    file_id = r.json()["file_id"]
    _, meta = storage.get(_USER, file_id)
    assert meta["source"] == "share_sheet"


def test_upload_output_is_png(client, auth, storage, tiny_jpeg):
    r = _upload(client, auth, tiny_jpeg)
    file_id = r.json()["file_id"]
    data, _ = storage.get(_USER, file_id)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


# ── metadata minimization ─────────────────────────────────────────────────────

def test_upload_does_not_store_filename(client, auth, storage, tiny_jpeg):
    r = _upload(client, auth, tiny_jpeg, filename="sensitive_doc.jpg")
    file_id = r.json()["file_id"]
    _, meta = storage.get(_USER, file_id)
    assert "filename" not in meta


def test_upload_does_not_store_size(client, auth, storage, tiny_jpeg):
    r = _upload(client, auth, tiny_jpeg)
    file_id = r.json()["file_id"]
    _, meta = storage.get(_USER, file_id)
    assert "size_in"  not in meta
    assert "size_out" not in meta


def test_upload_does_not_store_timestamp(client, auth, storage, tiny_jpeg):
    r = _upload(client, auth, tiny_jpeg)
    file_id = r.json()["file_id"]
    _, meta = storage.get(_USER, file_id)
    assert "created_at" not in meta


# ── auth guard ────────────────────────────────────────────────────────────────

def test_upload_without_auth_returns_401(client, tiny_jpeg):
    r = client.post(
        "/api/files/upload",
        files={"file": ("x.jpg", io.BytesIO(tiny_jpeg), "image/jpeg")},
    )
    assert r.status_code == 401


# ── rejection cases ───────────────────────────────────────────────────────────

def test_upload_unsupported_type_returns_415(client, auth):
    assert _upload(client, auth, b"\x00\x01\x02\x03" * 64, "file.bin").status_code == 415


def test_upload_corrupted_file_returns_422(client, auth, tiny_jpeg):
    assert _upload(client, auth, tiny_jpeg[:3], "trunc.jpg").status_code == 422


def test_upload_oversized_file_returns_413(client, auth):
    big = b"\xff\xd8\xff" + b"\x00" * (25 * 1024 * 1024 + 1)
    assert _upload(client, auth, big, "big.jpg").status_code == 413
