"""Archive manipulation tools: create, extract, list, filter, and verify archives."""

import fnmatch
import os
import shutil
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union, Any

from app.security.validation import (
    resolve_safe_path,
    validate_archive_safety,
    PathTraversalError,
    SecurityError,
)

DEFAULT_EXCLUDES = [
    ".git",
    ".git/*",
    "*/.git/*",
    "__pycache__",
    "*__pycache__*",
    "*.pyc",
    ".DS_Store",
    "Thumbs.db",
]


def detect_format(archive_path: Union[str, Path]) -> str:
    """Infer archive format from filename extensions."""
    name = str(archive_path).lower()
    if name.endswith((".tar.gz", ".tgz")):
        return "tar.gz"
    elif name.endswith((".tar.bz2", ".tbz2")):
        return "tar.bz2"
    elif name.endswith((".tar.xz", ".txz")):
        return "tar.xz"
    elif name.endswith(".tar"):
        return "tar"
    elif name.endswith(".zip"):
        return "zip"
    return "zip"


def _should_include_file(
    file_path: Path,
    relative_path: str,
    filter_criteria: Optional[Dict[str, Any]] = None,
) -> bool:
    """Evaluate whether a file should be included based on filters."""
    # Check default exclusion patterns
    norm_rel = relative_path.replace("\\", "/")
    for exc in DEFAULT_EXCLUDES:
        if fnmatch.fnmatch(norm_rel, exc) or fnmatch.fnmatch(os.path.basename(norm_rel), exc):
            return False

    if not filter_criteria:
        return True

    # Check custom exclude patterns
    for exc in filter_criteria.get("exclude_patterns", []):
        if fnmatch.fnmatch(norm_rel, exc) or fnmatch.fnmatch(os.path.basename(norm_rel), exc):
            return False

    # Check custom include patterns
    include_patterns = filter_criteria.get("patterns", [])
    if include_patterns:
        matched = any(
            fnmatch.fnmatch(norm_rel, pat) or fnmatch.fnmatch(os.path.basename(norm_rel), pat)
            for pat in include_patterns
        )
        if not matched:
            return False

    # Check extension include/exclude
    inc_exts = [e.lower() for e in filter_criteria.get("include_extensions", [])]
    if inc_exts and file_path.suffix.lower() not in inc_exts:
        return False

    exc_exts = [e.lower() for e in filter_criteria.get("exclude_extensions", [])]
    if exc_exts and file_path.suffix.lower() in exc_exts:
        return False

    # Check size constraints
    try:
        stat = file_path.stat()
        min_size = filter_criteria.get("min_size_bytes")
        if min_size is not None and stat.st_size < min_size:
            return False

        max_size = filter_criteria.get("max_size_bytes")
        if max_size is not None and stat.st_size > max_size:
            return False

        # Check modification time
        mtime = stat.st_mtime
        mod_after = filter_criteria.get("modified_after")
        if mod_after is not None:
            ts_after = mod_after.timestamp() if isinstance(mod_after, datetime) else float(mod_after)
            if mtime < ts_after:
                return False

        mod_before = filter_criteria.get("modified_before")
        if mod_before is not None:
            ts_before = mod_before.timestamp() if isinstance(mod_before, datetime) else float(mod_before)
            if mtime > ts_before:
                return False
    except OSError:
        return False

    return True


def create_archive(
    sources: Union[List[Union[str, Path]], Union[str, Path]],
    dest_path: Union[str, Path],
    format: Optional[str] = None,
    compression_level: int = 6,
    filter_criteria: Optional[Dict[str, Any]] = None,
) -> Path:
    """Create a compressed archive (.zip, .tar, .tar.gz, .tar.bz2, .tar.xz) from source paths."""
    if isinstance(sources, (str, Path)):
        sources = [sources]

    dest = Path(dest_path).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    archive_fmt = format.lower() if format else detect_format(dest)

    # Collect all (absolute_path, arcname) tuples
    files_to_add = []
    for src_raw in sources:
        src = Path(src_raw).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Source path does not exist: {src_raw}")

        if src.is_file():
            if _should_include_file(src, src.name, filter_criteria):
                files_to_add.append((src, src.name))
        elif src.is_dir():
            for root, _, files in os.walk(src):
                root_path = Path(root)
                for file_name in files:
                    full_file = root_path / file_name
                    rel_to_src = full_file.relative_to(src.parent)
                    if _should_include_file(full_file, str(rel_to_src), filter_criteria):
                        files_to_add.append((full_file, str(rel_to_src)))

    if archive_fmt == "zip":
        with zipfile.ZipFile(
            dest,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=compression_level,
        ) as zf:
            for full_file, arcname in files_to_add:
                zf.write(full_file, arcname=arcname)

    elif archive_fmt in ("tar", "tar.gz", "tar.bz2", "tar.xz"):
        mode_map = {
            "tar": "w:",
            "tar.gz": "w:gz",
            "tar.bz2": "w:bz2",
            "tar.xz": "w:xz",
        }
        tar_mode = mode_map[archive_fmt]
        with tarfile.open(dest, tar_mode) as tf:
            for full_file, arcname in files_to_add:
                tf.add(full_file, arcname=arcname)
    else:
        raise ValueError(f"Unsupported archive format: {archive_fmt}")

    return dest


