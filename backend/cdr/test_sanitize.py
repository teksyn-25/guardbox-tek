import pytest

pyvips = pytest.importorskip("pyvips")

import sys

import cdr.sanitize  # ensure submodule is in sys.modules
from cdr.sanitize import CorruptedInput, FileTooLarge, UnsupportedFileType, sanitize

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def tiny_jpeg():
    return pyvips.Image.black(8, 8, bands=3).write_to_buffer(".jpg")


@pytest.fixture(scope="module")
def tiny_png():
    return pyvips.Image.black(8, 8, bands=3).write_to_buffer(".png")


@pytest.fixture(scope="module")
def tiny_webp():
    return pyvips.Image.black(8, 8, bands=3).write_to_buffer(".webp")


# ── format detection ──────────────────────────────────────────────────────────


def test_unknown_magic_raises_unsupported_file_type():
    with pytest.raises(UnsupportedFileType):
        sanitize(b"\x00\x01\x02\x03" * 16)


def test_truncated_jpeg_raises_corrupted(tiny_jpeg):
    with pytest.raises(CorruptedInput):
        sanitize(tiny_jpeg[:3])


# ── output is always PNG ──────────────────────────────────────────────────────


def test_jpeg_input_produces_png(tiny_jpeg):
    out, _ = sanitize(tiny_jpeg)
    assert out[:8] == _PNG_MAGIC


def test_png_input_produces_png(tiny_png):
    out, _ = sanitize(tiny_png)
    assert out[:8] == _PNG_MAGIC


def test_webp_input_produces_png(tiny_webp):
    out, _ = sanitize(tiny_webp)
    assert out[:8] == _PNG_MAGIC


def test_output_is_parseable_by_pyvips(tiny_jpeg):
    out, _ = sanitize(tiny_jpeg)
    img = pyvips.Image.new_from_buffer(out, "")
    assert img.width == 8 and img.height == 8


# ── metadata stripping (whitelist: test what remains, not just what was removed) ──


def test_output_has_no_exif_fields(tiny_jpeg):
    out, _ = sanitize(tiny_jpeg)
    fields = pyvips.Image.new_from_buffer(out, "").get_fields()
    assert not any(f.startswith("exif-") for f in fields)


def test_output_has_no_xmp(tiny_jpeg):
    out, _ = sanitize(tiny_jpeg)
    fields = pyvips.Image.new_from_buffer(out, "").get_fields()
    assert "xmp-xml" not in fields


# ── strip report ──────────────────────────────────────────────────────────────


def test_strip_report_source_format_jpeg(tiny_jpeg):
    _, report = sanitize(tiny_jpeg)
    assert report["source_format"] == "jpeg"


def test_strip_report_source_format_png(tiny_png):
    _, report = sanitize(tiny_png)
    assert report["source_format"] == "png"


def test_strip_report_source_format_webp(tiny_webp):
    _, report = sanitize(tiny_webp)
    assert report["source_format"] == "webp"


def test_strip_report_output_format_always_png(tiny_jpeg):
    _, report = sanitize(tiny_jpeg)
    assert report["output_format"] == "png"


def test_strip_report_dimensions_match_input(tiny_jpeg):
    _, report = sanitize(tiny_jpeg)
    assert report["dimensions"] == [8, 8]


# ── decompression bomb guard ──────────────────────────────────────────────────


def test_oversized_image_raises_file_too_large(monkeypatch, tiny_jpeg):
    monkeypatch.setattr(sys.modules["cdr.sanitize"], "MAX_PIXELS", 1)
    with pytest.raises(FileTooLarge, match="exceeds maximum size"):
        sanitize(tiny_jpeg)


def test_image_at_exact_limit_is_accepted(monkeypatch, tiny_jpeg):
    monkeypatch.setattr(sys.modules["cdr.sanitize"], "MAX_PIXELS", 8 * 8)
    out, _ = sanitize(tiny_jpeg)
    assert out[:8] == _PNG_MAGIC


# ── invariants ────────────────────────────────────────────────────────────────


def test_original_bytes_not_mutated(tiny_jpeg):
    snapshot = bytearray(tiny_jpeg)
    sanitize(tiny_jpeg)
    assert bytes(snapshot) == tiny_jpeg
