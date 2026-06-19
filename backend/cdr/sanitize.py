"""
CDR core: identify from magic bytes → decode in-memory → strip metadata → re-encode as PNG.

The original bytes are never written to disk. The sandbox (build step 8) constrains
where this process runs; this module is pure Python + pyvips glue.
Output is always PNG. Only whitelisted pixel content survives — metadata does not.
"""

import pyvips


class UnsupportedFileType(ValueError):
    """Magic bytes don't match any supported image format."""


class CorruptedInput(ValueError):
    """Format recognised from magic bytes but pyvips failed to decode it."""


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _detect_format(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    raise UnsupportedFileType(f"unrecognised file type (magic: {data[:12]!r})")


def _stripped_categories(fields: list[str]) -> list[str]:
    cats = []
    has_gps = any("gps" in f.lower() for f in fields)
    has_exif = any(f.startswith("exif-") for f in fields)
    if has_gps:
        cats.append("GPS")
    if has_exif:
        cats.append("EXIF")
    if "xmp-xml" in fields:
        cats.append("XMP")
    return cats


def sanitize(file_bytes: bytes) -> tuple[bytes, dict]:
    """
    CDR-sanitise image bytes.

    Returns (clean_png_bytes, report) where report = {
        "source_format": "jpeg" | "png" | "webp",
        "stripped": list of metadata categories removed,
        "output_format": "png",
        "dimensions": [width, height],
    }

    Raises UnsupportedFileType or CorruptedInput.
    """
    source_format = _detect_format(file_bytes)

    try:
        image = pyvips.Image.new_from_buffer(file_bytes, "")
    except pyvips.Error as exc:
        raise CorruptedInput(f"failed to decode {source_format}: {exc}") from exc

    stripped = _stripped_categories(image.get_fields())

    try:
        # strip=True removes EXIF, XMP, IPTC; ICC kept for correct colour reproduction
        clean_bytes = image.write_to_buffer(".png", strip=True)
    except pyvips.Error as exc:
        raise CorruptedInput(f"failed to re-encode as PNG: {exc}") from exc

    return clean_bytes, {
        "source_format": source_format,
        "stripped": stripped,
        "output_format": "png",
        "dimensions": [image.width, image.height],
    }
