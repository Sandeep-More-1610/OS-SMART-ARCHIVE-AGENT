# Smart Archive Agent — Personal Reference & Viva Guide
**Team 12 (Kush Aghera & Sandeep More)**

> Keep this open during the review. It has the exact demo commands, short answers to likely questions, and file locations.

---

## 1. Live demonstration (about 3 minutes)

In the Ubuntu (WSL) terminal, prepare a small demo folder once (so the archive is small and quick):

```bash
mkdir -p ~/demo/project && cp -r ~/SMART-ARCHIVE-AGENT/docs ~/demo/project/
cd ~/demo/project
export PYTHONPATH=~/SMART-ARCHIVE-AGENT
python3 -m smart_archive_agent --doctor
```
*Say:* "It checks that Python and tar, gzip, bzip2, xz, gpg and file are installed, so it runs on any Ubuntu machine, including the lab's."

```bash
python3 -m smart_archive_agent
```

> Before a second rehearsal, clear old outputs: `rm -f ~/demo/project.tar.xz.gpg ~/demo/project/docs.tar.gz; rm -rf ~/demo/project-extracted`

Then type, in order:

1. **The brief's own example (chaining):**
   ```text
   Zip up my project folder, compress it heavily, and encrypt it.
   ```
   *Say:* "The planner turns one sentence into three steps: a tar.xz at maximum compression, xz -9e because of the word 'heavily'; GPG AES-256 encryption; and deleting the unencrypted copy. It shows the plan with absolute paths and runs nothing until I type y. The passphrase is typed hidden and sent to gpg on stdin, never as an argument."
   Answer `y`, then enter a passphrase twice.

   The result is `~/demo/project.tar.xz.gpg`.

2. **Fast compression and inspection without extracting:**
   ```text
   archive ./docs quickly
   inspect archive ./docs.tar.gz
   ```
   *Say:* "'quickly' selects gzip -1. Inspect reads the header and member list without writing anything."

3. **Decrypt and extract in one sentence:**
   ```text
   decrypt ../project.tar.xz.gpg and extract it
   ```
   The files appear in `~/demo/project-extracted/`.

4. **Guardrails:**
   ```text
   rm -rf /
   archive ./docs; rm -rf ~
   What is the weather today?
   ```
   *Say:* "The first two are blocked by the regex blacklist before any planning. The third is outside this agent's scope, so the shell's router would send it to another agent."

5. `exit`

6. **Tests and measurements:**
   ```bash
   cd ~/SMART-ARCHIVE-AGENT
   python3 -m pytest -q
   python3 benchmarks/evaluate.py
   ```
   *Say:* "58 tests pass. The benchmark measures intent accuracy on a held-out set, latency, and error recovery."

---

## 2. Viva questions and answers

**Q: Where is the LLM?**
"In the Agentic Shell the base shell owns the LLM. Our job, as the brief says, is to define Linux capabilities as tools for function calling. `get_tools()` returns JSON Schema definitions of our eight tools, and `execute_tool()` runs the one the LLM picks. The model can only choose among those tools with schema-checked arguments; it never writes a shell command. We also built a rule-based planner so the agent works on any lab machine with no API key or network."

**Q: How will the teacher integrate it?**
"`from smart_archive_agent import get_tools, execute_tool, handle_request`. The package name is unique, so it won't clash with the other 34 agents. It needs only the Python standard library."

**Q: How does 'heavily' change anything?**
"The planner maps heavily / maximum / as small as possible to level `max`, which is `xz -9e`, gzip -9 or bzip2 -9. Quick / fast maps to `fast` (gzip -1). The benchmark shows the trade-off: bzip2 is the slowest, and xz max costs about 1.8× the time of xz normal."

**Q: How accurate is the intent recognition?**
"80% on 20 held-out phrasings we never tuned on, and 100% on the 65 development phrasings. A first held-out set scored only 50%, which showed that keyword lists don't generalise. We rewrote the vocabulary with whole-word matching and then wrote a fresh held-out set. All four remaining misses were safe failures, and this is exactly why the shell's LLM sits in front."

**Q: How do you prevent Zip Slip?**
"In `extract_archive`, every member path is resolved against the destination and must stay inside it, and symlinks or hard links are refused. This happens before the destination folder is even created. On Python 3.12+ we also use tarfile's `data` filter."

**Q: Why `subprocess.run` with a list?**
"With `shell=True` a string like `; rm -rf /` would be executed by the shell. We pass argument lists like `['tar', '-I', 'xz -9e -T0', '-cf', out, '-C', parent, name]`, so user text is only ever data."

**Q: How is the passphrase protected?**
"It's read with `getpass` (hidden), sent to gpg on standard input with `--pinentry-mode loopback --passphrase-fd 0`, and `--no-symkey-cache` stops gpg-agent from caching it. It never appears in the process list, logs or files. A wrong passphrase fails cleanly and leaves no output."

**Q: What if the LLM produces a bad tool call?**
"`execute_tool` validates it against the schema first: unknown tool, missing or extra argument, wrong value. It's rejected with a structured error and nothing runs. Our benchmark sends 18 such bad calls, including Zip Slip, writing to /etc and a wrong passphrase. 18/18 are handled with no crash and no file written."

**Q: Archiving vs compression?**
"Archiving bundles many files into one (tar or zip). Compression shrinks bytes (gzip, bzip2, xz). A folder must be archived before it can be compressed or encrypted, so the planner always puts `create_archive` first for folders."

---

## 3. Files

* Code: `smart_archive_agent/` (`agent.py`, `planner.py`, `intent.py`, `tools/`, `security/`)
* Tests: `tests/` · Benchmark: `benchmarks/evaluate.py`, results in `benchmarks/results.json`
* Reports: `docs/Review_1_…`, `docs/Review_2_…`, `docs/Review_3_Smart_Archive_Agent.docx` / `.pdf`
* GitHub: https://github.com/redrighthand2007/OS-SMART-ARCHIVE-AGENT

## 4. Troubleshooting

* `No module named smart_archive_agent`: run from the repository root, or `export PYTHONPATH=/path/to/repo`.
* `pytest: command not found`: `python3 -m pip install pytest`, then `python3 -m pytest -q`.
* A tool is missing: `python3 -m smart_archive_agent --doctor` prints the `apt install` line.
