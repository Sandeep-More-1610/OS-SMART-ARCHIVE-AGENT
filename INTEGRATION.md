# Integrating Agent #12 — Smart Archive Agent

For the Agentic Shell maintainer. Team 12: Kush Aghera (24BCE0149), Sandeep More (24BCE2883).

## 1. Install, step by step

Works on any Ubuntu or Debian machine (or WSL). Needs Python 3.8+, no Python packages, and no root
except for `apt`. Run every command in a normal **terminal**.

**Step 1 — Install the Linux tools** (one time per machine; skip anything already installed):

```bash
sudo apt install -y python3 python3-venv python3-pip git tar gzip bzip2 xz-utils gnupg file
```

**Step 2 — Go to the Agentic Shell's project folder and use its virtual environment.**
If the shell already has a `.venv`, only activate it. Otherwise create one once:

```bash
cd ~/agentic-shell                # the shell's own folder (use its real path)
python3 -m venv .venv             # only the first time
source .venv/bin/activate         # every new terminal; the prompt then starts with (.venv)
```

A virtual environment is required on Ubuntu 23.04 and newer: a plain `pip install` outside one fails
with `error: externally-managed-environment`.

**Step 3 — Install the agent from GitHub** (same terminal, with `(.venv)` showing):

```bash
pip install git+https://github.com/redrighthand2007/OS-SMART-ARCHIVE-AGENT.git
```

**Step 4 — Check it** (any folder, same terminal):

```bash
smart-archive-agent --doctor       # every line should say [ok]
smart-archive-agent --version      # 1.0.0
```

If `--doctor` shows `[MISSING]`, run the `sudo apt install ...` line it prints, then check again.

**Step 5 — Try one request** (in any folder that has something to archive):

```bash
mkdir -p ~/archive-test/demo && echo "hello" > ~/archive-test/demo/a.txt
cd ~/archive-test
smart-archive-agent --yes "back up ./demo quickly"    # creates ~/archive-test/demo.tar.gz
```

**Step 6 — Use it from the shell's Python code** (Section 2 and Section 4 below).
`import smart_archive_agent` works anywhere while the same `.venv` is active.

**Updating later:** `pip install --upgrade git+https://github.com/redrighthand2007/OS-SMART-ARCHIVE-AGENT.git`

**Without pip (alternative):**

```bash
git clone https://github.com/redrighthand2007/OS-SMART-ARCHIVE-AGENT.git ~/OS-SMART-ARCHIVE-AGENT
export PYTHONPATH=~/OS-SMART-ARCHIVE-AGENT     # in every new terminal, or add to ~/.bashrc
python3 -m smart_archive_agent --doctor
```

## 2. What the shell gets

```python
import smart_archive_agent as archive_agent

archive_agent.get_manifest()       # name, description, routing keywords, tools, requirements (also agent.json)
archive_agent.get_tools("openai", prefixed=True)     # 8 tool schemas for LLM function calling
archive_agent.execute_tool(name, arguments, passphrase=None)   # run one tool call
archive_agent.handle_request(text, confirm=None, passphrase=None)  # plain English, no LLM needed
```

| Function | Notes |
| :--- | :--- |
| `get_manifest()` | `agent_id` 12, `name`, `description` (written for an LLM router, including what this agent does **not** do), `routing_keywords`, `example_prompts`, `requirements`. |
| `get_tools(style, prefixed)` | `style`: `"generic"` (`name`/`description`/`parameters`), `"openai"` (also works for Ollama and other OpenAI-compatible APIs) or `"anthropic"`. `prefixed=True` names tools `smart_archive__create_archive` etc., so they cannot collide with other agents' tools. |
| `execute_tool(name, args, passphrase=None)` | Accepts prefixed or plain names, and `args` as a dict **or** the JSON string an LLM API returns. **Never raises**: unknown tools, missing/extra arguments and invalid values are rejected before anything runs. |
| `handle_request(text, confirm, passphrase)` | Built-in rule-based planner for when no LLM is available. `confirm(plan) -> bool` is called before any file is written (`None` = approved). |

Every call returns a dictionary:

```python
{"success": True, "operation": "create_archive", "message": "Archive created ...", "output": "/abs/path/project.tar.xz"}
{"success": False, "operation": "create_archive", "error": "Output already exists: ...", "message": "..."}
```

`json.dumps(result)` can be sent straight back to the LLM as the tool result.

## 3. Tools

| Tool | Required | Optional |
| :--- | :--- | :--- |
| `create_archive` | `source_path`, `output_path` | `compression` (`auto` from extension, `none`, `gz`, `bz2`, `xz`, `zip`), `level` (`fast`, `normal`, `max`) |
| `extract_archive` | `archive_path`, `destination_path` | |
| `list_archive` | `archive_path` | |
| `inspect_archive` | `archive_path` | |
| `compress_file` | `source_path`, `output_path` | `algorithm` (`gz`, `bz2`, `xz`), `level` |
| `decompress_file` | `source_path`, `output_path` | |
| `encrypt_file` | `source_path`, `output_path` | passphrase given to `execute_tool`, never by the LLM |
| `decrypt_file` | `source_path`, `output_path` | passphrase given to `execute_tool` |

The brief's example, *"Zip up my project folder, compress it heavily, and encrypt it"*, maps to
`create_archive(level="max")` followed by `encrypt_file` on its output.

## 4. Typical loop in the base shell

```python
import json
import smart_archive_agent as archive_agent

tools = archive_agent.get_tools("openai", prefixed=True)      # add the other agents' tools too
# response = client.chat.completions.create(model=..., messages=..., tools=tools)
for call in response.choices[0].message.tool_calls or []:
    if call.function.name.startswith(archive_agent.TOOL_PREFIX):
        result = archive_agent.execute_tool(call.function.name, call.function.arguments,
                                            passphrase=ask_user_secretly_if_needed())
        messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
```

`examples/agentic_shell_example.py` runs this flow end to end without any LLM or network (see Section 7).

## 5. Command line (if the shell prefers subprocesses)

```bash
smart-archive-agent --yes "archive ./src with maximum compression"   # exit code 0 = success
smart-archive-agent --manifest                                       # JSON description
smart-archive-agent                                                  # interactive mode
```

## 6. Safety guarantees

* No `shell=True`: utilities are started with argument lists, so request text is never executed.
* Destructive text (`rm -rf`, `mkfs`, `dd if=`, `; rm`, `$(...)`, a bare `/`) is refused before planning.
* Never writes into `/bin`, `/boot`, `/dev`, `/etc`, `/lib`, `/proc`, `/sbin`, `/sys`, `/usr`, `/var/lib`.
* Never overwrites an existing file; archives are checked for path traversal (Zip Slip) and links before extraction.
* Passphrases go to `gpg` on standard input; they never appear in arguments, logs or results.
* Runs as a normal user; does not need or use `sudo`.

## 7. Run the test suite and the example (optional)

The tests and `examples/` are in the repository, not in the pip package, so clone it first.
Use any folder, with a virtual environment active (Step 2):

```bash
git clone https://github.com/redrighthand2007/OS-SMART-ARCHIVE-AGENT.git ~/OS-SMART-ARCHIVE-AGENT
cd ~/OS-SMART-ARCHIVE-AGENT
pip install pytest
python3 -m pytest -q                              # expected: 58 passed
python3 examples/agentic_shell_example.py         # loads the agent, routes a request, runs tool calls
python3 benchmarks/evaluate.py                    # accuracy, latency and error-recovery numbers
```