def extract_archive(
    archive_path: Union[str, Path],
    dest_dir: Union[str, Path],
    safe: bool = True,
    members: Optional[List[str]] = None,
) -> List[Path]:
    """Safely extract archive contents into dest_dir preventing Zip Slip vulnerabilities."""
    archive = Path(archive_path).resolve()
    target_dir = Path(dest_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    if safe:
        # Pre-validate archive structure, decompression bomb limits, traversal attacks
        validate_archive_safety(archive)

    extracted_paths: List[Path] = []

    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive, "r") as zf:
            infolist = zf.infolist()
            for info in infolist:
                if members and info.filename not in members:
                    continue

                # Validate safe destination path
                dest_file = resolve_safe_path(target_dir, info.filename)

                if info.is_dir():
                    dest_file.mkdir(parents=True, exist_ok=True)
                else:
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as src_f, open(dest_file, "wb") as out_f:
                        shutil.copyfileobj(src_f, out_f)
                    extracted_paths.append(dest_file)

    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive, "r:*") as tf:
            tar_members = tf.getmembers()
            for member in tar_members:
                if members and member.name not in members:
                    continue

                dest_file = resolve_safe_path(target_dir, member.name)

                if member.isdir():
                    dest_file.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    f_obj = tf.extractfile(member)
                    if f_obj is not None:
                        with open(dest_file, "wb") as out_f:
                            shutil.copyfileobj(f_obj, out_f)
                    extracted_paths.append(dest_file)
    else:
        raise ValueError(f"Unrecognized or unsupported archive format: {archive_path}")

    return extracted_paths


def list_archive(archive_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """List detailed file contents of an archive."""
    archive = Path(archive_path).resolve()
    items: List[Dict[str, Any]] = []

    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive, "r") as zf:
            for info in zf.infolist():
                dt = datetime(*info.date_time, tzinfo=timezone.utc).isoformat()
                items.append({
                    "filename": info.filename,
                    "size": info.file_size,
                    "compressed_size": info.compress_size,
                    "is_dir": info.is_dir(),
                    "modified": dt,
                })
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive, "r:*") as tf:
            for member in tf.getmembers():
                dt = datetime.fromtimestamp(member.mtime, tz=timezone.utc).isoformat()
                items.append({
                    "filename": member.name,
                    "size": member.size,
                    "compressed_size": member.size,  # tar member compression is stream-level
                    "is_dir": member.isdir(),
                    "modified": dt,
                })
    else:
        raise ValueError(f"Not a valid zip or tar archive: {archive_path}")

    return items


def inspect_archive(archive_path: Union[str, Path]) -> Dict[str, Any]:
    """Inspect archive and compute compression and safety summary."""
    return validate_archive_safety(archive_path)


def verify_archive(archive_path: Union[str, Path]) -> bool:
    """Verify archive integrity by checking headers and checksums."""
    archive = Path(archive_path).resolve()
    if not archive.is_file():
        return False

    if zipfile.is_zipfile(archive):
        try:
            with zipfile.ZipFile(archive, "r") as zf:
                bad_file = zf.testzip()
                return bad_file is None
        except Exception:
            return False

    if tarfile.is_tarfile(archive):
        try:
            with tarfile.open(archive, "r:*") as tf:
                for member in tf.getmembers():
                    if member.isfile():
                        f = tf.extractfile(member)
                        if f is not None:
                            # Read through to ensure no EOF or corruption error
                            while f.read(65536):
                                pass
            return True
        except Exception:
            return False

    return False
