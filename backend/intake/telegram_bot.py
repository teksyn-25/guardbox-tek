"""
Telegram bot adapter — server-to-server intake path.

Flow: user forwards a file to @GuardBoxBot → bot downloads it from Telegram's
servers (never via the user's device) → sanitize() → storage.save().

BOT_TOKEN is read from the environment. Never hardcoded.
"""

import logging
import os

from admin_auth import OWNER_ID
from cdr.sanitize import CorruptedInput, ImageTooLarge, UnsupportedFileType
from intake._pipeline import process_file_bytes
from storage import get_storage
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

logger = logging.getLogger(__name__)

_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB — Telegram bot API hard limit

_MSG_OK = "File sanitised. Open GuardBox to view the clean copy."
_MSG_UNSUPPORTED = (
    "Unsupported file type. GuardBox supports JPEG, PNG, and WebP images."
)
_MSG_CORRUPTED = "The file appears corrupted and could not be processed."
_MSG_TOO_LARGE = "File exceeds the 20 MB limit."
_MSG_TOO_LARGE_DIMS = "Image dimensions exceed the limit and could not be processed."
_MSG_ERROR = "Something went wrong. Please try again."


# ── Telegram handler ──────────────────────────────────────────────────────────


async def _handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    msg = update.message
    if msg.photo:
        tg_file_id = msg.photo[-1].file_id
    elif msg.document:
        tg_file_id = msg.document.file_id
    else:
        return
    storage = get_storage()
    try:
        tg_file = await context.bot.get_file(tg_file_id)
        file_bytes = bytes(await tg_file.download_as_bytearray())
        if len(file_bytes) > _MAX_FILE_SIZE:
            await update.message.reply_text(_MSG_TOO_LARGE)
            return
        process_file_bytes(file_bytes, OWNER_ID, "telegram_bot", storage)
        await update.message.reply_text(_MSG_OK)
    except UnsupportedFileType:
        await update.message.reply_text(_MSG_UNSUPPORTED)
    except CorruptedInput:
        await update.message.reply_text(_MSG_CORRUPTED)
    except ImageTooLarge:
        await update.message.reply_text(_MSG_TOO_LARGE_DIMS)
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Unhandled error processing media")
        await update.message.reply_text(_MSG_ERROR)


# ── app wiring ────────────────────────────────────────────────────────────────


def build_app() -> Application:
    """Build the PTB Application. BOT_TOKEN must be set in the environment."""
    token = os.environ["BOT_TOKEN"]
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, _handle_media))
    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_app().run_polling()


if __name__ == "__main__":
    main()
