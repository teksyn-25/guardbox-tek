"""
Session token middleware.

Tokens are HMAC-signed (itsdangerous URLSafeTimedSerializer).
Accepted from:
  - Authorization: Bearer <token>   — Flutter mobile app / REST API clients
  - Cookie: gb_session=<token>      — browser (HttpOnly, SameSite=Strict)

SESSION_SECRET   — required env var, signs tokens.
SESSION_SECURE_COOKIE — set to "false" only for local HTTP dev (default: true).
"""

import os

from fastapi import Cookie, Header, HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SESSION_MAX_AGE    = 60 * 60 * 24 * 30   # 30 days
SESSION_SECURE     = os.getenv("SESSION_SECURE_COOKIE", "true").lower() == "true"

_MAX_AGE = SESSION_MAX_AGE


def _signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(os.environ["SESSION_SECRET"])


def sign_token(user_id: str) -> str:
    return _signer().dumps(user_id)


def verify_token(token: str) -> str:
    try:
        return _signer().loads(token, max_age=_MAX_AGE)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=401, detail="Invalid or expired session token")


async def require_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    gb_session:    str | None = Cookie(default=None),
) -> str:
    """FastAPI dependency — accepts Bearer header (API) or HttpOnly cookie (web)."""
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            return verify_token(token)
    if gb_session:
        return verify_token(gb_session)
    raise HTTPException(status_code=401, detail="Authentication required")
