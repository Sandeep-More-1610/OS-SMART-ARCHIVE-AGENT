from pathlib import Path
import subprocess
import tarfile
import zipfile
from app.security.validation import (
    resolve_existing_path, resolve_output_path, reject_same_path, ValidationError
)

def _run(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True, timeout=600)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required Linux utility is not installed: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("The operation timed out.") from exc
    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or exc.stdout or str(exc)).strip()
        raise RuntimeError(message or "Linux utility failed.") from exc

def create_archive(source_path: str, output_path: str, compression: str = "xz") -> dict:
    source = resolve_existing_path(source_path)
    output = resolve_output_path(output_path)
    reject_same_path(source, output)
    if output.exists():
        raise ValidationError(f"Output already exists: {output}. Choose another name.")
    if compression not in {"none", "gz", "bz2", "xz"}:
        raise ValidationError("Compression must be one of: none, gz, bz2, xz.")
    flag = {"none": "-cf", "gz": "-czf", "bz2": "-cjf", "xz": "-cJf"}[compression]
    _run(["tar", flag, str(output), "-C", str(source.parent), source.name])
    return {"success": True, "operation": "create_archive", "output": str(output),
            "message": f"Archive created using {compression} compression."}

def list_archive(archive_path: str) -> dict:
    archive = resolve_existing_path(archive_path)
    if not archive.is_file():
        raise ValidationError("Archive path must be a file.")
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            entries = zf.namelist()
    else:
        result = _run(["tar", "-tf", str(archive)])
        entries = result.stdout.splitlines()
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
        result = _run(["file", "-b", str(archive)])
        kind = result.stdout.strip()
        try:
            entries = _run(["tar", "-tf", str(archive)]).stdout.splitlines()
        except Exception:
            entries = []
    return {"success": True, "operation": "inspect_archive", "archive": str(archive),
            "type": kind, "entries_count": len(entries), "entries_preview": entries[:20],
            "message": f"Archive/file type: {kind}"}

def extract_archive(archive_path: str, destination_path: str) -> dict:
    archive = resolve_existing_path(archive_path)
    destination = resolve_output_path(destination_path)
    if not archive.is_file():
        raise ValidationError("Archive path must be a file.")
    if not destination.exists():
        destination.mkdir(parents=False)
    if not destination.is_dir():
        raise ValidationError("Extraction destination must be a directory.")
    # Reject obvious path traversal entries before extraction.
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            for name in zf.namelist():
                target = (destination / name).resolve()
                if target != destination.resolve() and destination.resolve() not in target.parents:
                    raise ValidationError("Archive contains a path that escapes the destination.")
            zf.extractall(destination)
    else:
        with tarfile.open(archive, "r:*") as tf:
            root = destination.resolve()
            for member in tf.getmembers():
                target = (destination / member.name).resolve()
                if target != root and root not in target.parents:
                    raise ValidationError("Archive contains a path that escapes the destination.")
                if member.issym() or member.islnk():
                    raise ValidationError("Archive contains links; extraction stopped for safety.")
            try:
                tf.extractall(destination, filter="data")
            except TypeError:
                tf.extractall(destination)
    return {"success": True, "operation": "extract_archive", "destination": str(destination),
            "message": f"Archive extracted to {destination}"}

def compress_file(source_path: str, output_path: str, algorithm: str = "xz") -> dict:
    source = resolve_existing_path(source_path)
    output = resolve_output_path(output_path)
    reject_same_path(source, output)
    if not source.is_file():
        raise ValidationError("Compression input must be a file.")
    if output.exists():
        raise ValidationError(f"Output already exists: {output}. Choose another name.")
    commands = {
        "gz": ["gzip", "-c", str(source)],
        "bz2": ["bzip2", "-c", str(source)],
        "xz": ["xz", "-c", "-T0", str(source)],
    }
    if algorithm not in commands:
        raise ValidationError("Compression algorithm must be gz, bz2, or xz.")
    try:
        with output.open("xb") as target:
            subprocess.run(commands[algorithm], check=True, stdout=target, stderr=subprocess.PIPE,
                           text=False, timeout=600)
    except FileNotFoundError as exc:
        output.unlink(missing_ok=True)
        raise RuntimeError(f"Required Linux utility is not installed: {exc.filename}") from exc
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {"success": True, "operation": "compress_file", "output": str(output),
            "message": f"File compressed with {algorithm}."}

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
    command = next((cmd for suffix, cmd in commands.items() if source.name.endswith(suffix)), None)
    if command is None:
        raise ValidationError("Cannot infer compression format. Use a .gz, .bz2, or .xz file.")
    try:
        with output.open("xb") as target:
            subprocess.run(command, check=True, stdout=target, stderr=subprocess.PIPE,
                           text=False, timeout=600)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {"success": True, "operation": "decompress_file", "output": str(output),
            "message": f"File decompressed to {output}."}
