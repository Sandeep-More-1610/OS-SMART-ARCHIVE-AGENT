"""Run a visible demonstration using fresh sample files, never personal files."""
from pathlib import Path
import sys
import tempfile
import time
import os

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from smart_archive_agent import handle_request
from smart_archive_agent.planner import describe
from smart_archive_agent.tools.encryption import find_gpg


def main():
    demo = ROOT / "demo"
    demo.mkdir(exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="live-", dir=demo))
    source = workspace / "My Project"
    source.mkdir()
    (source / "hello.txt").write_text("Hello Sandeep! Your Smart Archive Agent is working.\n", encoding="utf-8")
    (source / "notes.txt").write_text("This is project data for the live demonstration.\n" * 100, encoding="utf-8")
    packed = workspace / "backup.tar.xz"
    encrypted = workspace / "backup.tar.xz.gpg"
    decrypted = workspace / "decrypted.tar.xz"
    restored = workspace / "restored"

    print("SMART ARCHIVE AGENT - LIVE DEMONSTRATION", flush=True)
    print("Two sample files: hello.txt and notes.txt", flush=True)
    print("Demo folder:", workspace, flush=True)
    os.chdir(workspace)

    def confirm(plan):
        for step in plan.steps:
            print("  PLAN:", step.tool, "-", step.reason, flush=True)
        print("  Approved automatically for these sample files.", flush=True)
        return True

    requests = [
        ("1. CREATE A COMPRESSED BACKUP", 'archive "./My Project" to "./backup.tar.xz" heavily'),
        ("2. INSPECT THE BACKUP", 'inspect archive "./backup.tar.xz"'),
    ]
    if find_gpg():
        requests.extend([
            ("3. ENCRYPT WITH GPG AES-256", 'encrypt "./backup.tar.xz" to "./backup.tar.xz.gpg"'),
            ("4. DECRYPT THE BACKUP", 'decrypt "./backup.tar.xz.gpg" to "./decrypted.tar.xz"'),
        ])
        extraction_source = decrypted
    else:
        print("GPG unavailable: encryption steps skipped.", flush=True)
        extraction_source = packed
    requests.append(("5. EXTRACT AND RESTORE FILES", f'extract "./{extraction_source.name}" into "./restored"'))

    for label, request in requests:
        print("\n" + label, flush=True)
        print("  REQUEST:", request, flush=True)
        result = handle_request(request, confirm=confirm, passphrase="public-demo-passphrase-only")
        if not result.get("success"):
            raise RuntimeError(result)
        print("  SUCCESS:", result.get("message", "Completed").replace(str(workspace) + os.sep, "./"), flush=True)
        for name in result.get("entries_preview", []):
            print("    ", name, flush=True)
        time.sleep(1)

    for original in source.iterdir():
        recovered = restored / source.name / original.name
        if original.read_bytes() != recovered.read_bytes():
            raise RuntimeError("Restored content differs: " + original.name)
        print("\nVERIFIED:", original.name, "restored exactly", flush=True)
    print("\nDEMONSTRATION COMPLETE - ALL STEPS PASSED", flush=True)
    print("Restored files:", restored / source.name, flush=True)


if __name__ == "__main__":
    main()
