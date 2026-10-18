import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"TMX1"
NONCE_SIZE = 12
KEY_SIZE = 32


def encrypt_bytes(plaintext: bytes, key: bytes) -> bytes:
    if len(key) != KEY_SIZE:
        raise ValueError("Encryption key must be 32 bytes")
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, MAGIC)
    return MAGIC + nonce + ciphertext


def decrypt_bytes(envelope: bytes, key: bytes) -> bytes:
    if len(key) != KEY_SIZE:
        raise ValueError("Encryption key must be 32 bytes")
    if not envelope.startswith(MAGIC) or len(envelope) <= len(MAGIC) + NONCE_SIZE:
        raise ValueError("Unable to decrypt invalid legacy export envelope")
    nonce_start = len(MAGIC)
    nonce_end = nonce_start + NONCE_SIZE
    try:
        return AESGCM(key).decrypt(
            envelope[nonce_start:nonce_end], envelope[nonce_end:], MAGIC
        )
    except InvalidTag as error:
        raise ValueError("Unable to decrypt legacy export with the supplied key") from error
