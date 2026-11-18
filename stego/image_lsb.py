"""Backward compatibility wrapper for image carrier operations."""

from .carriers.image import (
    decode_image as decode,
)
from .carriers.image import (
    decode_image_raw,
    get_image_capacity,
)
from .carriers.image import (
    encode_image as encode,
)

__all__ = ["encode", "decode", "decode_image_raw", "get_image_capacity"]
