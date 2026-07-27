import io

import pytest

from cdr.wire import WireError, encode_error, encode_success, read_message


def _stream(data: bytes) -> io.BytesIO:
    return io.BytesIO(data)


# ── success round-trip ─────────────────────────────────────────────────────


def test_success_round_trip_carries_report_and_bytes():
    report = {"source_format": "jpeg", "stripped": ["EXIF"], "output_format": "png", "dimensions": [8, 8]}
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"fake-png-data"

    encoded = encode_success(report, png_bytes)
    decoded = read_message(_stream(encoded))

    assert decoded["status"] == "ok"
    assert decoded["report"] == report
    assert decoded["png_bytes"] == png_bytes


def test_success_with_empty_png_bytes():
    decoded = read_message(_stream(encode_success({"a": 1}, b"")))
    assert decoded["png_bytes"] == b""


# ── error round-trip ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "error_type",
    ["UnsupportedFileType", "CorruptedInput", "ImageTooLarge", "InternalError", "OrchestratorError"],
)
def test_error_round_trip_each_known_type(error_type):
    encoded = encode_error(error_type, "something went wrong")
    decoded = read_message(_stream(encoded))

    assert decoded["status"] == "error"
    assert decoded["error_type"] == error_type
    assert decoded["message"] == "something went wrong"
    assert "png_bytes" not in decoded


def test_error_message_with_unicode():
    encoded = encode_error("CorruptedInput", "bad byte: ☃")
    decoded = read_message(_stream(encoded))
    assert decoded["message"] == "bad byte: ☃"


# ── malformed / truncated streams ───────────────────────────────────────────


def test_truncated_header_length_prefix_raises():
    with pytest.raises(WireError, match="truncated"):
        read_message(_stream(b"\x00\x00"))


def test_truncated_header_body_raises():
    encoded = encode_success({"a": 1}, b"payload")
    # Cut partway through the JSON header.
    truncated = encoded[:6]
    with pytest.raises(WireError, match="truncated"):
        read_message(_stream(truncated))


def test_truncated_png_payload_raises():
    encoded = encode_success({"a": 1}, b"0123456789")
    truncated = encoded[:-5]  # header intact, PNG payload cut short
    with pytest.raises(WireError, match="truncated"):
        read_message(_stream(truncated))


def test_malformed_json_header_raises():
    bad_header = b"{not valid json"
    length_prefix = len(bad_header).to_bytes(4, "big")
    with pytest.raises(WireError, match="malformed header JSON"):
        read_message(_stream(length_prefix + bad_header))


def test_header_missing_status_field_raises():
    length_prefix = (2).to_bytes(4, "big")
    with pytest.raises(WireError, match="status"):
        read_message(_stream(length_prefix + b"{}"))


def test_success_header_missing_png_length_raises():
    length_prefix = (16).to_bytes(4, "big")
    header = b'{"status": "ok"}'
    assert len(header) == 16
    with pytest.raises(WireError, match="png_length"):
        read_message(_stream(length_prefix + header))


def test_empty_stream_raises():
    with pytest.raises(WireError, match="truncated"):
        read_message(_stream(b""))
