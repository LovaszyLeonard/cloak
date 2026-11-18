"""Cloak – Modern Multi-Format Steganography Toolkit."""

from .carriers import (
    encode_carrier as encode,
    decode_carrier as decode,
    decode_carrier_to_file as decode_to_file,
    inspect_carrier as info,
    get_capacity,
    detect_carrier_type,
)
from .exceptions import (
    CloakError,
    CapacityError,
    PayloadNotFoundError,
    PasswordRequiredError,
    DecryptionError,
    CorruptedPayloadError,
    UnsupportedCarrierError,
)

__version__ = "0.2.0"

__all__ = [
    'encode',
    'decode',
    'decode_to_file',
    'info',
    'get_capacity',
    'detect_carrier_type',
    'CloakError',
    'CapacityError',
    'PayloadNotFoundError',
    'PasswordRequiredError',
    'DecryptionError',
    'CorruptedPayloadError',
    'UnsupportedCarrierError',
]
