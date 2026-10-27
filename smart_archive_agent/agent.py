from __future__ import annotations
import os
from pathlib import Path
from typing import Callable

from smart_archive_agent.planner import Plan, plan_local, validate_plan, describe
from smart_archive_agent.security.guardrails import check_request
from smart_archive_agent.tools.registry import execute_tool, READ_ONLY_TOOLS, NEEDS_PASSPHRASE, ask_passphrase
from smart_archive_agent.manifest import AGENT_NAME, AGENT_DESCRIPTION  # noqa: F401  (re-exported)

def _remove_intermediate(path: str, produced: set[str]) -> dict:
    target = Path(os.path.expanduser(path)).resolve()
    if str(target) not in produced or not target.is_file():
        return {"success": False, "operation": "remove_intermediate",
                "error": "Only files created earlier in this request can be removed."}
    target.unlink()
    return {"success": True, "operation": "remove_intermediate", "output": str(target),
            "message": f"Removed temporary file {target}."}

def handle_request(text: str, confirm: Callable[[Plan], bool] | None = None,
                   passphrase: str | Callable[[str], str] | None = None) -> dict:
    """Plan and run one natural-language request.

    confirm: called with the plan before anything is written; return False to cancel.
             None means approved (used by tests and by callers that confirm themselves).
    passphrase: a string, or a function(tool_name) -> str, used for encrypt/decrypt steps.
    """
    reason = check_request(text)
    if reason:
        return {"success": False, "operation": "blocked",
                "message": f"Blocked by safety guardrail: {reason}. "
                           "That request is outside the Smart Archive Agent's scope."}
    plan = plan_local(text)
    if plan.status == "exit":
        return {"success": True, "operation": "exit", "message": "Goodbye."}
    if plan.status in {"unrelated", "unknown"}:
        return {"success": False, "operation": plan.status,
                "message": plan.message or "That request is outside the Smart Archive Agent's scope."}
    if plan.status == "missing":
        return {"success": False, "operation": plan.operation, "missing": plan.missing,
                "message": plan.message}
    problems = validate_plan(plan)
    if problems:
        return {"success": False, "operation": plan.operation, "error": "; ".join(problems),
                "message": "The plan was rejected before execution."}
    plan_lines = describe(plan)
    writes = any(step.tool not in READ_ONLY_TOOLS for step in plan.steps)
    if writes and confirm is not None and not confirm(plan):
        return {"success": False, "operation": "cancelled", "plan": plan_lines,
                "message": "Cancelled. Nothing was changed."}
    return run_plan(plan, passphrase, plan_lines)

def run_plan(plan: Plan, passphrase=None, plan_lines: list[str] | None = None) -> dict:
    results, produced = [], set()
    for step in plan.steps:
        try:
            if step.tool == "remove_intermediate":
                result = _remove_intermediate(step.args["path"], produced)
            else:
                secret = None
                if step.tool in NEEDS_PASSPHRASE:
                    secret = passphrase(step.tool) if callable(passphrase) else passphrase
                result = execute_tool(step.tool, step.args, passphrase=secret)
        except Exception as exc:
            result = {"success": False, "operation": step.tool, "error": str(exc),
                      "message": "The operation could not be completed."}
        results.append(result)
        if not result.get("success"):
            done = len(results) - 1
            result = dict(result)
            result["plan"] = plan_lines or describe(plan)
            result["completed_steps"] = done
            if len(plan.steps) > 1:
                result["message"] = f"Step {done + 1} of {len(plan.steps)} failed; earlier steps completed. " + \
                                    result.get("message", "")
            return result
        for key in ("output", "destination"):
            if result.get(key):
                produced.add(str(Path(result[key]).resolve()))
    if len(results) == 1:
        single = dict(results[0])
        single["plan"] = plan_lines or describe(plan)
        return single
    final = next((r["output"] for r in reversed(results)
                  if r.get("output") and r.get("operation") != "remove_intermediate"), "")
    return {"success": True, "operation": "plan", "steps": results, "output": final,
            "plan": plan_lines or describe(plan),
            "message": " ".join(r.get("message", "") for r in results)}

def print_result(result: dict) -> None:
    print("\nAgent:")
    for step in result.get("steps", []):
        print("  done:", step.get("message", ""))
    if not result.get("steps"):
        print(result.get("message", ""))
    if result.get("success") and result.get("output"):
        print("Output:", result["output"])
    entries = result.get("entries")
    if entries is None and result.get("entries_preview") is not None:
        print(f"Entries: {result.get('entries_count', 0)}")
        entries = result["entries_preview"]
    if entries is not None:
        for item in entries[:30]:
            print(" -", item)
        if len(entries) > 30:
            print(f" ... and {len(entries) - 30} more")
    if result.get("error"):
        print("Error:", result["error"])

def confirm_in_terminal(plan: Plan) -> bool:
    print("\nPlan:")
    for line in describe(plan):
        print("  " + line)
    try:
        return input("Proceed? [y/N]: ").strip().lower() in {"y", "yes"}
    except (EOFError, KeyboardInterrupt):
        return False

def run(auto_yes: bool = False):
    print("Smart Archive Agent")
    print("Archive, compress, extract, inspect, encrypt, and decrypt files in plain English.")
    print("Example: zip up my project folder, compress it heavily, and encrypt it")
    print("Type 'exit' to quit.")
    while True:
        try:
            text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        result = handle_request(text, confirm=None if auto_yes else confirm_in_terminal,
                                passphrase=ask_passphrase)
        if result.get("operation") == "exit":
            print(result["message"])
            break
        print_result(result)
