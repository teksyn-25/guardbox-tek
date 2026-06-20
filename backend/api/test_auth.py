"""
Tests for POST /auth — Login with Telegram.

The Telegram hash is computed the same way the real widget does it so these
tests exercise the actual verification logic, not a mock of it.
"""

import hashlib
import hmac
import time

import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)

_BOT_TOKEN = "test-bot-token-do-not-use"
_USER_ID   = 123456789


def _make_payload(overrides: dict | None = None) -> dict:
    """Build a valid Telegram login payload signed with _BOT_TOKEN."""
    base = {
        "id":         _USER_ID,
        "first_name": "Test",
        "auth_date":  int(time.time()),
    }
    base.update(overrides or {})

    # Compute hash over all fields except 'hash' itself
    secret = hashlib.sha256(_BOT_TOKEN.encode()).digest()
    data = {k: str(v) for k, v in base.items() if v is not None}
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    base["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return base


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN",      _BOT_TOKEN)
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")


# ── success ───────────────────────────────────────────────────────────────────

def test_valid_payload_returns_200():
    assert client.post("/auth", json=_make_payload()).status_code == 200


def test_valid_payload_returns_token():
    r = client.post("/auth", json=_make_payload())
    assert "token" in r.json()


def test_token_is_string():
    r = client.post("/auth", json=_make_payload())
    assert isinstance(r.json()["token"], str)


def test_optional_fields_accepted():
    payload = _make_payload({"last_name": "User", "username": "testuser"})
    assert client.post("/auth", json=payload).status_code == 200


# ── hash verification ─────────────────────────────────────────────────────────

def test_wrong_hash_returns_401():
    payload = _make_payload()
    payload["hash"] = "a" * 64
    assert client.post("/auth", json=payload).status_code == 401


def test_tampered_field_returns_401():
    payload = _make_payload()
    payload["id"] = 999999  # changes data but not the hash
    assert client.post("/auth", json=payload).status_code == 401


def test_wrong_bot_token_returns_401(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "wrong-token")
    assert client.post("/auth", json=_make_payload()).status_code == 401


# ── stale auth_date ───────────────────────────────────────────────────────────

def test_stale_auth_date_returns_401():
    payload = _make_payload({"auth_date": int(time.time()) - 90_000})  # >24 h ago
    assert client.post("/auth", json=payload).status_code == 401


# ── missing required fields ───────────────────────────────────────────────────

def test_missing_id_returns_422():
    payload = _make_payload()
    del payload["id"]
    assert client.post("/auth", json=payload).status_code == 422


def test_missing_auth_date_returns_422():
    payload = _make_payload()
    del payload["auth_date"]
    assert client.post("/auth", json=payload).status_code == 422


def test_missing_hash_returns_422():
    payload = _make_payload()
    del payload["hash"]
    assert client.post("/auth", json=payload).status_code == 422
