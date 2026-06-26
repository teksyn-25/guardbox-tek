"""
Shared CDR pipeline — sanitize bytes, build metadata, persist to storage.

Both intake paths (telegram_bot, upload) call process_file_bytes() with their
respective source tag. Exception handling stays in the caller — each path
responds differently (Telegram reply vs HTTP exception).
"""

import uuid

from cdr.sanitize import sanitize
from storage.interface import StorageBackend


def process_file_bytes(
    file_bytes: bytes,
    user_id: str,
    source: str,
    storage: StorageBackend,
) -> dict:
    """Sanitize raw file bytes and persist the clean copy. Returns saved metadata.

    Propagates UnsupportedFileType and CorruptedInput so callers can map them
    to user-facing responses.
    """
    clean_bytes, report = sanitize(file_bytes)
    metadata = {
        "file_id": str(uuid.uuid4()),
        "user_id": user_id,
        "source": source,
        "source_format": report["source_format"],
        "stripped": report["stripped"],
        "output_format": report["output_format"],
        "dimensions": report["dimensions"],
    }
    storage.save(user_id, clean_bytes, metadata)
    return metadata
