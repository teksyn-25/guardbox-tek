import os

from .interface import StorageBackend


def get_storage() -> StorageBackend:
    """Factory: reads STORAGE_BACKEND env var and returns the matching implementation."""
    backend = os.getenv("STORAGE_BACKEND", "local")
    if backend == "local":
        from .local import LocalStorage
        return LocalStorage()
    if backend == "cloud":
        raise NotImplementedError("cloud backend not yet implemented")
    raise ValueError(f"Unknown STORAGE_BACKEND: {backend!r}")
