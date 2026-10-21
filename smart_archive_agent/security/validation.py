from __future__ import annotations
from pathlib import Path
import os

class ValidationError(ValueError):
    """Raised when a user-supplied path or operation is unsafe."""

def resolve_existing_path(raw_path: str) -> Path:
    if not raw_path or not raw_path.strip():
        raise ValidationError("Please provide a file or directory path.")
    path = Path(os.path.expanduser(raw_path.strip())).resolve()
    if not path.exists():
        raise ValidationError(f"Path does not exist: {path}")
    return path

def resolve_output_path(raw_path: str) -> Path:
    if not raw_path or not raw_path.strip():
        raise ValidationError("Please provide an output path.")
    path = Path(os.path.expanduser(raw_path.strip())).resolve()
    if not path.parent.exists():
        raise ValidationError(f"Output directory does not exist: {path.parent}")
    from smart_archive_agent.security.guardrails import PROTECTED_DIRS
    if any(str(path) == d or str(path).startswith(d + "/") for d in PROTECTED_DIRS):
        raise ValidationError(f"Refusing to write into a protected system location: {path}")
    return path

def reject_same_path(source: Path, output: Path) -> None:
    if source.resolve() == output.resolve():
        raise ValidationError("The output path must differ from the source path.")

def calculate_checksum(file_path: Path | str, algorithm: str = "sha256") -> str:
    """Calculate cryptographic hash of a file for integrity auditing."""
    path = Path(os.path.expanduser(str(file_path))).resolve()
    if not path.is_file():
        raise ValidationError(f"Cannot calculate checksum: not a file: {path}")
    import hashlib
    hasher = hashlib.new(algorithm.lower())
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

