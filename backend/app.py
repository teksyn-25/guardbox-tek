"""
GuardBox API entry point.

Run: uvicorn app:app --no-access-log --reload   (from backend/)

URL layout:
  /api/*   — REST API for Flutter mobile app (Bearer token auth, JSON responses)
  /*       — Web UI (HttpOnly cookie auth, HTML responses via HTMX)
  /static/ — self-hosted JS (HTMX, Alpine)
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

_HERE = Path(__file__).parent

from api.auth import router as auth_router
from api.files import router as files_router
from api.web import router as web_router
from intake.upload import router as upload_router

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_app = None
    if os.getenv("BOT_TOKEN"):
        from intake.telegram_bot import build_app

        bot_app = build_app()
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling()
        logger.info("Telegram bot polling started")
    else:
        logger.warning("BOT_TOKEN not set — Telegram bot disabled")
    yield
    if bot_app:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()


app = FastAPI(
    title="GuardBox API", docs_url="/api/docs", redoc_url=None, lifespan=lifespan
)

# REST — Flutter mobile app
app.include_router(auth_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(upload_router, prefix="/api")

# Web UI — browser
app.include_router(web_router)

# Self-hosted static assets (HTMX, Alpine)
app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")
