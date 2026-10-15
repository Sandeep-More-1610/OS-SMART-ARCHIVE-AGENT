"""Intent parsing engine for natural language and structured archiving commands."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ActionType(str, Enum):
    ARCHIVE = "archive"
    EXTRACT = "extract"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    LIST = "list"
    VERIFY = "verify"
    UNKNOWN = "unknown"


@dataclass
class ArchiveIntent:
    """Structured representation of an archiving or security intent."""
    action: ActionType
    sources: List[str] = field(default_factory=list)
    destination: Optional[str] = None
    format: Optional[str] = None
    encrypt: bool = False
    decrypt: bool = False
    password: Optional[str] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    confidence: float = 0.0
    raw_query: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert intent to serializable dictionary."""
        return {
            "action": self.action.value,
            "sources": self.sources,
            "destination": self.destination,
            "format": self.format,
            "encrypt": self.encrypt,
            "decrypt": self.decrypt,
            "password_provided": bool(self.password),
            "filters": self.filters,
            "dry_run": self.dry_run,
            "confidence": self.confidence,
            "raw_query": self.raw_query,
        }


class IntentParser:
    """Parse user instructions into actionable ArchiveIntent structures."""

    ACTION_PATTERNS = {
        ActionType.ARCHIVE: [
            r"\b(archive|compress|pack|zip|backup|bundle)\b",
        ],
        ActionType.EXTRACT: [
            r"\b(extract|decompress|unpack|unzip|restore)\b",
        ],
        ActionType.DECRYPT: [
            r"\b(decrypt|decode|unlock)\b",
        ],
        ActionType.ENCRYPT: [
            r"\b(encrypt|encode|lock|secure)\b",
        ],
        ActionType.LIST: [
            r"\b(list|show|view|inspect|contents)\b",
        ],
        ActionType.VERIFY: [
            r"\b(verify|check|test|validate|audit)\b",
        ],
    }

    FORMAT_PATTERNS = {
        "tar.gz": r"\b(tar\.gz|tgz|tarball)\b",
        "tar.bz2": r"\b(tar\.bz2|tbz2)\b",
        "tar.xz": r"\b(tar\.xz|txz)\b",
        "tar": r"\b(tar)\b",
        "zip": r"\b(zip)\b",
    }

    def parse(self, text: str) -> ArchiveIntent:
        """Parse natural language command into an ArchiveIntent."""
        raw_query = text.strip()
        lower_query = raw_query.lower()

        # Check dry run
        dry_run = bool(re.search(r"\b(dry[- ]?run|simulate|preview|test[- ]?run)\b", lower_query))

        # Check password / key extraction
        password = None
        pwd_match = re.search(r"(?:password|passphrase|key|with key|with password)[:=\s]+([^\s,;]+)", raw_query, re.IGNORECASE)
        if pwd_match:
            password = pwd_match.group(1).strip("'\"")

        # Check encryption / decryption flags
        wants_encrypt = bool(re.search(r"\b(encrypt|secure|lock|encrypted)\b", lower_query))
        wants_decrypt = bool(re.search(r"\b(decrypt|unencrypted|unlock)\b", lower_query))

        # Detect primary action
        action = ActionType.UNKNOWN
        confidence = 0.5

        if wants_decrypt and not re.search(r"\b(extract|unzip|unpack)\b", lower_query):
            action = ActionType.DECRYPT
            confidence = 0.9
        elif re.search(r"\b(extract|decompress|unpack|unzip|restore)\b", lower_query):
            action = ActionType.EXTRACT
            confidence = 0.95
        elif re.search(r"\b(list|show contents|view contents|inspect)\b", lower_query):
            action = ActionType.LIST
            confidence = 0.95
        elif re.search(r"\b(verify|check integrity|test archive|validate)\b", lower_query):
            action = ActionType.VERIFY
            confidence = 0.95
        elif re.search(r"\b(archive|compress|pack|zip|backup|bundle)\b", lower_query):
            action = ActionType.ARCHIVE
            confidence = 0.95
        elif wants_encrypt:
            action = ActionType.ENCRYPT
            confidence = 0.85

        # Detect format
        detected_format = None
        for fmt, pat in self.FORMAT_PATTERNS.items():
            if re.search(pat, lower_query):
                detected_format = fmt
                break

        # Detect filters (extensions, patterns)
        filters: Dict[str, Any] = {}
        ext_matches = re.findall(
            r"(?:\ball\s+|\bonly\s+|\bfilter\s+)(?:\*\.)?([a-zA-Z0-9]+)|\*\.([a-zA-Z0-9]+)|(?:\.|\*)?([a-zA-Z0-9]+)\s+files\b",
            raw_query,
            re.IGNORECASE,
        )
        if ext_matches:
            cleaned_exts = []
            for match in ext_matches:
                for group in match:
                    if group and group.lower() not in ("tar", "zip", "gz", "bz2", "xz", "enc", "all", "only", "the"):
                        ext = f".{group.lower()}"
                        if ext not in cleaned_exts:
                            cleaned_exts.append(ext)
            if cleaned_exts:
                filters["include_extensions"] = cleaned_exts

        # Detect source and destination paths
        sources: List[str] = []
        destination: Optional[str] = None

        # Look for "to <dest>" or "into <dest>"
        dest_match = re.search(r"\b(?:to|into|output|as|dest(?:ination)?)\s+([^\s,;]+)", raw_query, re.IGNORECASE)
        if dest_match:
            cand = dest_match.group(1).strip("'\"")
            # Avoid picking words like 'a', 'the', 'password', 'key'
            if cand.lower() not in ("a", "the", "an", "password", "key", "secret"):
                destination = cand

        # Look for "from <src>" or extract paths
        src_match = re.search(r"\b(?:from|of|source|in|folder|directory)\s+([^\s,;]+)", raw_query, re.IGNORECASE)
        if src_match:
            cand = src_match.group(1).strip("'\"")
            if cand.lower() not in ("a", "the", "an", "all", "password"):
                sources.append(cand)

        # Fallback path extraction: look for file/path-like tokens (containing / or \ or standard extensions)
        tokens = [t.strip("',;\"()[]{}") for t in raw_query.split()]
        path_like = [
            t for t in tokens
            if ("." in t or "/" in t or "\\" in t)
            and not t.startswith("-")
            and t.lower() not in ("tar.gz", "tar.bz2", "tar.xz", ".zip", ".tar", "tar", "zip")
            and t != password
        ]

        for p in path_like:
            if destination and p == destination:
                continue
            if p not in sources:
                sources.append(p)

        # Format detection from destination or source extension
        if not detected_format:
            check_cand = destination or (sources[0] if sources else None)
            if check_cand:
                cand_lower = check_cand.lower()
                if cand_lower.endswith((".tar.gz", ".tgz")):
                    detected_format = "tar.gz"
                elif cand_lower.endswith((".tar.bz2", ".tbz2")):
                    detected_format = "tar.bz2"
                elif cand_lower.endswith((".tar.xz", ".txz")):
                    detected_format = "tar.xz"
                elif cand_lower.endswith(".tar"):
                    detected_format = "tar"
                elif cand_lower.endswith(".zip"):
                    detected_format = "zip"

        return ArchiveIntent(
            action=action,
            sources=sources,
            destination=destination,
            format=detected_format,
            encrypt=wants_encrypt or (password is not None and action == ActionType.ARCHIVE),
            decrypt=wants_decrypt or (password is not None and action in (ActionType.EXTRACT, ActionType.DECRYPT)),
            password=password,
            filters=filters,
            dry_run=dry_run,
            confidence=confidence,
            raw_query=raw_query,
        )
