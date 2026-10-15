"""Archive and encryption toolset."""

from .archive import (
    create_archive,
    extract_archive,
    list_archive,
    inspect_archive,
    verify_archive,
    detect_format,
)
from .encryption import (
    generate_key,
    encrypt_bytes,
    decrypt_bytes,
    encrypt_file,
    decrypt_file,
    is_encrypted_file,
    EncryptionError,
    DecryptionError,
)

__all__ = [
    "create_archive",
    "extract_archive",
    "list_archive",
    "inspect_archive",
    "verify_archive",
    "detect_format",
    "generate_key",
    "encrypt_bytes",
    "decrypt_bytes",
    "encrypt_file",
    "decrypt_file",
    "is_encrypted_file",
    "EncryptionError",
    "DecryptionError",
]
