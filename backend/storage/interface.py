from abc import ABC, abstractmethod


class StorageBackend(ABC):

    @abstractmethod
    def save(self, user_id: str, file_bytes: bytes, metadata: dict) -> None:
        """Store clean file bytes and its metadata sidecar in pending state."""

    @abstractmethod
    def list(self, user_id: str, state: str) -> list[dict]:
        """Return metadata for all files owned by user_id in the given state."""

    @abstractmethod
    def get(self, user_id: str, file_id: str) -> tuple[bytes, dict]:
        """Return (file_bytes, metadata) for the given file. Raises FileNotFoundError."""

    @abstractmethod
    def delete(self, user_id: str, file_id: str) -> None:
        """Remove file bytes and metadata. Raises FileNotFoundError if absent."""

    @abstractmethod
    def move(self, user_id: str, file_id: str, new_state: str) -> None:
        """Transition a file between states (e.g. pending → saved)."""
