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


class ImageTooLarge(ValueError):
    """Decoded image exceeds the maximum pixel count (decompression-bomb guard).

    Distinct from the byte-size limits enforced at intake (25 MB upload / 20 MB
    Telegram): this is about *decoded* dimensions, which a small crafted file can
    blow up far beyond its on-disk size.
    """


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# Max decoded pixels (width × height). 100 MP sits above real phone cameras
# (iPhone ProRAW tops out at 48 MP; 108/200 MP Android sensors downscale below
# this) yet blocks decompression bombs — a tiny file that expands to a huge
# canvas — before the pixels are materialised by the PNG re-encode.
MAX_PIXELS = 100_000_000

# Decode ONLY via the loader for the detected format. Never new_from_buffer(data, "")
# — auto-detect would let libvips pick any loader (SVG/PDF via delegates) regardless
# of the magic-byte whitelist, which a polyglot could abuse.
_LOADERS = {
    "jpeg": "jpegload_buffer",
    "png": "pngload_buffer",
    "webp": "webpload_buffer",
}


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

    load = getattr(pyvips.Image, _LOADERS[source_format])
    try:
        image = load(file_bytes)
    except pyvips.Error as exc:
        raise CorruptedInput(f"failed to decode {source_format}: {exc}") from exc

    # width/height are header-only for these loaders, so this fires before the
    # PNG re-encode ever materialises the pixels — the point of the guard.
    if image.width * image.height > MAX_PIXELS:
        raise ImageTooLarge(
            f"image exceeds {MAX_PIXELS} px limit: {image.width}x{image.height}"
        )

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
