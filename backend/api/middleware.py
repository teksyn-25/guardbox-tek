"""
Session token middleware.

Tokens are HMAC-signed with SESSION_SECRET (itsdangerous URLSafeTimedSerializer).
Step 5 (Login with Telegram) calls sign_token() and returns the token to the client.
All protected endpoints use require_user as a FastAPI dependency.
"""

import os

from fastapi import Header, HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def _signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(os.environ["SESSION_SECRET"])


def sign_token(user_id: str) -> str:
    return _signer().dumps(user_id)


def verify_token(token: str) -> str:
    try:
        return _signer().loads(token, max_age=_MAX_AGE)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=401, detail="Invalid or expired session token")


async def require_user(authorization: str | None = Header(default=None, alias="Authorization")) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Bearer token required")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token required")
    return verify_token(token)
