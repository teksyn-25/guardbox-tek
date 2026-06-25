"""
Password-based admin auth for self-hosted GuardBox.

On first boot no password exists — the web UI redirects to /setup and the
mobile app calls GET /api/auth/status to detect this. The owner sets a
password once; it is stored as a scrypt hash in {STORAGE_ROOT}/.admin_password_hash.

To reset: delete .admin_password_hash and restart — the setup page reappears.
"""

import hashlib
import os
import secrets
from pathlib import Path

OWNER_ID = "owner"

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def _hash_path() -> Path:
    root = os.getenv("STORAGE_ROOT") or "/data/guardbox"
    return Path(root) / ".admin_password_hash"


def is_setup_done() -> bool:
    """True if a password has been set."""
    p = _hash_path()
    return p.exists() and bool(p.read_text().strip())


def set_password(password: str) -> None:
    """Hash and persist the password. Overwrites any existing hash."""
    salt = os.urandom(32)
    h = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P
    )
    p = _hash_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"{salt.hex()}:{h.hex()}")


def verify_password(candidate: str) -> bool:
    """Constant-time verification against the stored hash."""
    p = _hash_path()
    if not p.exists():
        return False
    stored = p.read_text().strip()
    try:
        salt_hex, hash_hex = stored.split(":")
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    h = hashlib.scrypt(
        candidate.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P
    )
    return secrets.compare_digest(h.hex(), hash_hex)
