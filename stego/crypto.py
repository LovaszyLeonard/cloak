import os
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

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

def encrypt_message(plaintext: str, password: str) -> bytes:
    salt = os.urandom(SALT_LENGTH)
    key = derive_key(password, salt)
    nonce = os.urandom(NONCE_LENGTH)

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)

    # Pack: salt + nonce + ciphertext (GCM tag is included in ciphertext)
    return salt + nonce + ciphertext

def decrypt_message(encrypted_blob: bytes, password: str) -> str:
    salt = encrypted_blob[:SALT_LENGTH]
    nonce = encrypted_blob[SALT_LENGTH:SALT_LENGTH + NONCE_LENGTH]
    ciphertext = encrypted_blob[SALT_LENGTH + NONCE_LENGTH:]

    key = derive_key(password, salt)
    aesgcm = AESGCM(key)

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')
    except Exception:
        raise ValueError("Decryption failed – wrong password or corrupted data.")