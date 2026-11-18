"""Unified carrier registry and high-level steganography functions."""

from pathlib import Path

from .audio import decode_audio, decode_audio_raw, encode_audio, get_audio_capacity, inspect_audio
from .detector import detect_carrier_type
from .image import decode_image, decode_image_raw, encode_image, get_image_capacity, inspect_image


def inspect_carrier(carrier_path: str | Path) -> dict:
    """Auto-detect carrier and inspect its metadata, capacity, and payload status."""
    carrier_type = detect_carrier_type(carrier_path)
    if carrier_type == "image":
        info = inspect_image(carrier_path)
    elif carrier_type == "audio":
        info = inspect_audio(carrier_path)
    else:
        raise ValueError(f"Unknown carrier type: {carrier_type}")

    info["file_path"] = str(Path(carrier_path).resolve())
    return info


def get_capacity(carrier_path: str | Path) -> int:
    """Get maximum embeddable payload capacity in bytes for any supported carrier."""
    carrier_type = detect_carrier_type(carrier_path)
    if carrier_type == "image":
        return get_image_capacity(carrier_path)
    elif carrier_type == "audio":
        return get_audio_capacity(carrier_path)
    raise ValueError(f"Unknown carrier type: {carrier_type}")


def encode_carrier(
    carrier_path: str | Path,
    message: str | bytes,
    output_path: str | Path,
    password: str | None = None,
    is_binary: bool = False,
    scatter: bool = False,
    compress: bool = True,
) -> None:
    """Auto-detect carrier format and embed payload."""
    carrier_type = detect_carrier_type(carrier_path)
    if carrier_type == "image":
        encode_image(
            carrier_path,
            message,
            output_path,
            password,
            is_binary=is_binary,
            scatter=scatter,
            compress=compress,
        )
    elif carrier_type == "audio":
        encode_audio(
            carrier_path,
            message,
            output_path,
            password,
            is_binary=is_binary,
            scatter=scatter,
            compress=compress,
        )
    else:
        raise ValueError(f"Unknown carrier type: {carrier_type}")


def decode_carrier_raw(
    carrier_path: str | Path,
    password: str | None = None,
) -> tuple[int, bytes]:
    """Auto-detect carrier format and extract raw payload bytes."""
    carrier_type = detect_carrier_type(carrier_path)
    if carrier_type == "image":
        return decode_image_raw(carrier_path, password)
    elif carrier_type == "audio":
        return decode_audio_raw(carrier_path, password)
    else:
        raise ValueError(f"Unknown carrier type: {carrier_type}")


def decode_carrier(
    carrier_path: str | Path,
    password: str | None = None,
) -> str:
    """Auto-detect carrier format and extract decrypted string message."""
    carrier_type = detect_carrier_type(carrier_path)
    if carrier_type == "image":
        return decode_image(carrier_path, password)
    elif carrier_type == "audio":
        return decode_audio(carrier_path, password)
    else:
        raise ValueError(f"Unknown carrier type: {carrier_type}")


def decode_carrier_to_file(
    carrier_path: str | Path,
    output_file: str | Path,
    password: str | None = None,
) -> int:
    """Extract payload bytes and write directly to an output file. Returns written byte count."""
    _, payload_bytes = decode_carrier_raw(carrier_path, password)
    dest = Path(output_file).expanduser()
    if dest.is_dir():
        raise ValueError(f"Destination path '{output_file}' is an existing directory, not a file.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(payload_bytes)
    return len(payload_bytes)


__all__ = [
    "detect_carrier_type",
    "get_capacity",
    "inspect_carrier",
    "encode_carrier",
    "decode_carrier",
    "decode_carrier_raw",
    "decode_carrier_to_file",
    "encode_image",
    "decode_image",
    "decode_image_raw",
    "get_image_capacity",
    "inspect_image",
    "encode_audio",
    "decode_audio",
    "decode_audio_raw",
    "get_audio_capacity",
    "inspect_audio",
]
