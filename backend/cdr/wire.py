"""Framing protocol shared by both hops of the sandboxed CDR pipeline:
api <-> orchestrator (over a Unix domain socket) and orchestrator <-> parser
(over a container's stdin/stdout). Both hops carry the same two pieces of
data - a JSON report and, on success, raw PNG bytes - over a single byte
stream, so one encode/decode implementation covers both.

Wire format:
    [4 bytes big-endian uint32: header length N]
    [N bytes UTF-8 JSON header]
    [iff header["status"] == "ok": exactly header["png_length"] raw PNG bytes]

Success header: {"status": "ok", "report": {...}, "png_length": <int>}
Error header:   {"status": "error", "error_type": "<str>", "message": "<str>"}
"""

import json
import struct

_HEADER_LEN_FMT = ">I"
_HEADER_LEN_SIZE = struct.calcsize(_HEADER_LEN_FMT)


class WireError(Exception):
    """The stream was truncated or contained a malformed header."""


def encode_success(report: dict, png_bytes: bytes) -> bytes:
    header = {"status": "ok", "report": report, "png_length": len(png_bytes)}
    return _encode(header) + png_bytes


def encode_error(error_type: str, message: str) -> bytes:
    header = {"status": "error", "error_type": error_type, "message": message}
    return _encode(header)


def _encode(header: dict) -> bytes:
    header_bytes = json.dumps(header).encode("utf-8")
    return struct.pack(_HEADER_LEN_FMT, len(header_bytes)) + header_bytes


def read_message(stream) -> dict:
    """Read one framed message from `stream` (anything with a blocking,
    EOF-respecting `.read(n)` - a subprocess's stdout or a socket's makefile).

    Returns the header dict; on success it also contains "png_bytes" (the
    raw PNG payload). Raises WireError on truncation or malformed JSON.
    """
    length_bytes = _read_exact(stream, _HEADER_LEN_SIZE)
    (header_len,) = struct.unpack(_HEADER_LEN_FMT, length_bytes)

    header_bytes = _read_exact(stream, header_len)
    try:
        header = json.loads(header_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WireError(f"malformed header JSON: {exc}") from exc

    if not isinstance(header, dict) or "status" not in header:
        raise WireError("header missing required 'status' field")

    if header["status"] == "ok":
        png_length = header.get("png_length")
        if not isinstance(png_length, int) or png_length < 0:
            raise WireError("success header missing valid 'png_length'")
        header["png_bytes"] = _read_exact(stream, png_length)

    return header


def _read_exact(stream, n: int) -> bytes:
    data = stream.read(n)
    if data is None or len(data) != n:
        got = 0 if data is None else len(data)
        raise WireError(f"truncated stream: expected {n} bytes, got {got}")
    return data
