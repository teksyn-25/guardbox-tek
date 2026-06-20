"""
GuardBox API entry point.

Run with: uvicorn app:app --reload   (from backend/)
"""

from fastapi import FastAPI

from api.auth import router as auth_router
from api.files import router as files_router

app = FastAPI(title="GuardBox API")
app.include_router(auth_router)
app.include_router(files_router)
