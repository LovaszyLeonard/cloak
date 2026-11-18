"""Backward compatibility wrapper for image carrier operations."""

from .carriers.image import (
    encode_image as encode,
    decode_image as decode,
    decode_image_raw,
    get_image_capacity,
)

__all__ = ['encode', 'decode', 'decode_image_raw', 'get_image_capacity']
