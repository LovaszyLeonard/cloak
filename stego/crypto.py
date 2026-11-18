import os
from typing import Union
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .exceptions import DecryptionError

SALT_LENGTH = 16      # bytes
NONCE_LENGTH = 12     # bytes (AES‑GCM standard)
KEY_LENGTH = 32       # bytes (AES‑256)
PBKDF2_ITERATIONS = 600_000  # recommended minimum for security

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode('utf-8'))

def encrypt_bytes(data: bytes, password: str) -> bytes:
    """Encrypt raw bytes using AES-256-GCM with PBKDF2 key derivation."""
    salt = os.urandom(SALT_LENGTH)
    key = derive_key(password, salt)
    nonce = os.urandom(NONCE_LENGTH)

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, None)

    # Pack: salt + nonce + ciphertext (GCM tag is appended by cryptography AEAD)
    return salt + nonce + ciphertext

def decrypt_bytes(encrypted_blob: bytes, password: str) -> bytes:
    """Decrypt raw bytes using AES-256-GCM with PBKDF2 key derivation."""
    if len(encrypted_blob) < SALT_LENGTH + NONCE_LENGTH + 16:
        raise DecryptionError("Encrypted payload is too short or corrupted.")

    salt = encrypted_blob[:SALT_LENGTH]
    nonce = encrypted_blob[SALT_LENGTH:SALT_LENGTH + NONCE_LENGTH]
    ciphertext = encrypted_blob[SALT_LENGTH + NONCE_LENGTH:]

    key = derive_key(password, salt)
    aesgcm = AESGCM(key)

    try:
        return aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        raise DecryptionError("Decryption failed – wrong password or corrupted data.") from e

def encrypt_message(plaintext: Union[str, bytes], password: str) -> bytes:
    """Encrypt string message or bytes (backward compatible)."""
    data = plaintext.encode('utf-8') if isinstance(plaintext, str) else plaintext
    return encrypt_bytes(data, password)

def decrypt_message(encrypted_blob: bytes, password: str) -> str:
    """Decrypt to UTF-8 string (backward compatible)."""
    raw = decrypt_bytes(encrypted_blob, password)
    return raw.decode('utf-8')
