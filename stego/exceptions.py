"""Exception classes for Cloak steganography toolkit."""


class CloakError(Exception):
    """Base exception for all Cloak-specific errors."""

    pass


class CapacityError(CloakError, ValueError):
    """Raised when the carrier media does not have enough capacity for the payload."""

    pass


class PayloadNotFoundError(CloakError, ValueError):
    """Raised when no Cloak steganographic payload is detected in the carrier."""

    pass


class PasswordRequiredError(CloakError, ValueError):
    """Raised when an encrypted payload is encountered but no password was provided."""

    pass


class DecryptionError(CloakError, ValueError):
    """Raised when decryption fails due to an invalid password or corrupted data."""

    pass


class CorruptedPayloadError(CloakError, ValueError):
    """Raised when payload metadata indicates corrupted or truncated data."""

    pass


class UnsupportedCarrierError(CloakError, ValueError):
    """Raised when an unsupported carrier file format is provided."""

    pass
