"""
GuardBox API entry point.

Run: uvicorn app:app --no-access-log --reload   (from backend/)

URL layout:
  /api/*   — REST API for Capacitor (Bearer token auth, JSON responses)
  /*       — Web UI (HttpOnly cookie auth, HTML responses via HTMX)
  /static/ — self-hosted JS (HTMX, Alpine)
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

_HERE = Path(__file__).parent

from api.auth import router as auth_router
from api.files import router as files_router
from api.web import router as web_router
from intake.upload import router as upload_router

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

app = FastAPI(title="GuardBox API", docs_url="/api/docs", redoc_url=None)

# REST — Capacitor / mobile clients
app.include_router(auth_router,   prefix="/api")
app.include_router(files_router,  prefix="/api")
app.include_router(upload_router, prefix="/api")

# Web UI — browser
app.include_router(web_router)

# Self-hosted static assets (HTMX, Alpine)
app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")
