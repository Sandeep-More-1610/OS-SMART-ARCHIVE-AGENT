from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path

# Allow `python smart_archive_agent/main.py` as well as `python -m smart_archive_agent`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smart_archive_agent.agent import run, handle_request, print_result, confirm_in_terminal
from smart_archive_agent.tools.registry import ask_passphrase
from smart_archive_agent.manifest import get_manifest, VERSION

# Linux utility -> Ubuntu/Debian package that provides it.
REQUIRED_UTILITIES = {"tar": "tar", "gzip": "gzip", "bzip2": "bzip2", "xz": "xz-utils",
                      "gpg": "gnupg", "file": "file"}

USAGE = """Usage:
  python -m smart_archive_agent                  interactive shell
  python -m smart_archive_agent "<request>"      run one request
  python -m smart_archive_agent --yes "<...>"    run without the confirmation prompt
  python -m smart_archive_agent --doctor         check that required Linux tools are installed
  python -m smart_archive_agent --manifest       print the agent description for the Agentic Shell
  python -m smart_archive_agent --version        print the version
(After `pip install`, `smart-archive-agent` works in place of `python -m smart_archive_agent`.)"""

def doctor() -> int:
    ok = sys.version_info >= (3, 8)
    print(f"[{'ok' if ok else 'MISSING'}] Python {sys.version.split()[0]} (3.8 or newer required)")
    missing = []
    for tool, package in REQUIRED_UTILITIES.items():
        found = shutil.which(tool)
        print(f"[{'ok' if found else 'MISSING'}] {tool:6} {found or ''}")
        if not found:
            missing.append(package)
    if missing:
        print("\nInstall the missing tools with:\n  sudo apt install " + " ".join(missing))
    else:
        print("\nAll required tools are installed.")
    return 0 if ok and not missing else 1

def main(argv: list[str]) -> int:
    args = list(argv)
    if args and args[0] in {"-h", "--help"}:
        print(USAGE)
        return 0
    if args and args[0] == "--doctor":
        return doctor()
    if args and args[0] == "--manifest":
        print(json.dumps(get_manifest(), indent=2))
        return 0
    if args and args[0] == "--version":
        print(VERSION)
        return 0
    auto_yes = bool(args) and args[0] in {"-y", "--yes"}
    if auto_yes:
        args = args[1:]
    if not args:
        run(auto_yes=auto_yes)
        return 0
    result = handle_request(" ".join(args), confirm=None if auto_yes else confirm_in_terminal,
                            passphrase=ask_passphrase)
    print_result(result)
    return 0 if result.get("success") else 1

def cli() -> None:
    """Entry point for the `smart-archive-agent` command installed by pip."""
    sys.exit(main(sys.argv[1:]))

if __name__ == "__main__":
    cli()
