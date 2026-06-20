"""
Auth endpoints.

POST /auth — Login with Telegram.
Verifies the HMAC-SHA256 hash from the Telegram Login Widget / OAuth redirect,
then returns a signed session token.
"""

import hashlib
import hmac
import os
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.middleware import sign_token

router = APIRouter()

_MAX_AUTH_AGE = 86_400  # Telegram auth_date must be within 24 hours


class TelegramLoginPayload(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


def _verify_telegram_hash(payload: TelegramLoginPayload) -> None:
    """
    Telegram Login Widget hash check.
    https://core.telegram.org/widgets/login#checking-authorization
    """
    bot_token = os.environ["BOT_TOKEN"]
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    data = {k: str(v) for k, v in payload.model_dump(exclude={"hash"}).items() if v is not None}
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))

    expected = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, payload.hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram auth hash")

    if time.time() - payload.auth_date > _MAX_AUTH_AGE:
        raise HTTPException(status_code=401, detail="Telegram auth_date is too old")


@router.post("/auth")
def login(payload: TelegramLoginPayload) -> dict:
    _verify_telegram_hash(payload)
    token = sign_token(str(payload.id))
    return {"token": token}
