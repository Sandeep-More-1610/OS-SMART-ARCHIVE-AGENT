"""Tests for security validation module."""

import zipfile
import pytest
from pathlib import Path
from app.security.validation import (
    is_safe_path,
    resolve_safe_path,
    sanitize_filename,
    calculate_checksum,
    verify_checksum,
    validate_archive_safety,
    PathTraversalError,
    ZipBombError,
)


def test_sanitize_filename():
    assert sanitize_filename("normal_file.txt") == "normal_file.txt"
    assert sanitize_filename("bad:file/name?.txt") == "bad_file_name_.txt"
    assert sanitize_filename("../../../etc/passwd") == "etc_passwd"
    assert sanitize_filename("") == "unnamed_file"


def test_is_safe_path(tmp_path):
    base = tmp_path / "base"
    base.mkdir()

    assert is_safe_path(base, "file.txt")
    assert is_safe_path(base, "sub/dir/file.txt")
    assert not is_safe_path(base, "../outside.txt")
    assert not is_safe_path(base, "../../root.txt")


def test_resolve_safe_path(tmp_path):
    base = tmp_path / "base"
    base.mkdir()

    resolved = resolve_safe_path(base, "valid.txt")
    assert resolved == (base / "valid.txt").resolve()

    with pytest.raises(PathTraversalError):
        resolve_safe_path(base, "../evil.txt")


def test_checksum_verification(tmp_path):
    test_file = tmp_path / "sample.txt"
    test_file.write_text("Integrity validation test content", encoding="utf-8")

    digest = calculate_checksum(test_file)
    assert len(digest) == 64
    assert verify_checksum(test_file, digest)
    assert not verify_checksum(test_file, "0" * 64)


def test_validate_safe_zip(tmp_path):
    zip_path = tmp_path / "safe.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("test1.txt", "data 1")
        zf.writestr("test2.txt", "data 2")

    result = validate_archive_safety(zip_path)
    assert result["is_safe"] is True
    assert result["file_count"] == 2


def test_zip_slip_detection(tmp_path):
    malicious_zip = tmp_path / "slip.zip"
    with zipfile.ZipFile(malicious_zip, "w") as zf:
        zf.writestr("../escaped.txt", "malicious payload")

    with pytest.raises(PathTraversalError):
        validate_archive_safety(malicious_zip)


def test_zip_bomb_file_count_limit(tmp_path):
    bomb_zip = tmp_path / "bomb.zip"
    with zipfile.ZipFile(bomb_zip, "w") as zf:
        for i in range(15):
            zf.writestr(f"f_{i}.txt", "data")

    # Limit to max 10 files
    with pytest.raises(ZipBombError):
        validate_archive_safety(bomb_zip, max_files=10)
