"""
WhatsApp / share-sheet intake endpoint.

POST /files/upload — the Flutter app streams bytes from the OS share intent
directly here. No write to GuardBox-owned disk before the upload; bytes travel
through device memory only.

Source tagged 'share_sheet'. No filename, size, or timestamp is retained.
"""

from api.middleware import require_user
from cdr.sanitize import CorruptedInput, ImageTooLarge, UnsupportedFileType
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from intake._pipeline import process_file_bytes
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
        metadata = process_file_bytes(raw, user_id, "share_sheet", storage)
    except UnsupportedFileType as exc:
        raise HTTPException(
            status_code=415, detail="Unsupported file type. JPEG, PNG, and WebP only."
        ) from exc
    except CorruptedInput as exc:
        raise HTTPException(
            status_code=422, detail="File appears corrupted and could not be processed."
        ) from exc
    except ImageTooLarge as exc:
        raise HTTPException(
            status_code=413, detail="Image dimensions exceed the allowed limit."
        ) from exc
    return {"file_id": metadata["file_id"]}
