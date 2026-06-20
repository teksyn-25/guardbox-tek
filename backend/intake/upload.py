"""
WhatsApp / share-sheet intake endpoint.

POST /files/upload — the Capacitor app streams bytes from the OS share intent
directly here. No write to GuardBox-owned disk before the upload; bytes travel
through device memory only.

Source tagged 'share_sheet'. No filename, size, or timestamp is retained.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from api.middleware import require_user
from cdr.sanitize import CorruptedInput, UnsupportedFileType, sanitize
from storage import get_storage
from storage.interface import StorageBackend

router = APIRouter()

_MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


@router.post("/files/upload", status_code=201)
async def upload_file(
    file: UploadFile,
    user_id: str = Depends(require_user),
    storage: StorageBackend = Depends(get_storage),
) -> dict:
    raw = await file.read(_MAX_FILE_SIZE + 1)
    if len(raw) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 25 MB limit")

    try:
        clean_bytes, report = sanitize(raw)
    except UnsupportedFileType:
        raise HTTPException(status_code=415, detail="Unsupported file type. JPEG, PNG, and WebP only.")
    except CorruptedInput:
        raise HTTPException(status_code=422, detail="File appears corrupted and could not be processed.")

    metadata = {
        "file_id": str(uuid.uuid4()),
        "user_id": user_id,
        "source": "share_sheet",
        "source_format": report["source_format"],
        "stripped": report["stripped"],
        "output_format": report["output_format"],
        "dimensions": report["dimensions"],
    }
    storage.save(user_id, clean_bytes, metadata)
    return {"file_id": metadata["file_id"]}
