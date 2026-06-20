"""
Auth endpoints.

POST /auth — Login with Telegram. Implemented in build step 5.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/auth", status_code=501)
def login():
    # Step 5: verify Telegram login payload, call sign_token(), return the token.
    return {"detail": "Login with Telegram — implemented in step 5."}
