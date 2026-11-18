"""Cloak – Modern Multi-Format Steganography Toolkit."""

from .carriers import (
    decode_carrier as decode,
)
from .carriers import (
    decode_carrier_to_file as decode_to_file,
)
from .carriers import (
    detect_carrier_type,
    get_capacity,
)
from .carriers import (
    encode_carrier as encode,
)
from .carriers import (
    inspect_carrier as info,
)
from .exceptions import (
    CapacityError,
    CloakError,
    CorruptedPayloadError,
    DecryptionError,
    PasswordRequiredError,
    PayloadNotFoundError,
    UnsupportedCarrierError,
)

__version__ = "0.2.0"

__all__ = [
    "encode",
    "decode",
    "decode_to_file",
    "info",
    "get_capacity",
    "detect_carrier_type",
    "CloakError",
    "CapacityError",
    "PayloadNotFoundError",
    "PasswordRequiredError",
    "DecryptionError",
    "CorruptedPayloadError",
    "UnsupportedCarrierError",
]
