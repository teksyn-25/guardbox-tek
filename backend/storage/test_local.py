import json
from pathlib import Path

import pytest
from storage.local import LocalStorage


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(root=str(tmp_path))


def _meta(file_id: str) -> dict:
    return {"file_id": file_id, "source": "telegram_bot", "stripped": ["EXIF", "GPS"]}


# ── save ─────────────────────────────────────────────────────────────────────


def test_save_creates_png(storage, tmp_path):
    storage.save("u1", b"\x89PNG", _meta("f1"))
    assert (tmp_path / "pending" / "u1" / "f1.png").exists()


def test_save_creates_json_sidecar(storage, tmp_path):
    meta = _meta("f2")
    storage.save("u1", b"\x89PNG", meta)
    stored = json.loads((tmp_path / "pending" / "u1" / "f2.json").read_text())
    assert stored == meta


# ── list ─────────────────────────────────────────────────────────────────────


def test_list_pending_returns_only_pending(storage):
    storage.save("u1", b"a", _meta("p1"))
    storage.save("u1", b"b", _meta("p2"))
    storage.move("u1", "p2", "saved")
    ids = [m["file_id"] for m in storage.list("u1", "pending")]
    assert ids == ["p1"]


def test_list_saved_returns_only_saved(storage):
    storage.save("u1", b"a", _meta("s1"))
    storage.move("u1", "s1", "saved")
    ids = [m["file_id"] for m in storage.list("u1", "saved")]
    assert ids == ["s1"]


def test_list_empty_for_user_with_no_files(storage):
    assert storage.list("nobody", "pending") == []


# ── get ──────────────────────────────────────────────────────────────────────


def test_get_returns_correct_bytes_and_metadata(storage):
    meta = _meta("g1")
    storage.save("u1", b"pixel_data", meta)
    data, returned = storage.get("u1", "g1")
    assert data == b"pixel_data"
    assert returned == meta


def test_get_nonexistent_raises_file_not_found(storage):
    with pytest.raises(FileNotFoundError):
        storage.get("u1", "no_such_file")


# ── delete ───────────────────────────────────────────────────────────────────


def test_delete_removes_png(storage, tmp_path):
    storage.save("u1", b"data", _meta("d1"))
    storage.delete("u1", "d1")
    assert not (tmp_path / "pending" / "u1" / "d1.png").exists()


def test_delete_removes_json_sidecar(storage, tmp_path):
    storage.save("u1", b"data", _meta("d1"))
    storage.delete("u1", "d1")
    assert not (tmp_path / "pending" / "u1" / "d1.json").exists()


def test_delete_leaves_nothing_on_disk(storage, tmp_path):
    storage.save("u1", b"data", _meta("d2"))
    storage.delete("u1", "d2")
    folder = tmp_path / "pending" / "u1"
    remaining = list(folder.iterdir()) if folder.exists() else []
    assert remaining == []


# ── move ─────────────────────────────────────────────────────────────────────


def test_move_present_in_new_location(storage, tmp_path):
    storage.save("u1", b"data", _meta("m1"))
    storage.move("u1", "m1", "saved")
    assert (tmp_path / "saved" / "u1" / "m1.png").exists()
    assert (tmp_path / "saved" / "u1" / "m1.json").exists()


def test_move_gone_from_old_location(storage, tmp_path):
    storage.save("u1", b"data", _meta("m2"))
    storage.move("u1", "m2", "saved")
    assert not (tmp_path / "pending" / "u1" / "m2.png").exists()
    assert not (tmp_path / "pending" / "u1" / "m2.json").exists()
