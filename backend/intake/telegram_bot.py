"""
Telegram bot adapter — server-to-server intake path.

Flow: user forwards a file to @GuardBoxBot → bot downloads it from Telegram's
servers (never via the user's device) → sanitize() → storage.save().

BOT_TOKEN is read from the environment. Never hardcoded.
"""

import logging
import os
import uuid

from admin_auth import OWNER_ID
from cdr.sanitize import CorruptedInput, UnsupportedFileType, sanitize
from storage import get_storage
from storage.interface import StorageBackend
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

logger = logging.getLogger(__name__)

_MSG_OK = "File sanitised. Open GuardBox to view the clean copy."
_MSG_UNSUPPORTED = (
    "Unsupported file type. GuardBox supports JPEG, PNG, and WebP images."
)
_MSG_CORRUPTED = "The file appears corrupted and could not be processed."
_MSG_ERROR = "Something went wrong. Please try again."


# ── core processing (no Telegram dependency — fully testable) ─────────────────


async def process_file_bytes(
    file_bytes: bytes,
    user_id: str,
    storage: StorageBackend,
) -> dict:
    """
    Sanitize raw file bytes and persist the clean copy.

    Returns the metadata dict that was saved. Propagates UnsupportedFileType
    and CorruptedInput so callers can map them to user-facing replies.
    """
    clean_bytes, report = sanitize(file_bytes)

    metadata = {
        "file_id": str(uuid.uuid4()),
        "user_id": user_id,
        "source": "telegram_bot",
        "source_format": report["source_format"],
        "stripped": report["stripped"],
        "output_format": report["output_format"],
        "dimensions": report["dimensions"],
    }

    storage.save(user_id, clean_bytes, metadata)
    return metadata


# ── Telegram handlers ─────────────────────────────────────────────────────────


async def _handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message is not None  # guaranteed by MessageHandler
    # Telegram sends multiple sizes; take the largest (last in list)
    photo = update.message.photo[-1]
    storage = get_storage()

    try:
        tg_file = await context.bot.get_file(photo.file_id)
        file_bytes = bytes(await tg_file.download_as_bytearray())
        await process_file_bytes(file_bytes, OWNER_ID, storage)
        await update.message.reply_text(_MSG_OK)
    except UnsupportedFileType:
        await update.message.reply_text(_MSG_UNSUPPORTED)
    except CorruptedInput:
        await update.message.reply_text(_MSG_CORRUPTED)
    except Exception:
        logger.exception("Unhandled error processing photo")
        await update.message.reply_text(_MSG_ERROR)


async def _handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message is not None  # guaranteed by MessageHandler
    doc = update.message.document
    assert doc is not None  # guaranteed by Document.ALL filter
    storage = get_storage()

    try:
        tg_file = await context.bot.get_file(doc.file_id)
        file_bytes = bytes(await tg_file.download_as_bytearray())
        await process_file_bytes(file_bytes, OWNER_ID, storage)
        await update.message.reply_text(_MSG_OK)
    except UnsupportedFileType:
        await update.message.reply_text(_MSG_UNSUPPORTED)
    except CorruptedInput:
        await update.message.reply_text(_MSG_CORRUPTED)
    except Exception:
        logger.exception("Unhandled error processing document")
        await update.message.reply_text(_MSG_ERROR)


# ── app wiring ────────────────────────────────────────────────────────────────


def build_app() -> Application:
    """Build the PTB Application. BOT_TOKEN must be set in the environment."""
    token = os.environ["BOT_TOKEN"]
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.PHOTO, _handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, _handle_document))
    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_app().run_polling()


if __name__ == "__main__":
    main()
