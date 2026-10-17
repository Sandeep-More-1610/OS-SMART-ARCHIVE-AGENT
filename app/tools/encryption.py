from pathlib import Path
import subprocess
from app.security.validation import resolve_existing_path, resolve_output_path, reject_same_path, ValidationError

def encrypt_file(source_path: str, output_path: str) -> dict:
    source = resolve_existing_path(source_path)
    output = resolve_output_path(output_path)
    reject_same_path(source, output)
    if not source.is_file():
        raise ValidationError("Encryption input must be a file.")
    if output.exists():
        raise ValidationError(f"Output already exists: {output}. Choose another name.")
    try:
        subprocess.run(["gpg", "--batch", "--yes", "--symmetric", "--cipher-algo", "AES256",
                        "--output", str(output), str(source)],
                       check=True, capture_output=True, text=True, timeout=600)
    except FileNotFoundError as exc:
        raise RuntimeError("GPG is not installed. Install it with: sudo apt install gnupg") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError((exc.stderr or exc.stdout or "GPG encryption failed.").strip()) from exc
    return {"success": True, "operation": "encrypt_file", "output": str(output),
            "message": "File encrypted with GPG symmetric encryption. GPG will prompt for a passphrase."}

def decrypt_file(source_path: str, output_path: str) -> dict:
    source = resolve_existing_path(source_path)
    output = resolve_output_path(output_path)
    reject_same_path(source, output)
    if not source.is_file():
        raise ValidationError("Decryption input must be a file.")
    if output.exists():
        raise ValidationError(f"Output already exists: {output}. Choose another name.")
    try:
        subprocess.run(["gpg", "--output", str(output), "--decrypt", str(source)],
                       check=True, capture_output=True, text=True, timeout=600)
    except FileNotFoundError as exc:
        raise RuntimeError("GPG is not installed. Install it with: sudo apt install gnupg") from exc
    except subprocess.CalledProcessError as exc:
        output.unlink(missing_ok=True)
        raise RuntimeError((exc.stderr or exc.stdout or "GPG decryption failed. Check the passphrase.").strip()) from exc
    return {"success": True, "operation": "decrypt_file", "output": str(output),
            "message": "File decrypted successfully."}
