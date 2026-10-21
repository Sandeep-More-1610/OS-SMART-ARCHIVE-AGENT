"""Machine-readable description of this agent for the Agentic Shell's router.

`python3 -m smart_archive_agent --manifest` prints it; agent.json in the repository
root is a copy for readers who do not run Python.
"""
from __future__ import annotations

from smart_archive_agent.tools.registry import TOOL_PREFIX, TOOL_SCHEMAS

VERSION = "1.0.0"
AGENT_ID = 12
AGENT_NAME = "smart_archive_agent"
DISPLAY_NAME = "Smart Archive Agent"
AGENT_DESCRIPTION = (
    "Creates archives (tar, tar.gz, tar.bz2, tar.xz, zip), compresses and decompresses single files "
    "(gzip, bzip2, xz), lists, inspects and safely extracts archives, and encrypts or decrypts files "
    "with GPG AES-256. Understands compression strength words such as 'heavily' or 'quickly'. "
    "Does not search for files, delete or shred files, rotate logs or free disk space."
)

def get_manifest() -> dict:
    return {
        "agent_id": AGENT_ID,
        "name": AGENT_NAME,
        "display_name": DISPLAY_NAME,
        "version": VERSION,
        "description": AGENT_DESCRIPTION,
        "team": ["Kush Aghera (24BCE0149)", "Sandeep More (24BCE2883)"],
        "routing_keywords": ["archive", "zip", "unzip", "tar", "tarball", "compress", "decompress",
                             "extract", "unpack", "backup", "bundle", "gzip", "bzip2", "xz",
                             "encrypt", "decrypt", "gpg", "password-protect"],
        "example_prompts": [
            "Zip up my project folder, compress it heavily, and encrypt it.",
            "extract ./backup.tar.xz into ./restored",
            "what is inside ./photos.zip",
            "decrypt ./project.tar.xz.gpg and extract it",
        ],
        "python_api": {
            "import": "import smart_archive_agent",
            "get_tools": "smart_archive_agent.get_tools(style='generic'|'openai'|'anthropic', prefixed=False)",
            "execute_tool": "smart_archive_agent.execute_tool(name, args, passphrase=None) -> dict",
            "handle_request": "smart_archive_agent.handle_request(text, confirm=None, passphrase=None) -> dict",
        },
        "command_line": "smart-archive-agent [--yes] [\"request\"] | --doctor | --manifest",
        "tools": [t["name"] for t in TOOL_SCHEMAS],
        "prefixed_tool_names": [TOOL_PREFIX + t["name"] for t in TOOL_SCHEMAS],
        "requirements": {
            "python": ">=3.8",
            "python_packages": [],
            "system_commands": ["tar", "gzip", "bzip2", "xz", "gpg", "file"],
            "apt_install": "sudo apt install -y tar gzip bzip2 xz-utils gnupg file",
        },
        "needs_root": False,
        "secrets": "encrypt_file / decrypt_file need a passphrase, passed as execute_tool(..., passphrase=...) "
                   "or typed at a hidden prompt; it must never come from the LLM.",
        "result_format": {"success": "bool", "operation": "str", "message": "str", "output": "str (optional)",
                          "error": "str (on failure)"},
    }
