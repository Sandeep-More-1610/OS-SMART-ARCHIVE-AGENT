from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass
class Intent:
    operation: str
    args: dict
    missing: list[str]
    message: str = ""

# Deterministic intent recognition: works offline and without an API key. When the
# Agentic Shell's LLM is available it calls the tools directly instead (see
# tools/registry.py); this module is the built-in fallback.
PATH_RE = re.compile(
    r""""(?P<double>[^"]+)"|'(?P<single>[^']+)'|(?P<path>"""
    r"""[A-Za-z]:[\\/][^"'<>\r\n]*?(?=\s+(?:to|into|and|with|then)\b|\s+[A-Za-z]:[\\/]|$)|"""
    r"""(?:~|/|\./|\.\./|\.\\|\.\.\\|\\\\)[^\s"'<>]+|"""
    r"""[A-Za-z0-9_-][A-Za-z0-9_.-]*\.(?:tar\.xz|tar\.gz|tar\.bz2|tar|tgz|tbz2?|txz|zip|gz|bz2|xz|gpg|txt|md|pdf|py|log|csv|json|jpg|png)\b)""",
    re.IGNORECASE,
)

def _words(*phrases: str) -> re.Pattern:
    return re.compile(r"\b(?:" + "|".join(phrases) + r")\b", re.IGNORECASE)

# Checked in this order; the first match decides the operation. Phrases are matched
# as whole words, so "zip" does not match inside "gzip" and "lock" not inside "unlock".
VOCABULARY = [
    ("decrypt_file", _words(r"decrypt\w*", r"unlock", r"decipher", r"remove\s+the\s+password")),
    ("encrypt_file", _words(r"encrypt\w*", r"password[- ]protect\w*", r"protect\s+(?:it\s+)?with\s+a\s+password",
                            r"with\s+a\s+password", r"lock", r"secure\s+.*\bwith\s+(?:gpg|a\s+password)", r"gpg")),
    ("extract_archive", _words(r"extract\w*", r"unzip\w*", r"unpack\w*", r"untar", r"unarchive",
                               r"restore", r"open\s+(?:up\s+)?the\s+archive", r"open\s+up")),
    ("decompress_file", _words(r"decompress\w*", r"uncompress\w*", r"gunzip", r"unxz", r"bunzip2?",
                               r"inflate")),
    ("list_archive", _words(r"list", r"inspect\w*", r"what\s+is\s+inside", r"what'?s\s+inside",
                            r"what'?s\s+in", r"contents?\s+of", r"show\s+(?:me\s+)?(?:the\s+)?(?:files|contents)",
                            r"inside\s+this\s+archive", r"look\s+inside", r"peek")),
    ("compress_file", _words(r"compress\w*", r"squeeze", r"shrink", r"reduce\s+the\s+size", r"make\s+.*\bsmaller",
                             r"gzip", r"bzip2?", r"xz")),
    ("create_archive", _words(r"archive", r"zip", r"tar", r"tarball", r"bundle", r"package", r"pack(?:\s+up)?",
                              r"back\s?up", r"backup")),
]
EXIT_RE = _words("exit", "quit", "goodbye", "bye")
ARCHIVE_EXT_RE = re.compile(r"\.(tar(\.(gz|bz2|xz))?|tgz|tbz2?|txz|zip)$", re.IGNORECASE)

# Arguments each operation takes, in the order paths appear in the request.
ARG_ORDER = {
    "decrypt_file": ("source_path", "output_path"),
    "encrypt_file": ("source_path", "output_path"),
    "extract_archive": ("archive_path", "destination_path"),
    "decompress_file": ("source_path", "output_path"),
    "list_archive": ("archive_path",),
    "compress_file": ("source_path", "output_path"),
    "create_archive": ("source_path", "output_path"),
}

def _paths(text: str) -> list[str]:
    found = []
    for match in PATH_RE.finditer(text):
        quoted = match.group("double") or match.group("single")
        value = quoted if quoted is not None else match.group("path").rstrip(".,!?;: ")
        if value:
            found.append(value)
    # Keep stable order and remove duplicates.
    return list(dict.fromkeys(found))

def classify(text: str) -> Intent:
    raw = text.strip()
    if not raw:
        return Intent("unknown", {}, [], "Please enter a request.")
    paths = _paths(raw)
    words = PATH_RE.sub(" ", raw)  # keywords are matched with the file paths removed
    if EXIT_RE.search(words) and len(raw.split()) <= 3:
        return Intent("exit", {}, [])
    operation = next((op for op, pattern in VOCABULARY if pattern.search(words)), None)
    # "list"/"show" are generic verbs: without a path or an archive word they belong to another agent.
    if operation == "list_archive" and not paths and not re.search(r"\b(archive|zip|tar|tarball)\b", words, re.I):
        operation = None
    if operation is None:
        return Intent("unrelated", {}, [], "That request is outside the Smart Archive Agent's scope.")
    # "uncompress project.tar.gz" means unpack the archive, not just strip the .gz layer.
    if operation == "decompress_file" and paths and ARCHIVE_EXT_RE.search(paths[0]):
        operation = "extract_archive"
    names = ARG_ORDER[operation]
    args = {name: (paths[i] if i < len(paths) else "") for i, name in enumerate(names)}
    if operation == "compress_file":
        args["algorithm"] = "xz"
    if operation == "create_archive":
        args["compression"] = "xz"
    return Intent(operation, args, [name for name in names if not args[name]])
