"""
File endpoints — the only HTTP interface the frontend calls.

All routes require a valid session token (require_user dependency).
user_id is extracted from the token; it is never a query parameter.
"""

from typing import Literal

from api.middleware import require_user
from fastapi import APIRouter, Depends, HTTPException, Response
from storage import get_storage
from storage.interface import StorageBackend

router = APIRouter(prefix="/files")


@router.get("")
def list_files(
    state: Literal["pending", "saved"],
    user_id: str = Depends(require_user),
    storage: StorageBackend = Depends(get_storage),
) -> list[dict]:
    return storage.list(user_id, state)


@router.get("/{file_id}")
def get_metadata(
    file_id: str,
    user_id: str = Depends(require_user),
    storage: StorageBackend = Depends(get_storage),
) -> dict:
    try:
        _, meta = storage.get(user_id, file_id)
        return meta
    except FileNotFoundError:
        raise HTTPException(status_code=404)


@router.get("/{file_id}/image")
def get_image(
    file_id: str,
    user_id: str = Depends(require_user),
    storage: StorageBackend = Depends(get_storage),
) -> Response:
    try:
        data, _ = storage.get(user_id, file_id)
        return Response(content=data, media_type="image/png")
    except FileNotFoundError:
        raise HTTPException(status_code=404)


@router.post("/{file_id}/save", status_code=204)
def save_file(
    file_id: str,
    user_id: str = Depends(require_user),
    storage: StorageBackend = Depends(get_storage),
) -> None:
    try:
        storage.move(user_id, file_id, "saved")
    except FileNotFoundError:
        raise HTTPException(status_code=404)


@router.delete("/{file_id}", status_code=204)
def delete_file(
    file_id: str,
    user_id: str = Depends(require_user),
    storage: StorageBackend = Depends(get_storage),
) -> None:
    try:
        storage.delete(user_id, file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404)
