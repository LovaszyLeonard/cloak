"""PNG image carrier implementation using zero-copy bitwise LSB steganography."""

import zlib
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
from PIL import Image, UnidentifiedImageError

from ..crypto import encrypt_bytes, decrypt_bytes
from ..envelope import (
    pack_envelope,
    unpack_envelope,
    peek_envelope,
    embed_bits,
    embed_bits_scattered,
    derive_scatter_seed,
    FLAG_ENCRYPTED,
    FLAG_BINARY,
    FLAG_COMPRESSED,
    FLAG_SCATTERED,
    HEADER_SIZE,
)
from ..exceptions import (
    CapacityError,
    PasswordRequiredError,
    CorruptedPayloadError,
    UnsupportedCarrierError,
)

LOSSY_EXTENSIONS = {'.jpg', '.jpeg', '.webp'}


def _open_image_safely(image_path: Union[str, Path]) -> Image.Image:
    """Open image file with descriptive error handling for corrupted or unreadable images."""
    path = Path(image_path).expanduser()
    try:
        return Image.open(path)
    except (UnidentifiedImageError, OSError) as e:
        raise UnsupportedCarrierError(
            f"'{path.name}' is not a valid or readable image file: {e}"
        ) from e


def get_image_capacity(image_path: Union[str, Path]) -> int:
    """Return maximum payload capacity in bytes for the given image."""
    with _open_image_safely(image_path) as img:
        width, height = img.size
    total_bytes = width * height * 3  # RGB channels
    available_payload_bytes = (total_bytes // 8) - HEADER_SIZE
    return max(0, available_payload_bytes)


def inspect_image(image_path: Union[str, Path]) -> Dict:
    """Inspect image properties, steganographic capacity, and detect Cloak payloads."""
    path = Path(image_path).expanduser()
    file_size = path.stat().st_size

    with _open_image_safely(path) as img:
        width, height = img.size
        img_format = img.format or "PNG"
        img_mode = img.mode

    total_carrier_elements = width * height * 3
    total_capacity_bytes = total_carrier_elements // 8
    max_payload_bytes = max(0, total_capacity_bytes - HEADER_SIZE)

    # Peek envelope from the first pixels without loading full uncompressed image if possible
    with _open_image_safely(path) as img:
        rgb_img = img.convert('RGB')
        raw_sample = rgb_img.tobytes()[: HEADER_SIZE * 8]
    envelope_info = peek_envelope(raw_sample, total_capacity_bytes=total_capacity_bytes, stride=1)

    return {
        "carrier_type": "image",
        "format": img_format,
        "mode": img_mode,
        "width": width,
        "height": height,
        "file_size": file_size,
        "capacity_bytes": max_payload_bytes,
        "envelope": envelope_info,
    }


def encode_image(
    image_path: Union[str, Path],
    message: Union[str, bytes],
    output_path: Union[str, Path],
    password: Optional[str] = None,
    is_binary: bool = False,
    scatter: bool = False,
    compress: bool = True,
) -> None:
    """Embed payload into RGB channels of a PNG image."""
    out_p = Path(output_path).expanduser()
    if out_p.suffix.lower() in LOSSY_EXTENSIONS:
        raise ValueError(
            f"Cannot save steganographic carrier as lossy format '{out_p.suffix}'. "
            "Lossy compression destroys embedded payloads. Please use .png or .bmp."
        )

    if out_p.parent:
        out_p.parent.mkdir(parents=True, exist_ok=True)

    with _open_image_safely(image_path) as img:
        rgb_img = img.convert('RGB')
        img_size = rgb_img.size
        raw_bytes = bytearray(rgb_img.tobytes())

    max_payload = (len(raw_bytes) // 8) - HEADER_SIZE

    if isinstance(message, str):
        payload_bytes = message.encode('utf-8')
    else:
        payload_bytes = bytes(message)
        is_binary = True

    # Transparent compression before encryption
    is_compressed = False
    if compress and len(payload_bytes) > 0:
        compressed_candidate = zlib.compress(payload_bytes, level=6)
        if len(compressed_candidate) < len(payload_bytes):
            payload_bytes = compressed_candidate
            is_compressed = True

    is_encrypted = bool(password)
    if is_encrypted:
        payload_bytes = encrypt_bytes(payload_bytes, password)

    if len(payload_bytes) > max_payload:
        raise CapacityError(
            f"Payload too large! Need {len(payload_bytes)} bytes (+{HEADER_SIZE}b envelope), "
            f"but image can only hold {max_payload} bytes."
        )

    envelope = pack_envelope(
        payload_bytes,
        is_encrypted=is_encrypted,
        is_binary=is_binary,
        is_compressed=is_compressed,
        is_scattered=scatter,
    )

    if scatter:
        # Embed fixed 9-byte header at indices 0..71
        embed_bits(raw_bytes, envelope[:HEADER_SIZE], stride=1)
        # Embed payload bits scattered across the remaining carrier elements
        seed = derive_scatter_seed(password)
        embed_bits_scattered(
            raw_bytes,
            envelope[HEADER_SIZE:],
            seed=seed,
            total_elements=len(raw_bytes),
            stride=1,
        )
    else:
        embed_bits(raw_bytes, envelope, stride=1)

    new_img = Image.frombytes('RGB', img_size, bytes(raw_bytes))
    new_img.save(str(out_p), 'PNG')


def decode_image_raw(
    image_path: Union[str, Path],
    password: Optional[str] = None,
) -> Tuple[int, bytes]:
    """Extract and decrypt raw payload bytes from an image."""
    with _open_image_safely(image_path) as img:
        rgb_img = img.convert('RGB')
        raw_bytes = rgb_img.tobytes()

    total_capacity_bytes = len(raw_bytes) // 8

    flags, payload_bytes = unpack_envelope(
        raw_bytes,
        total_capacity_bytes=total_capacity_bytes,
        stride=1,
        password=password,
    )

    if flags & FLAG_ENCRYPTED:
        if not password:
            raise PasswordRequiredError("Carrier contains an encrypted payload. A password is required.")
        payload_bytes = decrypt_bytes(payload_bytes, password)

    if flags & FLAG_COMPRESSED:
        try:
            payload_bytes = zlib.decompress(payload_bytes)
        except Exception as e:
            raise CorruptedPayloadError("Failed to decompress payload data.") from e

    return flags, payload_bytes


def decode_image(
    image_path: Union[str, Path],
    password: Optional[str] = None,
) -> str:
    """Extract and decrypt text message from an image."""
    flags, payload_bytes = decode_image_raw(image_path, password)
    try:
        return payload_bytes.decode('utf-8')
    except UnicodeDecodeError as e:
        if flags & FLAG_BINARY:
            raise ValueError("Payload contains binary data. Use -O / --output-file to save to disk.") from e
        raise ValueError("Decoded payload is not valid UTF-8 text.") from e
