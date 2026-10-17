import re
from dataclasses import dataclass

@dataclass
class Intent:
    operation: str
    args: dict
    missing: list[str]
    message: str = ""

# This initial implementation is deterministic and works without an API key.
# A model-backed intent adapter can replace this module later without changing tool functions.
PATH_RE = re.compile(
    r"""(?P<path>(?:~|/|\./|\.\./)[^\s"'<>]+|[A-Za-z0-9_-][A-Za-z0-9_.-]*\.(?:tar\.xz|tar\.gz|tar\.bz2|tar|tgz|tbz2|zip|gz|bz2|xz|gpg|txt|md|pdf|py|log|csv|json|jpg|png))""",
    re.IGNORECASE,
)

def _paths(text: str) -> list[str]:
    found = []
    for match in PATH_RE.finditer(text):
        value = match.group("path").rstrip(".,!?;:")
        if value:
            found.append(value)
    # Keep stable order and remove duplicates.
    return list(dict.fromkeys(found))

def classify(text: str) -> Intent:
    raw = text.strip()
    low = raw.lower()
    paths = _paths(raw)
    if not raw:
        return Intent("unknown", {}, [], "Please enter a request.")
    if any(x in low for x in ["exit", "quit", "goodbye"]) and len(low.split()) <= 3:
        return Intent("exit", {}, [])
    if not any(k in low for k in [
        "archive", "compress", "compression", "extract", "unzip", "decompress",
        "decompression", "encrypt", "decrypt", "gpg", "tar file", "archive file",
        "contents of", "inside this archive", "list archive", "inspect archive"
    ]):
        return Intent("unrelated", {}, [], "That request is outside the Smart Archive Agent's scope.")
    if any(k in low for k in ["decrypt", "decryption"]):
        return Intent("decrypt_file", {"source_path": paths[0] if paths else "", "output_path": paths[1] if len(paths)>1 else ""}, 
                      [k for k in ("source_path", "output_path") if not (paths[0] if k=="source_path" and paths else paths[1] if k=="output_path" and len(paths)>1 else "")])
    if any(k in low for k in ["encrypt", "encryption"]):
        return Intent("encrypt_file", {"source_path": paths[0] if paths else "", "output_path": paths[1] if len(paths)>1 else ""}, 
                      [k for k in ("source_path", "output_path") if not (paths[0] if k=="source_path" and paths else paths[1] if k=="output_path" and len(paths)>1 else "")])
    if any(k in low for k in ["extract", "unzip", "unpack"]):
        return Intent("extract_archive", {"archive_path": paths[0] if paths else "", "destination_path": paths[1] if len(paths)>1 else ""}, 
                      [k for k in ("archive_path", "destination_path") if not (paths[0] if k=="archive_path" and paths else paths[1] if k=="destination_path" and len(paths)>1 else "")])
    if any(k in low for k in ["decompress", "decompression"]):
        return Intent("decompress_file", {"source_path": paths[0] if paths else "", "output_path": paths[1] if len(paths)>1 else ""}, 
                      [k for k in ("source_path", "output_path") if not (paths[0] if k=="source_path" and paths else paths[1] if k=="output_path" and len(paths)>1 else "")])
    if any(k in low for k in ["inspect archive", "what is inside", "contents of", "list archive", "show me inside"]):
        return Intent("list_archive", {"archive_path": paths[0] if paths else ""}, [] if paths else ["archive_path"])
    if "compress" in low or "compression" in low:
        if "archive" in low and paths:
            return Intent("compress_file", {"source_path": paths[0], "output_path": paths[1] if len(paths)>1 else "", "algorithm": "xz"},
                          [] if len(paths)>1 else ["output_path"])
        return Intent("compress_file", {"source_path": paths[0] if paths else "", "output_path": paths[1] if len(paths)>1 else "", "algorithm": "xz"},
                      [k for k in ("source_path", "output_path") if not (paths[0] if k=="source_path" and paths else paths[1] if k=="output_path" and len(paths)>1 else "")])
    if "archive" in low or "backup" in low:
        return Intent("create_archive", {"source_path": paths[0] if paths else "", "output_path": paths[1] if len(paths)>1 else "", "compression": "xz"},
                      [k for k in ("source_path", "output_path") if not (paths[0] if k=="source_path" and paths else paths[1] if k=="output_path" and len(paths)>1 else "")])
    return Intent("unrelated", {}, [], "That request is outside the Smart Archive Agent's scope.")
