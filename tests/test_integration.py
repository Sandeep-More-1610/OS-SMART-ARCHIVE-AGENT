"""The contract the Agentic Shell relies on: manifest, prefixed tools, JSON arguments, packaging."""

import json
import subprocess
import sys
from pathlib import Path

import smart_archive_agent as agent

ROOT = Path(__file__).resolve().parent.parent


def test_manifest_describes_the_agent():
    m = agent.get_manifest()
    assert m["agent_id"] == 12 and m["name"] == "smart_archive_agent"
    assert m["tools"] == [t["name"] for t in agent.get_tools()]
    assert m["requirements"]["python_packages"] == []


def test_agent_json_matches_the_code():
    # Regenerate with: python3 -m smart_archive_agent --manifest > agent.json
    assert json.loads((ROOT / "agent.json").read_text()) == agent.get_manifest()


def test_pyproject_version_matches():
    assert f'version = "{agent.__version__}"' in (ROOT / "pyproject.toml").read_text()


def test_prefixed_tool_names_are_unique_and_accepted(tmp_path):
    names = [t["function"]["name"] for t in agent.get_tools("openai", prefixed=True)]
    assert all(n.startswith(agent.TOOL_PREFIX) for n in names) and len(set(names)) == len(names)
    src = tmp_path / "a"
    src.mkdir()
    (src / "x.txt").write_text("x")
    result = agent.execute_tool(agent.TOOL_PREFIX + "create_archive",
                                json.dumps({"source_path": str(src), "output_path": str(tmp_path / "a.tar.gz")}))
    assert result["success"], result


def test_invalid_json_arguments_are_rejected():
    result = agent.execute_tool("list_archive", "{not json")
    assert result["success"] is False and "JSON" in result["error"]


def test_command_line_manifest_and_example_run():
    out = subprocess.run([sys.executable, "-m", "smart_archive_agent", "--manifest"], cwd=ROOT,
                         capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL)
    assert json.loads(out.stdout)["agent_id"] == 12
    example = subprocess.run([sys.executable, str(ROOT / "examples" / "agentic_shell_example.py")],
                             capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120)
    assert example.returncode == 0, example.stderr
    assert "handle_request: success=True" in example.stdout
