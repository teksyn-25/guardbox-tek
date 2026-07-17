from unittest.mock import patch

import pytest

pyvips = pytest.importorskip("pyvips")

import sys

from cdr.sanitize import (
    CorruptedInput,
    ImageTooLarge,
    UnsupportedFileType,
    sanitize,
)

# The module object — NOT `import cdr.sanitize`, whose `.sanitize` attr is the
# shadowing function (cdr/__init__.py does `from .sanitize import sanitize`).
sanitize_mod = sys.modules["cdr.sanitize"]

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


# ── loader confinement ────────────────────────────────────────────────────────
# new_from_buffer(data, "") lets libvips auto-pick ANY loader (SVG/PDF via
# delegates) *after* the magic-byte check — a polyglot could be decoded as a
# non-whitelisted type. sanitize must decode via the format-specific loader only.


def test_jpeg_not_decoded_via_autodetect(tiny_jpeg):
    with patch.object(
        pyvips.Image, "new_from_buffer", side_effect=AssertionError("autodetect used")
    ):
        out, _ = sanitize(tiny_jpeg)
    assert out[:8] == _PNG_MAGIC


def test_png_not_decoded_via_autodetect(tiny_png):
    with patch.object(
        pyvips.Image, "new_from_buffer", side_effect=AssertionError("autodetect used")
    ):
        out, _ = sanitize(tiny_png)
    assert out[:8] == _PNG_MAGIC


def test_webp_not_decoded_via_autodetect(tiny_webp):
    with patch.object(
        pyvips.Image, "new_from_buffer", side_effect=AssertionError("autodetect used")
    ):
        out, _ = sanitize(tiny_webp)
    assert out[:8] == _PNG_MAGIC


def test_jpeg_decoded_by_jpeg_loader(tiny_jpeg):
    with patch.object(
        pyvips.Image, "jpegload_buffer", wraps=pyvips.Image.jpegload_buffer
    ) as spy:
        sanitize(tiny_jpeg)
    spy.assert_called_once()


# ── decompression-bomb guard ──────────────────────────────────────────────────
# MAX_PIXELS is monkeypatched down so the guard is exercised against the tiny 8×8
# fixture — no large image is ever constructed (no OOM in the test itself).


def test_oversized_image_raises_image_too_large(tiny_jpeg, monkeypatch):
    monkeypatch.setattr(sanitize_mod, "MAX_PIXELS", 10)  # 8×8 = 64 > 10
    with pytest.raises(ImageTooLarge):
        sanitize(tiny_jpeg)


def test_image_at_exact_limit_is_accepted(tiny_jpeg, monkeypatch):
    monkeypatch.setattr(sanitize_mod, "MAX_PIXELS", 64)  # 8×8 = 64, not over
    out, _ = sanitize(tiny_jpeg)
    assert out[:8] == _PNG_MAGIC


# ── invariants ────────────────────────────────────────────────────────────────


def test_original_bytes_not_mutated(tiny_jpeg):
    snapshot = bytearray(tiny_jpeg)
    sanitize(tiny_jpeg)
    assert bytes(snapshot) == tiny_jpeg


# ── package public API ────────────────────────────────────────────────────────
# The cdr package must re-export every CDR exception so callers can `from cdr
# import ImageTooLarge`. A missing re-export slips through unnoticed because the
# intake modules import from cdr.sanitize directly — this test guards that gap.


def test_cdr_package_reexports_all_exceptions():
    import cdr

    assert cdr.ImageTooLarge is sanitize_mod.ImageTooLarge
    assert cdr.CorruptedInput is sanitize_mod.CorruptedInput
    assert cdr.UnsupportedFileType is sanitize_mod.UnsupportedFileType
    assert set(cdr.__all__) >= {
        "sanitize",
        "UnsupportedFileType",
        "CorruptedInput",
        "ImageTooLarge",
    }
