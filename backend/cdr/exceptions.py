"""CDR exception types, kept dependency-free so importing them never pulls in pyvips."""


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
