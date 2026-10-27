from __future__ import annotations
from pathlib import Path
import os
import subprocess
import tarfile
import zipfile
import gzip
import bz2
import lzma
import shutil
import stat
from pathlib import PureWindowsPath
from smart_archive_agent.security.validation import (
    resolve_existing_path, resolve_output_path, reject_same_path, ValidationError
)

LEVELS = ("fast", "normal", "max")

# Compressor command line for each algorithm at each level. "max" is what the
# planner selects for words such as "heavily", "maximum" or "as small as possible".
COMPRESSORS = {
    "gz": {"fast": ["gzip", "-1"], "normal": ["gzip", "-6"], "max": ["gzip", "-9"]},
    "bz2": {"fast": ["bzip2", "-1"], "normal": ["bzip2", "-9"], "max": ["bzip2", "-9"]},
    "xz": {"fast": ["xz", "-1", "-T0"], "normal": ["xz", "-6", "-T0"], "max": ["xz", "-9e", "-T0"]},
}

ARCHIVE_SUFFIXES = {
    ".tar.gz": "gz", ".tgz": "gz", ".tar.bz2": "bz2", ".tbz2": "bz2", ".tbz": "bz2",
    ".tar.xz": "xz", ".txz": "xz", ".tar": "none", ".zip": "zip",
}

def _run(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True, timeout=600,
                              stdin=subprocess.DEVNULL)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required Linux utility is not installed: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("The operation timed out.") from exc
    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or exc.stdout or str(exc)).strip()
        raise RuntimeError(message or "Linux utility failed.") from exc

def _size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file() and not p.is_symlink())

def archive_format_for(output_path: str) -> str | None:
    """Infer the archive format from an output file name, or None if unknown."""
    name = output_path.lower()
    for suffix, fmt in ARCHIVE_SUFFIXES.items():
        if name.endswith(suffix):
            return fmt
    return None

def _check_level(level: str) -> None:
    if level not in LEVELS:
        raise ValidationError("Compression level must be one of: fast, normal, max.")

def create_archive(source_path: str, output_path: str, compression: str = "auto",
                   level: str = "normal") -> dict:
    source = resolve_existing_path(source_path)
    if source == Path(source.anchor):
        raise ValidationError("Archiving the whole root filesystem is not allowed.")
    output = resolve_output_path(output_path)
    reject_same_path(source, output)
    if output.exists():
        raise ValidationError(f"Output already exists: {output}. Choose another name.")
    if output == source or source in output.parents:
        raise ValidationError("The archive cannot be written inside the folder being archived.")
    if compression == "auto":
        compression = archive_format_for(output.name) or "xz"
    if compression not in {"none", "gz", "bz2", "xz", "zip"}:
        raise ValidationError("Compression must be one of: none, gz, bz2, xz, zip.")
    _check_level(level)
    try:
        if compression != "zip" and os.name != "nt":
            output.touch(exist_ok=False)
        if compression == "zip":
            _create_zip(source, output, level)
        elif os.name == "nt":
            # Windows ships BSD tar, whose -I option is incompatible with GNU tar.
            options = {}
            if compression in {"gz", "bz2"}:
                options["compresslevel"] = {"fast": 1, "normal": 6, "max": 9}[level]
            elif compression == "xz":
                options["preset"] = {"fast": 1, "normal": 6, "max": 9 | lzma.PRESET_EXTREME}[level]
            with output.open("xb") as target:
                with tarfile.open(fileobj=target, mode="w:" + ("" if compression == "none" else compression),
                                  **options) as tf:
                    tf.add(source, arcname=source.name)
        elif compression == "none":
            _run(["tar", "-cf", str(output), "-C", str(source.parent), "--", source.name])
        else:
            program = " ".join(COMPRESSORS[compression][level])
            _run(["tar", "-I", program, "-cf", str(output), "-C", str(source.parent), "--", source.name])
    except FileExistsError:
        raise
    except Exception:
        output.unlink(missing_ok=True)
        raise
    original, packed = _size(source), output.stat().st_size
    return {"success": True, "operation": "create_archive", "output": str(output),
            "original_bytes": original, "archive_bytes": packed,
            "message": f"Archive created using {compression} compression ({level} level): "
                       f"{original:,} bytes -> {packed:,} bytes."}

def _create_zip(source: Path, output: Path, level: str) -> None:
    compresslevel = {"fast": 1, "normal": 6, "max": 9}[level]
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=compresslevel) as zf:
        if source.is_file():
            zf.write(source, source.name)
            return
        zf.write(source, source.name + "/")  # preserve empty source folders too
        for root, dirs, files in os.walk(source):
            for name in sorted(dirs + files):
                path = Path(root) / name
                if path.is_symlink():
                    continue  # never follow links out of the folder being archived
                zf.write(path, path.relative_to(source.parent))

def list_archive(archive_path: str) -> dict:
    archive = resolve_existing_path(archive_path)
    if not archive.is_file():
        raise ValidationError("Archive path must be a file.")
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            entries = zf.namelist()
    else:
        with tarfile.open(archive, "r:*") as tf:
            entries = tf.getnames()
    return {"success": True, "operation": "list_archive", "archive": str(archive),
            "entries": entries, "message": f"Found {len(entries)} archive entries."}

def inspect_archive(archive_path: str) -> dict:
    archive = resolve_existing_path(archive_path)
    if not archive.is_file():
        raise ValidationError("Archive path must be a file.")
    if zipfile.is_zipfile(archive):
        kind = "zip"
        with zipfile.ZipFile(archive) as zf:
            entries = zf.namelist()
    else:
        with tarfile.open(archive, "r:*") as tf:
            entries = tf.getnames()
        kind = "tar (" + (archive_format_for(archive.name) or "auto-detected") + ")"
    return {"success": True, "operation": "inspect_archive", "archive": str(archive),
            "type": kind, "entries_count": len(entries), "entries_preview": entries[:20],
            "message": f"Archive/file type: {kind}"}

