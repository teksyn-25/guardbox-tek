"""
Self-hosted storage: KVM disk + JSON sidecars, no database.

Layout:
    {STORAGE_ROOT}/pending/{user_id}/{file_id}.png
    {STORAGE_ROOT}/pending/{user_id}/{file_id}.json
    {STORAGE_ROOT}/saved/{user_id}/{file_id}.png
    {STORAGE_ROOT}/saved/{user_id}/{file_id}.json

STORAGE_ROOT is read from the env var of the same name; defaults to /data/guardbox.
Never imported directly outside storage/ — always access via the interface.
"""

import json
import os
import shutil
from pathlib import Path

from .interface import StorageBackend

_DEFAULT_ROOT = "/data/guardbox"


class LocalStorage(StorageBackend):

    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root) if root is not None else Path(os.getenv("STORAGE_ROOT", _DEFAULT_ROOT))

    # ── internal helpers ──────────────────────────────────────────────────

    def _img(self, state: str, user_id: str, file_id: str) -> Path:
        return self.root / state / user_id / f"{file_id}.png"

    def _meta(self, state: str, user_id: str, file_id: str) -> Path:
        return self.root / state / user_id / f"{file_id}.json"

    def _locate(self, user_id: str, file_id: str) -> str:
        """Return the state folder ('pending' or 'saved') that holds file_id."""
        for state in ("pending", "saved"):
            if self._img(state, user_id, file_id).exists():
                return state
        raise FileNotFoundError(f"file {file_id!r} not found for user {user_id!r}")

    # ── StorageBackend interface ──────────────────────────────────────────

    def save(self, user_id: str, file_bytes: bytes, metadata: dict) -> None:
        file_id = metadata["file_id"]
        img = self._img("pending", user_id, file_id)
        img.parent.mkdir(parents=True, exist_ok=True)
        img.write_bytes(file_bytes)
        self._meta("pending", user_id, file_id).write_text(json.dumps(metadata))

    def list(self, user_id: str, state: str) -> list[dict]:
        folder = self.root / state / user_id
        if not folder.exists():
            return []
        return [json.loads(p.read_text()) for p in sorted(folder.glob("*.json"))]

    def get(self, user_id: str, file_id: str) -> tuple[bytes, dict]:
        state = self._locate(user_id, file_id)
        return (
            self._img(state, user_id, file_id).read_bytes(),
            json.loads(self._meta(state, user_id, file_id).read_text()),
        )

    def delete(self, user_id: str, file_id: str) -> None:
        state = self._locate(user_id, file_id)
        self._img(state, user_id, file_id).unlink()
        self._meta(state, user_id, file_id).unlink()

    def move(self, user_id: str, file_id: str, new_state: str) -> None:
        old_state = self._locate(user_id, file_id)
        if old_state == new_state:
            return
        new_img = self._img(new_state, user_id, file_id)
        new_img.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(self._img(old_state, user_id, file_id)), str(new_img))
        shutil.move(str(self._meta(old_state, user_id, file_id)), str(self._meta(new_state, user_id, file_id)))
