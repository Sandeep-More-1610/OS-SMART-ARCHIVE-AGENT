from __future__ import annotations
import subprocess
import os
import shutil
from pathlib import Path
from smart_archive_agent.security.validation import resolve_existing_path, resolve_output_path, reject_same_path, ValidationError

# The passphrase is collected by the agent (getpass, never echoed) and handed to
# GPG on standard input with loopback pinentry, so it never appears in argv,
# environment variables or logs, and no GUI/curses pinentry is needed.
GPG_BASE = ["gpg", "--batch", "--yes", "--no-symkey-cache", "--pinentry-mode", "loopback",
            "--passphrase-fd", "0"]

def find_gpg() -> str | None:
    """Find GPG on PATH or in standard Windows GnuPG/Git installations."""
    found = shutil.which("gpg")
    if found or os.name != "nt":
        return found
    for variable in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(variable)
        if not base:
            continue
        for relative in ("GnuPG/bin/gpg.exe", "Git/usr/bin/gpg.exe", "Programs/Git/usr/bin/gpg.exe"):
            candidate = Path(base) / relative
            if candidate.is_file():
                return str(candidate)
    return None

def _gpg(args: list[str], passphrase: str, failure: str, output: Path) -> None:
    executable = find_gpg()
    if not executable:
        raise RuntimeError("GPG is not installed. Install GnuPG/Gpg4win on Windows or run sudo apt install gnupg on Linux.")
    if not isinstance(passphrase, str) or not passphrase or any(c in passphrase for c in "\r\n\x00"):
        raise ValidationError("Passphrase must be non-empty and cannot contain newline or NUL characters.")
    target = output.open("xb")  # reserve exclusively; GPG must never replace another file
    try:
        with target:
            subprocess.run([executable] + GPG_BASE[1:] + args, input=(passphrase + "\n").encode("utf-8"), check=True,
                           stdout=target, stderr=subprocess.PIPE, timeout=600)
    except FileNotFoundError as exc:
        output.unlink(missing_ok=True)
        raise RuntimeError("GPG is not installed. Install it with: sudo apt install gnupg") from exc
    except subprocess.CalledProcessError as exc:
        output.unlink(missing_ok=True)
        lines = (exc.stderr or exc.stdout or b"").decode("utf-8", errors="replace").strip().splitlines()
        detail = lines[-1].replace("gpg: ", "", 1) if lines else ""  # Python 3.8: no removeprefix
        if "bad session key" in detail.lower() or "bad passphrase" in detail.lower():
            detail = "wrong passphrase"
        raise RuntimeError(f"{failure} ({detail})" if detail else failure) from exc
    except Exception:
        output.unlink(missing_ok=True)
        raise

def encrypt_file(source_path: str, output_path: str, passphrase: str | None = None) -> dict:
    source = resolve_existing_path(source_path)
    output = resolve_output_path(output_path)
    reject_same_path(source, output)
    if not source.is_file():
        raise ValidationError("Encryption input must be a file. Archive a folder first.")
    if output.exists():
        raise ValidationError(f"Output already exists: {output}. Choose another name.")
    if not passphrase:
        raise ValidationError("A passphrase is required for encryption.")
    _gpg(["--symmetric", "--cipher-algo", "AES256", "--output", "-", "--", str(source)],
         passphrase, "GPG encryption failed.", output)
    return {"success": True, "operation": "encrypt_file", "output": str(output),
            "message": "File encrypted with GPG symmetric AES-256."}

def decrypt_file(source_path: str, output_path: str, passphrase: str | None = None) -> dict:
    source = resolve_existing_path(source_path)
    output = resolve_output_path(output_path)
    reject_same_path(source, output)
    if not source.is_file():
        raise ValidationError("Decryption input must be a file.")
    if output.exists():
        raise ValidationError(f"Output already exists: {output}. Choose another name.")
    if not passphrase:
        raise ValidationError("A passphrase is required for decryption.")
    _gpg(["--output", "-", "--decrypt", "--", str(source)], passphrase,
         "GPG decryption failed. Check the passphrase.", output)
    return {"success": True, "operation": "decrypt_file", "output": str(output),
            "message": "File decrypted successfully."}