def extract_archive(archive_path: str, destination_path: str) -> dict:
    archive = resolve_existing_path(archive_path)
    destination = resolve_output_path(destination_path)
    if not archive.is_file():
        raise ValidationError("Archive path must be a file.")
    if destination.exists() and not destination.is_dir():
        raise ValidationError("Extraction destination must be a directory.")
    root = destination.resolve()

    def check(name: str, is_directory: bool) -> None:
        # Treat Windows paths as unsafe even when scanning on Linux.
        windows = PureWindowsPath(name)
        if windows.drive or windows.root or "\\" in name:
            raise ValidationError("Archive contains a path that escapes the destination.")
        target = (root / name).resolve()
        if target != root and root not in target.parents:
            raise ValidationError("Archive contains a path that escapes the destination.")
        if target.exists() and not (is_directory and target.is_dir()):
            raise ValidationError(f"Extraction would overwrite an existing file: {target}")
        # Do not write through pre-existing links, even if they point inside root.
        raw_target = root / name
        if any(p.is_symlink() for p in (raw_target, *raw_target.parents)):
            raise ValidationError("Extraction through symbolic links is not allowed.")
        if any(p.exists() and not p.is_dir() for p in raw_target.parents):
            raise ValidationError("Extraction path has a non-directory parent.")

    # Every member is checked before the destination is created or anything is written.
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            for member in zf.infolist():
                check(member.filename, member.is_dir())
                kind = stat.S_IFMT(member.external_attr >> 16)
                if kind not in {0, stat.S_IFREG, stat.S_IFDIR}:
                    raise ValidationError("Archive contains links or special files; extraction stopped for safety.")
            destination.mkdir(exist_ok=True)
            zf.extractall(destination)
    else:
        with tarfile.open(archive, "r:*") as tf:
            for member in tf.getmembers():
                check(member.name, member.isdir())
                if not (member.isfile() or member.isdir()):
                    raise ValidationError("Archive contains links or special files; extraction stopped for safety.")
            destination.mkdir(exist_ok=True)
            try:
                tf.extractall(destination, filter="data")
            except TypeError:  # Python < 3.12 has no extraction filters
                tf.extractall(destination)
    return {"success": True, "operation": "extract_archive", "destination": str(destination),
            "output": str(destination), "message": f"Archive extracted to {destination}"}

def compress_file(source_path: str, output_path: str, algorithm: str = "xz",
                  level: str = "normal") -> dict:
    source = resolve_existing_path(source_path)
    output = resolve_output_path(output_path)
    reject_same_path(source, output)
    if not source.is_file():
        raise ValidationError("Compression input must be a file. Folders are archived with create_archive.")
    if output.exists():
        raise ValidationError(f"Output already exists: {output}. Choose another name.")
    if algorithm not in COMPRESSORS:
        raise ValidationError("Compression algorithm must be gz, bz2, or xz.")
    _check_level(level)
    command = COMPRESSORS[algorithm][level] + ["-c", "--", str(source)]
    try:
        with output.open("xb") as target:
            if os.name == "nt":
                effort = {"fast": 1, "normal": 6, "max": 9}[level]
                opener = {"gz": gzip.open, "bz2": bz2.BZ2File, "xz": lzma.LZMAFile}[algorithm]
                options = {"preset": effort | (lzma.PRESET_EXTREME if level == "max" else 0)} if algorithm == "xz" else {"compresslevel": effort}
                with source.open("rb") as data, opener(target, "wb", **options) as compressed:
                    shutil.copyfileobj(data, compressed)
            else:
                subprocess.run(command, check=True, stdout=target, stderr=subprocess.PIPE,
                               stdin=subprocess.DEVNULL, text=False, timeout=600)
    except FileExistsError:
        raise
    except FileNotFoundError as exc:
        output.unlink(missing_ok=True)
        raise RuntimeError(f"Required Linux utility is not installed: {exc.filename}") from exc
    except Exception:
        output.unlink(missing_ok=True)
        raise
    original, packed = source.stat().st_size, output.stat().st_size
    return {"success": True, "operation": "compress_file", "output": str(output),
            "original_bytes": original, "archive_bytes": packed,
            "message": f"File compressed with {algorithm} ({level} level): "
                       f"{original:,} bytes -> {packed:,} bytes."}

def decompress_file(source_path: str, output_path: str) -> dict:
    source = resolve_existing_path(source_path)
    output = resolve_output_path(output_path)
    reject_same_path(source, output)
    if output.exists():
        raise ValidationError(f"Output already exists: {output}. Choose another name.")
    commands = {
        ".gz": ["gzip", "-dc", str(source)],
        ".bz2": ["bzip2", "-dc", str(source)],
        ".xz": ["xz", "-dc", str(source)],
    }
    command = next((cmd for suffix, cmd in commands.items() if source.name.lower().endswith(suffix)), None)
    if command is None:
        raise ValidationError("Cannot infer compression format. Use a .gz, .bz2, or .xz file.")
    try:
        with output.open("xb") as target:
            if os.name == "nt":
                opener = {".gz": gzip.open, ".bz2": bz2.open, ".xz": lzma.open}[source.suffix.lower()]
                with opener(source, "rb") as compressed:
                    shutil.copyfileobj(compressed, target)
            else:
                subprocess.run(command, check=True, stdout=target, stderr=subprocess.PIPE,
                               stdin=subprocess.DEVNULL, text=False, timeout=600)
    except FileExistsError:
        raise
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {"success": True, "operation": "decompress_file", "output": str(output),
            "message": f"File decompressed to {output}."}
