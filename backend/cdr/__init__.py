from .exceptions import CorruptedInput, ImageTooLarge, UnsupportedFileType

__all__ = ["sanitize", "UnsupportedFileType", "CorruptedInput", "ImageTooLarge"]


def __getattr__(name):
    if name == "sanitize":
        from .sanitize import sanitize

        return sanitize
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
