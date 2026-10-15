"""Security validation and safety auditing for archives and file paths."""

import hashlib
import hmac
import os
import re
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, Any


class SecurityError(Exception):
    """Base exception for all archive security violations."""
    pass


class PathTraversalError(SecurityError):
    """Raised when an archive member or path attempts directory traversal (Zip Slip)."""
    pass


class ZipBombError(SecurityError):
    """Raised when an archive exceeds safe compression or expansion limits."""
    pass


class IntegrityError(SecurityError):
    """Raised when file integrity or checksum verification fails."""
    pass


class PermissionSecurityError(SecurityError):
    """Raised when an operation encounters forbidden or restricted permissions."""
    pass


# Characters disallowed in file names across Windows and POSIX systems
DISALLOWED_CHARS = re.compile(r'[\x00-\x1f<>:"/\\|?*]')


def sanitize_filename(name: str) -> str:
    """Sanitize a filename by removing or replacing illegal characters, null bytes, and path separators."""
    if not name:
        return "unnamed_file"
    
    # Replace illegal characters and separators with underscores
    sanitized = DISALLOWED_CHARS.sub("_", name).strip("._ ")
    return sanitized if sanitized else "unnamed_file"


def is_safe_path(base_dir: str | Path, target_path: str | Path) -> bool:
    """Check whether a target path resides strictly inside base_dir."""
    try:
        base = Path(base_dir).resolve()
        target = (base / target_path).resolve() if not Path(target_path).is_absolute() else Path(target_path).resolve()
        
        # Check if target starts with base
        try:
            target.relative_to(base)
            return True
        except ValueError:
            return False
    except (ValueError, RuntimeError):
        return False


def resolve_safe_path(base_dir: str | Path, target_path: str | Path) -> Path:
    """Resolve target_path within base_dir.
    
    Raises:
        PathTraversalError: If target_path resolves outside base_dir.
    """
    base = Path(base_dir).resolve()
    
    # Clean target string to avoid leading slashes escaping base
    clean_target = str(target_path).lstrip("/\\")
    resolved = (base / clean_target).resolve()
    
    try:
        resolved.relative_to(base)
    except ValueError:
        raise PathTraversalError(
            f"Path traversal detected: '{target_path}' attempts to escape '{base_dir}'."
        )
    return resolved


def calculate_checksum(file_path: str | Path, algorithm: str = "sha256") -> str:
    """Calculate the cryptographic hash of a file."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    algo = algorithm.lower()
    if algo not in hashlib.algorithms_available:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    hasher = hashlib.new(algo)
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_checksum(file_path: str | Path, expected_hash: str, algorithm: str = "sha256") -> bool:
    """Verify that a file's hash matches the expected hash using constant-time comparison."""
    actual = calculate_checksum(file_path, algorithm=algorithm)
    return hmac.compare_digest(actual.lower(), expected_hash.strip().lower())


def validate_archive_safety(
    archive_path: str | Path,
    max_files: int = 50_000,
    max_uncompressed_bytes: int = 1_073_741_824,  # 1 GB default limit
    max_ratio: float = 200.0,
) -> Dict[str, Any]:
    """Inspect an archive for Zip Slip, decompression bomb (zip bomb), and excessive files.
    
    Returns:
        dict: Summary of the archive structure and safety metrics.
        
    Raises:
        PathTraversalError: If any member path escapes destination root.
        ZipBombError: If limits are exceeded.
        FileNotFoundError: If the archive does not exist.
        SecurityError: For corrupted or malformed archives.
    """
    path = Path(archive_path)
    if not path.is_file():
        raise FileNotFoundError(f"Archive file not found: {archive_path}")

    compressed_size = max(path.stat().st_size, 1)
    total_uncompressed = 0
    file_count = 0
    member_names = []

    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path, "r") as zf:
            for info in zf.infolist():
                file_count += 1
                name = info.filename
                member_names.append(name)
                
                # Check for traversal indicators
                if name.startswith("/") or name.startswith("\\") or ".." in name.split("/") or ".." in name.split("\\"):
                    raise PathTraversalError(f"Malicious member path in zip: '{name}'")
                
                # Detect drive letters (e.g., C:)
                if re.match(r"^[a-zA-Z]:", name):
                    raise PathTraversalError(f"Absolute drive path in zip: '{name}'")

                total_uncompressed += info.file_size
                
                if file_count > max_files:
                    raise ZipBombError(f"Exceeded maximum file count limit ({max_files})")
                if total_uncompressed > max_uncompressed_bytes:
                    raise ZipBombError(f"Exceeded maximum uncompressed size ({max_uncompressed_bytes} bytes)")

    elif tarfile.is_tarfile(path):
        with tarfile.open(path, "r:*") as tf:
            for member in tf.getmembers():
                file_count += 1
                name = member.name
                member_names.append(name)

                # Check for traversal indicators
                if name.startswith("/") or name.startswith("\\") or ".." in name.split("/") or ".." in name.split("\\"):
                    raise PathTraversalError(f"Malicious member path in tar: '{name}'")
                if re.match(r"^[a-zA-Z]:", name):
                    raise PathTraversalError(f"Absolute drive path in tar: '{name}'")

                total_uncompressed += member.size

                if file_count > max_files:
                    raise ZipBombError(f"Exceeded maximum file count limit ({max_files})")
                if total_uncompressed > max_uncompressed_bytes:
                    raise ZipBombError(f"Exceeded maximum uncompressed size ({max_uncompressed_bytes} bytes)")
    else:
        # Not a standard zip or tar archive; return basic metrics
        return {
            "archive": str(path),
            "file_count": 0,
            "compressed_size": compressed_size,
            "uncompressed_size": compressed_size,
            "ratio": 1.0,
            "is_safe": True,
        }

    ratio = total_uncompressed / compressed_size
    # Only flag ratio if uncompressed size is substantial (> 1MB)
    if total_uncompressed > 1_048_576 and ratio > max_ratio:
        raise ZipBombError(
            f"Suspicious compression ratio ({ratio:.1f} > {max_ratio}). Potential decompression bomb."
        )

    return {
        "archive": str(path),
        "file_count": file_count,
        "compressed_size": compressed_size,
        "uncompressed_size": total_uncompressed,
        "ratio": round(ratio, 2),
        "is_safe": True,
    }
