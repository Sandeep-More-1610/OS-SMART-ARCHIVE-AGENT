"""Minimal example of how the Agentic Shell can plug in the Smart Archive Agent.

Runs without any LLM or network: the "router" scores agents by keyword and the
"LLM tool call" is a hard-coded dictionary in the same shape an OpenAI-compatible
API (OpenAI, Ollama, vLLM, ...) returns. Replace those two parts with the real LLM.

    python3 examples/agentic_shell_example.py
"""
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # not needed after `pip install`

# 1. The shell loads every agent package by name (the other 34 would be listed here too).
AGENT_PACKAGES = ["smart_archive_agent"]
agents = {}
for package in AGENT_PACKAGES:
    module = importlib.import_module(package)
    manifest = module.get_manifest()
    agents[manifest["name"]] = (module, manifest)
    print(f"Loaded agent #{manifest['agent_id']} {manifest['display_name']} v{manifest['version']}")

# 2. The shell's LLM sees every agent's tools. Prefixed names keep 35 agents' tools unique.
all_tools = []
for module, _ in agents.values():
    all_tools += module.get_tools("openai", prefixed=True)
print(f"{len(all_tools)} tools offered to the LLM, e.g. {all_tools[0]['function']['name']}")

# 3. Routing. A real shell asks its LLM; this placeholder counts manifest keywords.
def route(text: str):
    words = text.lower()
    scores = {name: sum(k in words for k in m["routing_keywords"]) for name, (_, m) in agents.items()}
    best = max(scores, key=scores.get)
    return agents[best][0] if scores[best] else None

workdir = Path(tempfile.mkdtemp())
(workdir / "project").mkdir()
(workdir / "project" / "notes.txt").write_text("hello from the Agentic Shell\n" * 500)
os.chdir(workdir)

request = "Zip up my project folder, compress it heavily, and encrypt it."
agent = route(request)
print(f"\nRouted {request!r} to {agent.AGENT_NAME}")

# 4a. Path A: the LLM chose tools. This is the shape of an OpenAI-style tool call;
#     `arguments` arrives as a JSON string and can be passed straight through.
llm_tool_calls = [
    {"function": {"name": "smart_archive__create_archive",
                  "arguments": json.dumps({"source_path": "./project", "output_path": "./project.tar.xz",
                                           "compression": "xz", "level": "max"})}},
    {"function": {"name": "smart_archive__list_archive",
                  "arguments": json.dumps({"archive_path": "./project.tar.xz"})}},
]
for call in llm_tool_calls:
    owner = next(m for m, _ in agents.values() if call["function"]["name"].startswith(m.TOOL_PREFIX))
    result = owner.execute_tool(call["function"]["name"], call["function"]["arguments"])
    print(f"  {call['function']['name']}: success={result['success']} {result['message']}")
    # A real shell sends json.dumps(result) back to the LLM as the tool result.

# 4b. Path B: no LLM available. Hand the whole sentence to the agent's own planner.
#     confirm= and passphrase= let the shell supply its own UI instead of terminal prompts.
os.remove("project.tar.xz")
result = agent.handle_request(request, confirm=lambda plan: True, passphrase="example-passphrase")
print(f"\nhandle_request: success={result['success']}")
for line in result.get("plan", []):
    print("  " + line)
print("  output:", result.get("output") or result.get("error"))
