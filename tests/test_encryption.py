"""Tests for AES-256-GCM encryption and decryption module."""

import pytest
from app.tools.encryption import (
    generate_key,
    encrypt_bytes,
    decrypt_bytes,
    encrypt_file,
    decrypt_file,
    is_encrypted_file,
    DecryptionError,
    EncryptionError,
)


def test_key_generation():
    key = generate_key()
    assert isinstance(key, str)
    assert len(key) > 30


def test_encrypt_decrypt_bytes_with_password():
    data = b"Secret data to protect with AES-256-GCM"
    password = "SuperSecretPassword123!"

    encrypted = encrypt_bytes(data, password)
    assert encrypted != data
    assert encrypted.startswith(b"SAA_ENC_v1")

    decrypted = decrypt_bytes(encrypted, password)
    assert decrypted == data


def test_encrypt_decrypt_bytes_with_generated_key():
    data = b"Confidential message using raw key"
    key = generate_key()

    encrypted = encrypt_bytes(data, key)
    decrypted = decrypt_bytes(encrypted, key)
    assert decrypted == data


def test_decrypt_with_wrong_password():
    data = b"Sensitive information"
    encrypted = encrypt_bytes(data, "correct_pass")

    with pytest.raises(DecryptionError):
        decrypt_bytes(encrypted, "wrong_pass")


def test_decrypt_corrupted_payload():
    data = b"Integrity check payload"
    encrypted = bytearray(encrypt_bytes(data, "pass"))
    # Tamper with the ciphertext/tag
    encrypted[-1] ^= 0xFF

    with pytest.raises(DecryptionError):
        decrypt_bytes(bytes(encrypted), "pass")


def test_encrypt_decrypt_file(tmp_path):
    plain_file = tmp_path / "document.txt"
    plain_file.write_text("Hello secure archive world!", encoding="utf-8")

    enc_file = encrypt_file(plain_file, password_or_key="safe_key")
    assert enc_file.exists()
    assert is_encrypted_file(enc_file)
    assert not is_encrypted_file(plain_file)

    dec_file = decrypt_file(enc_file, password_or_key="safe_key")
    assert dec_file.exists()
    assert dec_file.read_text(encoding="utf-8") == "Hello secure archive world!"
