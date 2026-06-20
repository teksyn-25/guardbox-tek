"""
GuardBox API entry point.

Run with: uvicorn app:app --no-access-log --reload   (from backend/)
"""

import logging

from fastapi import FastAPI

from api.auth import router as auth_router
from api.files import router as files_router
from intake.upload import router as upload_router

# Suppress per-request access logs — they include client IP addresses.
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

app = FastAPI(title="GuardBox API")
app.include_router(auth_router)
app.include_router(files_router)
app.include_router(upload_router)
