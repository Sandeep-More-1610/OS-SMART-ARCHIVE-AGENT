from __future__ import annotations
import re

# Regex blacklist of destructive shell idioms and phrases. Any match stops the
# request before intent routing, so no tool is ever selected for it.
DESTRUCTIVE_PATTERNS = [
    (re.compile(r"\brm\s+-[a-z]*r[a-z]*f|\brm\s+-[a-z]*f[a-z]*r", re.I), "recursive forced delete (rm -rf)"),
    (re.compile(r"\bmkfs(\.\w+)?\b", re.I), "filesystem formatting (mkfs)"),
    (re.compile(r"\bdd\s+if=", re.I), "raw disk write (dd)"),
    (re.compile(r":\(\)\s*\{\s*:\|:&\s*\};:"), "fork bomb"),
    (re.compile(r">\s*/dev/(sd|nvme|hd)\w*", re.I), "raw block-device overwrite"),
    (re.compile(r"\bchmod\s+(-R\s+)?777\s+/(\s|$)", re.I), "world-writable root filesystem"),
    (re.compile(r"\b(shutdown|reboot|poweroff|halt)\b", re.I), "system power control"),
    (re.compile(r"\b(format|wipe|erase|destroy)\b.*\b(drive|disk|partition|system|everything)\b", re.I),
     "disk wipe request"),
    (re.compile(r"\bdelete\s+(everything|all\s+files|all\s+my\s+files)\b", re.I), "mass deletion request"),
    (re.compile(r"(?:^|\s)/\*?(?:\s|$)"), "operation on the whole root filesystem (/)"),
    (re.compile(r"[;&|`]\s*(rm|sudo|curl|wget|bash|sh)\b|\$\(", re.I), "shell command injection"),
]

# Output locations the agent will never write into, even if the user asks.
# /root is deliberately absent: it is the home folder when the shell runs as root.
PROTECTED_DIRS = ("/bin", "/boot", "/dev", "/etc", "/lib", "/lib64", "/proc",
                  "/sbin", "/sys", "/usr", "/var/lib")


def check_request(text: str) -> str | None:
    """Return a refusal reason if the request matches a destructive pattern."""
    for pattern, reason in DESTRUCTIVE_PATTERNS:
        if pattern.search(text):
            return reason
    return None
