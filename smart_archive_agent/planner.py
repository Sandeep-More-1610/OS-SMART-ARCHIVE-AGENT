"""Turns one natural-language request into an ordered, validated tool plan.

The planner is deterministic and needs no network or API key, so the agent works
on any Linux machine on its own. When the Agentic Shell's LLM chooses tools
instead, it calls tools.registry.execute_tool() with the same schemas this
module validates against. Every plan passes validate_plan() and is shown to the
user before anything touches the filesystem.
"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from smart_archive_agent.intent import classify, _paths, PATH_RE, VOCABULARY

VOCABULARY_BY_OP = dict(VOCABULARY)
from smart_archive_agent.tools.archive import archive_format_for
from smart_archive_agent.tools.registry import check_arguments

@dataclass
class Step:
    tool: str
    args: dict
    reason: str = ""

@dataclass
class Plan:
    status: str                      # ok | missing | unrelated | unknown | exit
    steps: list[Step] = field(default_factory=list)
    message: str = ""
    missing: list[str] = field(default_factory=list)
    operation: str = ""

HEAVY_RE = re.compile(r"\b(heav(y|ily)|maximum|max(imum)?\s+compression|as\s+small\s+as\s+possible|"
                      r"as\s+small\s+as\s+(you|it)\s+can|smallest|tiny|strong(ly)?|tight(ly)?|"
                      r"best\s+compression|ultra|squeeze)\b", re.I)
FAST_RE = re.compile(r"\b(fast(est)?|quick(ly)?|light(ly)?|low\s+compression)\b", re.I)
PACKAGE_RE = VOCABULARY_BY_OP["create_archive"]
ZIP_FORMAT_RE = re.compile(r"(\.zip\b|\bzip\s+(file|format|archive)\b|\bas\s+a\s+zip\b)", re.I)
ENCRYPT_RE = VOCABULARY_BY_OP["encrypt_file"]
COMPRESS_RE = VOCABULARY_BY_OP["compress_file"]
FOLDER_RE = re.compile(r"\b(?:my|the|this)\s+([\w.-]+)\s+(?:folder|directory|dir)\b", re.I)

EXTENSIONS = {"xz": ".tar.xz", "gz": ".tar.gz", "bz2": ".tar.bz2", "none": ".tar", "zip": ".zip"}

def _explicit_algorithm(low: str) -> str | None:
    if re.search(r"\bgzip\b|\bgz\b", low):
        return "gz"
    if re.search(r"\bbzip2?\b|\bbz2\b", low):
        return "bz2"
    if re.search(r"\bxz\b|\blzma\b", low):
        return "xz"
    return None

def _level(low: str) -> str:
    if HEAVY_RE.search(low):
        return "max"
    if FAST_RE.search(low):
        return "fast"
    return "normal"

def _folder_from_phrase(low: str) -> str | None:
    if re.search(r"\b(current|working)\s+(folder|directory|dir)\b|\bthis\s+(folder|directory|project)\b", low):
        return "."
    match = FOLDER_RE.search(low)
    if not match:
        return None
    name = match.group(1)
    if name in {"project", "current", "working", "this", "own"}:
        return "./" + name if Path(name).is_dir() else "."
    for candidate in (Path(name), Path(os.path.expanduser("~")) / name):
        if candidate.is_dir():
            return str(candidate) if candidate.is_absolute() else "./" + name
    return "./" + name

def _abs(raw: str) -> Path:
    return Path(os.path.expanduser(raw)).resolve()

def _unique(path: Path) -> Path:
    if not path.exists():
        return path
    suffix = "".join(s for s in path.suffixes if len(s) <= 5)
    stem = path.name[: len(path.name) - len(suffix)] if suffix else path.name
    n = 1
    while (candidate := path.with_name(f"{stem}-{n}{suffix}")).exists():
        n += 1
    return candidate

def _strip_suffix(name: str, suffixes: tuple[str, ...]) -> str:
    for suffix in suffixes:
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return name

def plan_local(text: str) -> Plan:
    intent = classify(text)
    low = text.lower()
    if intent.operation in {"exit", "unknown", "unrelated"}:
        return Plan(intent.operation, message=intent.message, operation=intent.operation)

    paths = _paths(text)
    words = PATH_RE.sub(" ", low)   # keywords are matched with the file paths removed
    op = intent.operation
    level = _level(words)
    algorithm = _explicit_algorithm(words)

    if op == "decrypt_file":
        return _plan_decrypt(words, paths)
    if op == "extract_archive":
        if not paths:
            return Plan("missing", missing=["archive_path"], operation=op,
                        message="Which archive should I extract?")
        dest = paths[1] if len(paths) > 1 else str(_unique(_abs(paths[0]).with_name(
            _strip_suffix(_abs(paths[0]).name, tuple(EXTENSIONS.values()) + (".tbz2", ".tgz", ".txz")) + "-extracted")))
        return Plan("ok", [Step("extract_archive", {"archive_path": paths[0], "destination_path": dest},
                                "unpack the archive safely")], operation=op)
    if op == "decompress_file":
        if not paths:
            return Plan("missing", missing=["source_path"], operation=op,
                        message="Which compressed file should I decompress?")
        out = paths[1] if len(paths) > 1 else str(_unique(_abs(_strip_suffix(paths[0], (".gz", ".bz2", ".xz")))))
        return Plan("ok", [Step("decompress_file", {"source_path": paths[0], "output_path": out},
                                "restore the original file")], operation=op)
    if op == "list_archive":
        if not paths:
            return Plan("missing", missing=["archive_path"], operation=op,
                        message="Which archive should I look inside?")
        tool = "inspect_archive" if "inspect" in words else "list_archive"
        return Plan("ok", [Step(tool, {"archive_path": paths[0]}, "read the archive without extracting")],
                    operation=tool)
    return _plan_package(text, words, op, paths, level, algorithm)

def _plan_decrypt(low: str, paths: list[str]) -> Plan:
    if not paths:
        return Plan("missing", missing=["source_path"], operation="decrypt_file",
                    message="Which .gpg file should I decrypt?")
    source = paths[0]
    wants_extract = VOCABULARY_BY_OP["extract_archive"].search(low) is not None
    if len(paths) > 1 and not wants_extract:
        out = paths[1]
    else:
        out = str(_unique(_abs(_strip_suffix(source, (".gpg",)) if source.lower().endswith(".gpg")
                               else source + ".decrypted")))
    steps = [Step("decrypt_file", {"source_path": source, "output_path": out}, "decrypt with your passphrase")]
    if wants_extract and archive_format_for(out):
        base = _abs(out)
        dest = paths[1] if len(paths) > 1 else str(_unique(base.with_name(
            _strip_suffix(base.name, tuple(EXTENSIONS.values())) + "-extracted")))
        steps.append(Step("extract_archive", {"archive_path": out, "destination_path": dest},
                          "unpack the decrypted archive"))
        steps.append(Step("remove_intermediate", {"path": out}, "remove the temporary decrypted archive"))
    return Plan("ok", steps, operation="decrypt_file")

def _plan_package(text: str, words: str, op: str, paths: list[str], level: str, algorithm: str | None) -> Plan:
    source = paths[0] if paths else _folder_from_phrase(words)
    if not source:
        return Plan("missing", missing=["source_path"], operation=op,
                    message="I recognized an archive-related request, but need these details: source_path")
    source_abs = _abs(source)
    if source_abs == Path(source_abs.anchor):
        return Plan("unrelated", operation=op, message="Archiving the whole root filesystem is not allowed.")
    rest = paths[1:]
    gpg_out = next((p for p in rest if p.lower().endswith(".gpg")), None)
    named_out = next((p for p in rest if not p.lower().endswith(".gpg")), None)
    wants_encrypt = ENCRYPT_RE.search(words) is not None
    named_archive = named_out is not None and archive_format_for(named_out) is not None
    wants_archive = (op == "create_archive" or source_abs.is_dir() or named_archive
                     or PACKAGE_RE.search(words) is not None)
    wants_compress = COMPRESS_RE.search(words) is not None

    steps: list[Step] = []
    packed = None
    if wants_archive:
        fmt = (archive_format_for(named_out) if named_archive else None) or               ("zip" if ZIP_FORMAT_RE.search(words) else algorithm or ("gz" if level == "fast" else "xz"))
        packed = named_out if named_archive else str(_unique(source_abs.parent / (source_abs.name + EXTENSIONS[fmt])))
        steps.append(Step("create_archive", {"source_path": source, "output_path": packed,
                                             "compression": fmt, "level": level},
                          f"bundle into one {fmt} archive ({level} compression)"))
    elif wants_compress:
        algo = algorithm or ("gz" if level == "fast" else "xz")
        packed = named_out or str(_unique(Path(str(source_abs) + "." + algo)))
        steps.append(Step("compress_file", {"source_path": source, "output_path": packed,
                                            "algorithm": algo, "level": level},
                          f"compress with {algo} ({level} level)"))
    if wants_encrypt:
        enc_source = packed or source
        enc_out = gpg_out or (named_out if packed is None else None) or                   str(_unique(Path(str(_abs(enc_source)) + ".gpg")))
        steps.append(Step("encrypt_file", {"source_path": enc_source, "output_path": enc_out},
                          "encrypt with GPG AES-256"))
    if not steps:
        return Plan("missing", missing=["output_path"], operation=op,
                    message="I recognized an archive-related request, but need these details: output_path")
    return finalize_plan(Plan("ok", steps, operation=steps[0].tool if len(steps) == 1 else "plan"), text)

def finalize_plan(plan: Plan, text: str) -> Plan:
    """Delete an agent-named plaintext archive once it has been encrypted.

    If the user typed the intermediate path themselves, it is kept.
    """
    produced = {}
    for i, step in enumerate(plan.steps):
        if step.tool in {"create_archive", "compress_file"}:
            produced[str(_abs(step.args["output_path"]))] = step.args["output_path"]
        if step.tool == "encrypt_file":
            src = str(_abs(step.args["source_path"]))
            named_by_user = produced.get(src, "") in text
            already = any(s.tool == "remove_intermediate" and str(_abs(s.args["path"])) == src
                          for s in plan.steps[i + 1:])
            if src in produced and not named_by_user and not already:
                plan.steps.insert(i + 1, Step("remove_intermediate", {"path": produced[src]},
                                              "delete the unencrypted copy so only the .gpg file remains"))
                break
    return plan

def validate_plan(plan: Plan) -> list[str]:
    """Return a list of problems; an empty list means the plan is safe to show and run."""
    problems = []
    produced: set[str] = set()
    for n, step in enumerate(plan.steps, 1):
        if step.tool == "remove_intermediate":
            path = step.args.get("path")
            if not isinstance(path, str) or str(_abs(path)) not in produced:
                problems.append(f"step {n}: may only delete a file created earlier in this plan")
            continue
        problems += [f"step {n}: {p}" for p in check_arguments(step.tool, step.args)]
        for key in ("output_path", "destination_path"):
            if isinstance(step.args.get(key), str):
                produced.add(str(_abs(step.args[key])))
    return problems

def describe(plan: Plan) -> list[str]:
    lines = []
    for n, step in enumerate(plan.steps, 1):
        a = step.args
        if step.tool == "create_archive":
            what = f"Archive {_abs(a['source_path'])} -> {_abs(a['output_path'])}"
        elif step.tool in {"compress_file", "decompress_file", "encrypt_file", "decrypt_file"}:
            what = f"{step.tool.split('_')[0].capitalize()} {_abs(a['source_path'])} -> {_abs(a['output_path'])}"
        elif step.tool == "extract_archive":
            what = f"Extract {_abs(a['archive_path'])} -> {_abs(a['destination_path'])}"
        elif step.tool == "remove_intermediate":
            what = f"Delete temporary file {_abs(a['path'])}"
        else:
            what = f"{step.tool} {_abs(a['archive_path'])}"
        lines.append(f"{n}. {what}" + (f"  ({step.reason})" if step.reason else ""))
    return lines
