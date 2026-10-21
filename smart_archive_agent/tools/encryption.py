from __future__ import annotations
import subprocess
from smart_archive_agent.security.validation import resolve_existing_path, resolve_output_path, reject_same_path, ValidationError

# The passphrase is collected by the agent (getpass, never echoed) and handed to
# GPG on standard input with loopback pinentry, so it never appears in argv,
# environment variables or logs, and no GUI/curses pinentry is needed.
GPG_BASE = ["gpg", "--batch", "--yes", "--no-symkey-cache", "--pinentry-mode", "loopback",
            "--passphrase-fd", "0"]

def _gpg(args: list[str], passphrase: str, failure: str) -> None:
    try:
        subprocess.run(GPG_BASE + args, input=passphrase + "\n", check=True,
                       capture_output=True, text=True, timeout=600)
    except FileNotFoundError as exc:
        raise RuntimeError("GPG is not installed. Install it with: sudo apt install gnupg") from exc
    except subprocess.CalledProcessError as exc:
        lines = (exc.stderr or exc.stdout or "").strip().splitlines()
        detail = lines[-1].replace("gpg: ", "", 1) if lines else ""  # Python 3.8: no removeprefix
        if "bad session key" in detail.lower() or "bad passphrase" in detail.lower():
            detail = "wrong passphrase"
        raise RuntimeError(f"{failure} ({detail})" if detail else failure) from exc

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
    try:
        _gpg(["--symmetric", "--cipher-algo", "AES256", "--output", str(output), str(source)],
             passphrase, "GPG encryption failed.")
    except Exception:
        output.unlink(missing_ok=True)
        raise
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
    try:
        _gpg(["--output", str(output), "--decrypt", str(source)], passphrase,
             "GPG decryption failed. Check the passphrase.")
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {"success": True, "operation": "decrypt_file", "output": str(output),
            "message": "File decrypted successfully."}
