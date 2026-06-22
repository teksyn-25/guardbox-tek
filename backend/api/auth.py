"""
Auth endpoints for Capacitor / REST clients.

GET  /api/auth/status  — returns {"setup_done": bool}, no auth required
POST /api/auth/setup   — first-run only: set the password, returns Bearer token
POST /api/auth         — login with password, returns Bearer token
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from admin_auth import OWNER_ID, is_setup_done, set_password, verify_password
from api.middleware import sign_token

router = APIRouter()

_MIN_PASSWORD_LEN = 8


class PasswordSetupPayload(BaseModel):
    password: str


class PasswordLoginPayload(BaseModel):
    password: str


@router.get("/auth/status")
def auth_status() -> dict:
    return {"setup_done": is_setup_done()}


@router.post("/auth/setup")
def setup(payload: PasswordSetupPayload) -> dict:
    if is_setup_done():
        raise HTTPException(status_code=409, detail="Password already set")
    if len(payload.password) < _MIN_PASSWORD_LEN:
        raise HTTPException(status_code=422, detail=f"Password must be at least {_MIN_PASSWORD_LEN} characters")
    set_password(payload.password)
    return {"token": sign_token(OWNER_ID)}


@router.post("/auth")
def login(payload: PasswordLoginPayload) -> dict:
    if not is_setup_done():
        raise HTTPException(status_code=428, detail="setup_required")
    if not verify_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    return {"token": sign_token(OWNER_ID)}
