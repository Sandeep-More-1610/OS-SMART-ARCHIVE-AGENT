"""Tool definitions for LLM function calling, and the single entry point that runs them.

The Agentic Shell's LLM reads get_tools(), picks a tool and arguments, and the shell
calls execute_tool(name, args). The schemas are plain JSON Schema, so they work with
any provider; get_tools() can also return them in OpenAI or Anthropic wrapping.
"""
from __future__ import annotations
import getpass
import json
import sys

from smart_archive_agent.tools import archive, encryption
from smart_archive_agent.security.validation import ValidationError

def _schema(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required,
            "additionalProperties": False}

def _path(description: str) -> dict:
    return {"type": "string", "description": description}

LEVEL = {"type": "string", "enum": ["fast", "normal", "max"],
         "description": "Compression effort. Use 'max' when the user says heavily, maximum or "
                        "as small as possible; 'fast' for quick; otherwise 'normal'."}

TOOL_SCHEMAS = [
    {"name": "create_archive",
     "description": "Bundle a file or folder into one archive (tar, tar.gz, tar.bz2, tar.xz or zip). "
                    "Use this for folders before compressing or encrypting them.",
     "parameters": _schema({
         "source_path": _path("File or folder to archive."),
         "output_path": _path("Archive file to create, e.g. ./project.tar.xz. Must not exist yet."),
         "compression": {"type": "string", "enum": ["auto", "none", "gz", "bz2", "xz", "zip"],
                         "description": "Format. 'auto' infers it from the output file extension."},
         "level": LEVEL}, ["source_path", "output_path"])},
    {"name": "extract_archive",
     "description": "Safely extract a tar or zip archive into a folder. Blocks path traversal (Zip Slip) and links.",
     "parameters": _schema({
         "archive_path": _path("Archive to extract."),
         "destination_path": _path("Folder to extract into; created if missing.")},
         ["archive_path", "destination_path"])},
    {"name": "list_archive",
     "description": "List the files inside an archive without extracting it.",
     "parameters": _schema({"archive_path": _path("Archive to list.")}, ["archive_path"])},
    {"name": "inspect_archive",
     "description": "Report an archive's type, entry count and a preview of its entries.",
     "parameters": _schema({"archive_path": _path("Archive to inspect.")}, ["archive_path"])},
    {"name": "compress_file",
     "description": "Compress one single file (not a folder) with gzip, bzip2 or xz.",
     "parameters": _schema({
         "source_path": _path("File to compress."),
         "output_path": _path("Compressed file to create, e.g. ./data.csv.xz."),
         "algorithm": {"type": "string", "enum": ["gz", "bz2", "xz"]},
         "level": LEVEL}, ["source_path", "output_path"])},
    {"name": "decompress_file",
     "description": "Decompress a .gz, .bz2 or .xz file.",
     "parameters": _schema({
         "source_path": _path("Compressed file."),
         "output_path": _path("Decompressed file to create.")}, ["source_path", "output_path"])},
    {"name": "encrypt_file",
     "description": "Encrypt one file with GPG symmetric AES-256. The passphrase is collected "
                    "securely by the shell, never passed by the model.",
     "parameters": _schema({
         "source_path": _path("File to encrypt (archive folders first)."),
         "output_path": _path("Encrypted file to create, usually ending in .gpg.")},
         ["source_path", "output_path"])},
    {"name": "decrypt_file",
     "description": "Decrypt a GPG-encrypted file. The passphrase is collected securely by the shell.",
     "parameters": _schema({
         "source_path": _path("Encrypted .gpg file."),
         "output_path": _path("Decrypted file to create.")}, ["source_path", "output_path"])},
]

FUNCTIONS = {
    "create_archive": archive.create_archive,
    "extract_archive": archive.extract_archive,
    "list_archive": archive.list_archive,
    "inspect_archive": archive.inspect_archive,
    "compress_file": archive.compress_file,
    "decompress_file": archive.decompress_file,
    "encrypt_file": encryption.encrypt_file,
    "decrypt_file": encryption.decrypt_file,
}
NEEDS_PASSPHRASE = {"encrypt_file", "decrypt_file"}
READ_ONLY_TOOLS = {"list_archive", "inspect_archive"}

# With 35 agents in one shell, tool names can collide; prefixed=True makes them unique.
TOOL_PREFIX = "smart_archive__"

def get_tools(style: str = "generic", prefixed: bool = False) -> list[dict]:
    """Tool definitions: 'generic' (name/description/parameters), 'openai' or 'anthropic'."""
    tools = [dict(t, name=TOOL_PREFIX + t["name"] if prefixed else t["name"]) for t in TOOL_SCHEMAS]
    if style == "openai":
        return [{"type": "function", "function": t} for t in tools]
    if style == "anthropic":
        return [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
                for t in tools]
    if style != "generic":
        raise ValueError("style must be 'generic', 'openai' or 'anthropic'")
    return tools

def check_arguments(name: str, args: dict) -> list[str]:
    """Validate a model-proposed call against its schema; returns a list of problems."""
    schema = next((t["parameters"] for t in TOOL_SCHEMAS if t["name"] == name), None)
    if schema is None:
        return [f"unknown tool '{name}'"]
    if not isinstance(args, dict):
        return ["arguments must be an object"]
    problems = [f"missing argument '{k}'" for k in schema["required"] if k not in args]
    for key, value in args.items():
        spec = schema["properties"].get(key)
        if spec is None:
            problems.append(f"unexpected argument '{key}'")
        elif not isinstance(value, str) or not value.strip():
            problems.append(f"argument '{key}' must be a non-empty string")
        elif "enum" in spec and value not in spec["enum"]:
            problems.append(f"argument '{key}' must be one of {spec['enum']}")
    return problems

def ask_passphrase(tool: str) -> str:
    if not sys.stdin.isatty():
        raise ValidationError("A passphrase is required; pass passphrase= when calling non-interactively.")
    first = getpass.getpass("Passphrase: ")
    if tool == "encrypt_file" and getpass.getpass("Repeat passphrase: ") != first:
        raise ValidationError("Passphrases did not match.")
    return first

def execute_tool(name: str, args: dict, passphrase: str | None = None) -> dict:
    """Run one tool call. Never raises: failures come back as {'success': False, ...}.

    `name` may carry the TOOL_PREFIX; `args` may be a dict or the JSON string an LLM API returns.
    """
    if isinstance(name, str) and name.startswith(TOOL_PREFIX):
        name = name[len(TOOL_PREFIX):]
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            return {"success": False, "operation": name, "error": "arguments are not valid JSON",
                    "message": "The tool call was rejected before execution."}
    problems = check_arguments(name, args)
    if problems:
        return {"success": False, "operation": name, "error": "; ".join(problems),
                "message": "The tool call was rejected before execution."}
    try:
        kwargs = dict(args)
        if name in NEEDS_PASSPHRASE:
            kwargs["passphrase"] = passphrase or ask_passphrase(name)
        return FUNCTIONS[name](**kwargs)
    except Exception as exc:
        return {"success": False, "operation": name, "error": str(exc),
                "message": "The operation could not be completed. Review the error and try again."}
