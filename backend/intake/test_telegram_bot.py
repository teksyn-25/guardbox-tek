"""
Tests for the Telegram bot adapter.

process_file_bytes() is tested with real pyvips images and real LocalStorage
(tmp_path), so these tests exercise the full sanitize → store pipeline without
mocking the CDR or storage layers.

Handler error-routing tests use AsyncMock to simulate Telegram update objects
and verify the correct reply string is sent for each exception type.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pyvips = pytest.importorskip("pyvips")

import sys

from admin_auth import OWNER_ID
from cdr.sanitize import CorruptedInput, UnsupportedFileType
from intake._pipeline import process_file_bytes
from intake.telegram_bot import (
    _MAX_FILE_SIZE,
    _MSG_CORRUPTED,
    _MSG_ERROR,
    _MSG_OK,
    _MSG_TOO_LARGE,
    _MSG_TOO_LARGE_DIMS,
    _MSG_UNAUTHORIZED,
    _MSG_UNSUPPORTED,
    _handle_media,
    build_app,
)
from storage.local import LocalStorage

# The module object — NOT `import cdr.sanitize`, whose `.sanitize` attr is the shadowing fn.
sanitize_mod = sys.modules["cdr.sanitize"]

# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _owner_env(monkeypatch):
    # _make_update() sets effective_user.id == 42; authorise that sender by
    # default so the handler tests exercise the happy path. Individual auth
    # tests override or clear this.
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "42")


@pytest.fixture(scope="module")
def tiny_jpeg():
    return pyvips.Image.black(8, 8, bands=3).write_to_buffer(".jpg")


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(root=str(tmp_path))


def _make_update(reply_mock: AsyncMock) -> MagicMock:
    """Minimal Update-alike with a reply_text mock."""
    update = MagicMock()
    update.message.reply_text = reply_mock
    update.effective_user.id = 42
    return update


# ── process_file_bytes: core pipeline ────────────────────────────────────────


def test_process_file_bytes_saves_clean_file(tiny_jpeg, storage, tmp_path):
    meta = process_file_bytes(tiny_jpeg, "u1", "telegram_bot", storage)
    file_id = meta["file_id"]
    assert (tmp_path / "pending" / "u1" / f"{file_id}.png").exists()


def test_process_file_bytes_returns_source_telegram_bot(tiny_jpeg, storage):
    meta = process_file_bytes(tiny_jpeg, "u1", "telegram_bot", storage)
    assert meta["source"] == "telegram_bot"


def test_process_file_bytes_returns_all_required_fields(tiny_jpeg, storage):
    meta = process_file_bytes(tiny_jpeg, "u1", "telegram_bot", storage)
    for key in (
        "file_id",
        "user_id",
        "source",
        "source_format",
        "stripped",
        "output_format",
        "dimensions",
    ):
        assert key in meta, f"missing key: {key}"


def test_process_file_bytes_user_id_in_metadata(tiny_jpeg, storage):
    meta = process_file_bytes(tiny_jpeg, "user99", "telegram_bot", storage)
    assert meta["user_id"] == "user99"


def test_process_file_bytes_propagates_unsupported_file_type(storage):
    with pytest.raises(UnsupportedFileType):
        process_file_bytes(b"\x00\x01\x02\x03" * 16, "u1", "telegram_bot", storage)


def test_process_file_bytes_propagates_corrupted_input(tiny_jpeg, storage):
    with pytest.raises(CorruptedInput):
        process_file_bytes(tiny_jpeg[:3], "u1", "telegram_bot", storage)


def test_process_file_bytes_each_call_gets_unique_file_id(tiny_jpeg, storage):
    m1 = process_file_bytes(tiny_jpeg, "u1", "telegram_bot", storage)
    m2 = process_file_bytes(tiny_jpeg, "u1", "telegram_bot", storage)
    assert m1["file_id"] != m2["file_id"]


# ── handler error routing ─────────────────────────────────────────────────────


def _make_photo_update(reply_mock):
    update = _make_update(reply_mock)
    update.message.photo = [MagicMock(file_id="tg_photo_id")]
    update.message.document = None
    return update


def _make_document_update(reply_mock):
    update = _make_update(reply_mock)
    update.message.photo = None
    update.message.document = MagicMock(file_id="tg_doc_id")
    return update


async def _context_downloading(file_bytes: bytes) -> MagicMock:
    tg_file = AsyncMock()
    tg_file.download_as_bytearray.return_value = bytearray(file_bytes)
    ctx = MagicMock()
    ctx.bot.get_file = AsyncMock(return_value=tg_file)
    return ctx


async def test_photo_handler_replies_ok_on_success(tiny_jpeg, tmp_path):
    reply = AsyncMock()
    update = _make_photo_update(reply)
    ctx = await _context_downloading(tiny_jpeg)

    with patch(
        "intake.telegram_bot.get_storage", return_value=LocalStorage(root=str(tmp_path))
    ):
        await _handle_media(update, ctx)

    reply.assert_awaited_once_with(_MSG_OK)


async def test_photo_handler_replies_unsupported_on_bad_type(tmp_path):
    reply = AsyncMock()
    update = _make_photo_update(reply)
    ctx = await _context_downloading(b"\x00" * 32)

    with patch(
        "intake.telegram_bot.get_storage", return_value=LocalStorage(root=str(tmp_path))
    ):
        await _handle_media(update, ctx)

    reply.assert_awaited_once_with(_MSG_UNSUPPORTED)


async def test_photo_handler_replies_corrupted_on_bad_file(tiny_jpeg, tmp_path):
    reply = AsyncMock()
    update = _make_photo_update(reply)
    ctx = await _context_downloading(tiny_jpeg[:3])

    with patch(
        "intake.telegram_bot.get_storage", return_value=LocalStorage(root=str(tmp_path))
    ):
        await _handle_media(update, ctx)

    reply.assert_awaited_once_with(_MSG_CORRUPTED)


async def test_document_handler_replies_ok_on_success(tiny_jpeg, tmp_path):
    reply = AsyncMock()
    update = _make_document_update(reply)
    ctx = await _context_downloading(tiny_jpeg)

    with patch(
        "intake.telegram_bot.get_storage", return_value=LocalStorage(root=str(tmp_path))
    ):
        await _handle_media(update, ctx)

    reply.assert_awaited_once_with(_MSG_OK)


async def test_document_handler_replies_unsupported_on_bad_type(tmp_path):
    reply = AsyncMock()
    update = _make_document_update(reply)
    ctx = await _context_downloading(b"\x00" * 32)

    with patch(
        "intake.telegram_bot.get_storage", return_value=LocalStorage(root=str(tmp_path))
    ):
        await _handle_media(update, ctx)

    reply.assert_awaited_once_with(_MSG_UNSUPPORTED)


async def test_document_handler_replies_corrupted_on_bad_file(tiny_jpeg, tmp_path):
    reply = AsyncMock()
    update = _make_document_update(reply)
    ctx = await _context_downloading(tiny_jpeg[:3])

    with patch(
        "intake.telegram_bot.get_storage", return_value=LocalStorage(root=str(tmp_path))
    ):
        await _handle_media(update, ctx)

    reply.assert_awaited_once_with(_MSG_CORRUPTED)


# ── file size limit ───────────────────────────────────────────────────────────


async def test_photo_handler_replies_too_large_when_file_exceeds_limit(tmp_path):
    reply = AsyncMock()
    update = _make_photo_update(reply)
    ctx = await _context_downloading(b"\xff\xd8\xff" + b"\x00" * _MAX_FILE_SIZE)

    with patch(
        "intake.telegram_bot.get_storage", return_value=LocalStorage(root=str(tmp_path))
    ):
        await _handle_media(update, ctx)

    reply.assert_awaited_once_with(_MSG_TOO_LARGE)


async def test_photo_handler_replies_too_large_dims_on_bomb(
    tiny_jpeg, tmp_path, monkeypatch
):
    # Decompression-bomb guard: over-pixel image gets its own reply, not the
    # generic error swallowed by the broad except. Cap dropped below 8×8.
    monkeypatch.setattr(sanitize_mod, "MAX_PIXELS", 10)
    reply = AsyncMock()
    update = _make_photo_update(reply)
    ctx = await _context_downloading(tiny_jpeg)

    with patch(
        "intake.telegram_bot.get_storage", return_value=LocalStorage(root=str(tmp_path))
    ):
        await _handle_media(update, ctx)

    reply.assert_awaited_once_with(_MSG_TOO_LARGE_DIMS)


# ── sender authorization ──────────────────────────────────────────────────────


async def test_unauthorized_sender_is_rejected(tiny_jpeg, tmp_path, monkeypatch):
    # Sender 42 is not in the allowlist (owner is 999) → private-instance reply,
    # and the file is never downloaded or stored.
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "999")
    reply = AsyncMock()
    update = _make_photo_update(reply)
    ctx = await _context_downloading(tiny_jpeg)
    storage = LocalStorage(root=str(tmp_path))

    with patch("intake.telegram_bot.get_storage", return_value=storage):
        await _handle_media(update, ctx)

    reply.assert_awaited_once_with(_MSG_UNAUTHORIZED)
    ctx.bot.get_file.assert_not_awaited()
    assert storage.list(OWNER_ID, "pending") == []


async def test_unset_owner_rejects_all_senders(tiny_jpeg, tmp_path, monkeypatch):
    # Fail-closed: with no TELEGRAM_OWNER_ID configured, nobody is authorised.
    monkeypatch.delenv("TELEGRAM_OWNER_ID", raising=False)
    reply = AsyncMock()
    update = _make_photo_update(reply)
    ctx = await _context_downloading(tiny_jpeg)

    with patch(
        "intake.telegram_bot.get_storage", return_value=LocalStorage(root=str(tmp_path))
    ):
        await _handle_media(update, ctx)

    reply.assert_awaited_once_with(_MSG_UNAUTHORIZED)
    ctx.bot.get_file.assert_not_awaited()


async def test_authorized_sender_in_multi_id_allowlist_is_processed(
    tiny_jpeg, tmp_path, monkeypatch
):
    # Allowlist may hold several IDs (comma-separated); sender 42 is one of them.
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "7, 42 , 100")
    reply = AsyncMock()
    update = _make_photo_update(reply)
    ctx = await _context_downloading(tiny_jpeg)

    with patch(
        "intake.telegram_bot.get_storage", return_value=LocalStorage(root=str(tmp_path))
    ):
        await _handle_media(update, ctx)

    reply.assert_awaited_once_with(_MSG_OK)


# ── build_app wiring ──────────────────────────────────────────────────────────


def test_build_app_raises_without_bot_token(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(KeyError):
        build_app()
