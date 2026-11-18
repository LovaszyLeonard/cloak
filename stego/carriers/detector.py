"""Carrier format detection for Cloak."""

from pathlib import Path

from ..exceptions import UnsupportedCarrierError

IMAGE_EXTENSIONS = {".png", ".bmp"}
AUDIO_EXTENSIONS = {".wav"}


def detect_carrier_type(file_path: str | Path) -> str:
    """
    Detect whether the file is an image carrier or audio carrier based on
    file extension and magic bytes. Returns 'image' or 'audio'.
    """
    path = Path(file_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Carrier file not found: {file_path}")
    if not path.is_file():
        raise UnsupportedCarrierError(f"Carrier path is a directory, not a regular file: {file_path}")

    ext = path.suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in AUDIO_EXTENSIONS:
        return "audio"

    # Fallback to inspecting initial magic bytes
    try:
        with open(path, "rb") as f:
            magic = f.read(12)
    except Exception as e:
        raise UnsupportedCarrierError(f"Cannot read carrier file: {e}") from e

    if magic.startswith(b"\x89PNG\r\n\x1a\n") or magic.startswith(b"BM"):
        return "image"
    if magic.startswith(b"RIFF") and len(magic) >= 12 and magic[8:12] == b"WAVE":
        return "audio"

    raise UnsupportedCarrierError(
        f"Unsupported carrier format for '{path.name}'. Only PNG images and WAV audio files are supported."
    )
