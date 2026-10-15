"""Cryptographic encryption and decryption tools for archives and files."""

import base64
import os
from pathlib import Path
from typing import Union

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

MAGIC_HEADER = b"SAA_ENC_v1"
SALT_SIZE = 16
NONCE_SIZE = 12
PBKDF2_ITERATIONS = 100_000


class EncryptionError(Exception):
    """Base exception for encryption operations."""
    pass


class DecryptionError(Exception):
    """Raised when decryption or integrity verification fails."""
    pass


def generate_key() -> str:
    """Generate a cryptographically secure URL-safe 256-bit key string."""
    raw_key = AESGCM.generate_key(bit_length=256)
    return base64.urlsafe_b64encode(raw_key).decode("utf-8")


def _resolve_key(key_or_password: Union[str, bytes], salt: bytes) -> bytes:
    """Derive or parse a 256-bit key from either a raw key or password."""
    if isinstance(key_or_password, str):
        key_bytes = key_or_password.encode("utf-8")
    else:
        key_bytes = key_or_password

    # Check if input is a valid 32-byte base64 key
    try:
        decoded = base64.urlsafe_b64decode(key_bytes)
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass

    # If raw 32 bytes provided
    if len(key_bytes) == 32 and not isinstance(key_or_password, str):
        return key_bytes

    # Otherwise derive 256-bit key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(key_bytes)


def encrypt_bytes(data: bytes, key_or_password: Union[str, bytes]) -> bytes:
    """Encrypt raw bytes using AES-256-GCM authenticated encryption."""
    if not key_or_password:
        raise EncryptionError("Encryption key or password must be provided.")

    salt = os.urandom(SALT_SIZE)
    key = _resolve_key(key_or_password, salt)
    nonce = os.urandom(NONCE_SIZE)

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, associated_data=MAGIC_HEADER)
    
    # Payload format: MAGIC (10) + SALT (16) + NONCE (12) + CIPHERTEXT
    return MAGIC_HEADER + salt + nonce + ciphertext


def decrypt_bytes(payload: bytes, key_or_password: Union[str, bytes]) -> bytes:
    """Decrypt and verify ciphertext payload using AES-256-GCM."""
    if not key_or_password:
        raise DecryptionError("Decryption key or password must be provided.")

    if not payload.startswith(MAGIC_HEADER):
        raise DecryptionError("Invalid archive payload: Missing SAA encryption header.")

    header_len = len(MAGIC_HEADER)
    if len(payload) < header_len + SALT_SIZE + NONCE_SIZE + 16:
        raise DecryptionError("Corrupted payload: Insufficient data length.")

    salt_offset = header_len
    nonce_offset = salt_offset + SALT_SIZE
    ct_offset = nonce_offset + NONCE_SIZE

    salt = payload[salt_offset:nonce_offset]
    nonce = payload[nonce_offset:ct_offset]
    ciphertext = payload[ct_offset:]

    key = _resolve_key(key_or_password, salt)
    aesgcm = AESGCM(key)

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=MAGIC_HEADER)
        return plaintext
    except InvalidTag:
        raise DecryptionError("Decryption failed: Incorrect password/key or corrupted data.")
    except Exception as exc:
        raise DecryptionError(f"Decryption error: {str(exc)}") from exc


def encrypt_file(
    src_path: Union[str, Path],
    dest_path: Union[str, Path, None] = None,
    password_or_key: Union[str, bytes] = "",
) -> Path:
    """Encrypt an entire file and write to dest_path (defaults to src_path.enc)."""
    src = Path(src_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Source file not found: {src_path}")

    if dest_path is None:
        dest = src.with_name(src.name + ".enc")
    else:
        dest = Path(dest_path).resolve()

    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(src, "rb") as f_in:
        content = f_in.read()

    encrypted = encrypt_bytes(content, password_or_key)

    with open(dest, "wb") as f_out:
        f_out.write(encrypted)

    return dest


def decrypt_file(
    src_path: Union[str, Path],
    dest_path: Union[str, Path, None] = None,
    password_or_key: Union[str, bytes] = "",
) -> Path:
    """Decrypt an encrypted file and write to dest_path."""
    src = Path(src_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Source encrypted file not found: {src_path}")

    if dest_path is None:
        if src.suffix == ".enc":
            dest = src.with_suffix("")
        else:
            dest = src.with_name(f"{src.stem}_decrypted{src.suffix}")
    else:
        dest = Path(dest_path).resolve()

    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(src, "rb") as f_in:
        content = f_in.read()

    decrypted = decrypt_bytes(content, password_or_key)

    with open(dest, "wb") as f_out:
        f_out.write(decrypted)

    return dest


def is_encrypted_file(file_path: Union[str, Path]) -> bool:
    """Determine if a given file has the SAA encryption magic header."""
    path = Path(file_path)
    if not path.is_file():
        return False
    try:
        with open(path, "rb") as f:
            header = f.read(len(MAGIC_HEADER))
            return header == MAGIC_HEADER
    except Exception:
        return False
