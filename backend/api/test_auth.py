"""
Tests for REST auth endpoints:
  GET  /api/auth/status
  POST /api/auth/setup
  POST /api/auth
"""

import pytest
from app import app
from fastapi.testclient import TestClient

client = TestClient(app)

_PASSWORD = "correcthorsebatterystaple"
_SHORT = "short"


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))


# ── GET /api/auth/status ──────────────────────────────────────────────────────


def test_status_before_setup():
    r = client.get("/api/auth/status")
    assert r.status_code == 200
    assert r.json() == {"setup_done": False}


def test_status_after_setup():
    client.post("/api/auth/setup", json={"password": _PASSWORD})
    r = client.get("/api/auth/status")
    assert r.json() == {"setup_done": True}


# ── POST /api/auth/setup ──────────────────────────────────────────────────────


def test_setup_returns_200():
    assert (
        client.post("/api/auth/setup", json={"password": _PASSWORD}).status_code == 200
    )


def test_setup_returns_bearer_token():
    r = client.post("/api/auth/setup", json={"password": _PASSWORD})
    assert "token" in r.json()
    assert isinstance(r.json()["token"], str)


def test_setup_second_call_returns_409():
    """
    SECURITY BOUNDARY: Single-owner enforcement

    Threat: Attacker calls /setup after the owner has already configured a password,
    overwriting it with their own.
    Expected: 409 — setup endpoint locked after first use.
    """
    client.post("/api/auth/setup", json={"password": _PASSWORD})
    r = client.post("/api/auth/setup", json={"password": "anotherpassword"})
    assert r.status_code == 409


def test_setup_short_password_returns_422():
    """
    SECURITY BOUNDARY: Password strength enforcement

    Threat: Owner sets a trivially short password, weakening brute-force resistance.
    Expected: 422 — passwords below minimum length are rejected at input.
    """
    r = client.post("/api/auth/setup", json={"password": _SHORT})
    assert r.status_code == 422


def test_setup_missing_field_returns_422():
    assert client.post("/api/auth/setup", json={}).status_code == 422


# ── POST /api/auth ────────────────────────────────────────────────────────────


def test_login_before_setup_returns_428():
    r = client.post("/api/auth", json={"password": _PASSWORD})
    assert r.status_code == 428


def test_login_correct_password_returns_200():
    client.post("/api/auth/setup", json={"password": _PASSWORD})
    assert client.post("/api/auth", json={"password": _PASSWORD}).status_code == 200


def test_login_returns_bearer_token():
    client.post("/api/auth/setup", json={"password": _PASSWORD})
    r = client.post("/api/auth", json={"password": _PASSWORD})
    assert "token" in r.json()


def test_login_wrong_password_returns_401():
    """
    SECURITY BOUNDARY: Credential validation

    Threat: Attacker attempts to log in with an incorrect password.
    Expected: 401 — access denied with no information about why the password failed.
    """
    client.post("/api/auth/setup", json={"password": _PASSWORD})
    assert (
        client.post("/api/auth", json={"password": "wrongpassword"}).status_code == 401
    )


def test_login_missing_field_returns_422():
    client.post("/api/auth/setup", json={"password": _PASSWORD})
    assert client.post("/api/auth", json={}).status_code == 422
