# Showcase Guide — Smart Archive Agent (Team 12)

Personal step-by-step guide for demonstrating **only our agent**, either on our own laptop (Windows + WSL Ubuntu)
or on any other Ubuntu PC (for example a lab machine). The talking points and viva answers are in [refer.md](refer.md).

**Time needed:** about 5 minutes for setup B, 3 minutes for the demo.

---

## A. On our laptop (Windows + WSL Ubuntu)

Everything is already installed here. The project lives in Ubuntu at `~/SMART-ARCHIVE-AGENT`.

**Step A1 — Open an Ubuntu terminal.** Use either:
* the Windows **Start menu → type `Ubuntu` → Enter**, or
* **VS Code → File → Open Recent → `SMART-ARCHIVE-AGENT (Workspace) [WSL: Ubuntu]`**, then **Terminal → New Terminal**.

The prompt should look like `adminredrighthand2007@SuperSonic:~$`.

**Step A2 — Get the latest code from GitHub.** *Where:* the Ubuntu terminal.

```bash
cd ~/SMART-ARCHIVE-AGENT
git pull
```

**Step A3 — Check that everything works.** *Where:* same terminal, same folder.

```bash
python3 -m smart_archive_agent --doctor      # every line should say [ok]
python3 -m pytest -q                         # expected: 58 passed
```

**Step A4 — Prepare a fresh demo folder.** *Where:* same terminal. This removes only the old demo outputs in `~/demo`.

```bash
rm -rf ~/demo && mkdir -p ~/demo/project && cp -r ~/SMART-ARCHIVE-AGENT/docs ~/demo/project/
cd ~/demo/project
export PYTHONPATH=~/SMART-ARCHIVE-AGENT
```

Then go to **Section C (the demo)**.

---

## B. On any other Ubuntu PC (lab or teacher's machine), starting from nothing

**Step B1 — Open a terminal.** Press **Ctrl + Alt + T** (or Activities → type `Terminal`).

**Step B2 — Install the tools** (once per PC, needs the PC's password for `sudo`). *Where:* the terminal, any folder.

```bash
sudo apt update
sudo apt install -y git python3 tar gzip bzip2 xz-utils gnupg file python3-pytest
```

If you are not allowed to use `sudo`, skip this step: most Ubuntu PCs already have these. Step B4 tells you if
anything is missing. (`python3-pytest` is only needed for the test run.)

**Step B3 — Download our project.** *Where:* the terminal, in your home folder.

```bash
cd ~
git clone https://github.com/redrighthand2007/OS-SMART-ARCHIVE-AGENT.git
cd OS-SMART-ARCHIVE-AGENT
```

*No `git` or no internet on that PC?* On a PC with internet open
https://github.com/redrighthand2007/OS-SMART-ARCHIVE-AGENT → green **Code** button → **Download ZIP**, copy the
ZIP with a pen drive, then in the terminal: `cd ~ && unzip ~/Downloads/OS-SMART-ARCHIVE-AGENT-main.zip &&
mv OS-SMART-ARCHIVE-AGENT-main OS-SMART-ARCHIVE-AGENT && cd OS-SMART-ARCHIVE-AGENT`.

**Step B4 — Check that everything works.** *Where:* same terminal, inside `~/OS-SMART-ARCHIVE-AGENT`.
No virtual environment or `pip install` is needed for running from this folder.

```bash
python3 -m smart_archive_agent --doctor      # every line should say [ok]
python3 -m pytest -q                         # expected: 58 passed
```

If `--doctor` shows `[MISSING]`, run the `sudo apt install ...` line it prints.

**Step B5 — Prepare a demo folder.** *Where:* same terminal.

```bash
mkdir -p ~/demo/project && cp -r ~/OS-SMART-ARCHIVE-AGENT/docs ~/demo/project/
cd ~/demo/project
export PYTHONPATH=~/OS-SMART-ARCHIVE-AGENT
```

Then go to **Section C (the demo)**.

---

## C. The demo (same on both)

*Where:* the terminal from A4 or B5, inside `~/demo/project`. Start the agent:

```bash
python3 -m smart_archive_agent
```

Type these one at a time at the `You:` prompt:

| # | Type this | Then | What it shows |
|---|---|---|---|
| 1 | `Zip up my project folder, compress it heavily, and encrypt it.` | type `y`, then a passphrase twice (it stays hidden; remember it) | The brief's own example: 3-step plan, xz -9e, GPG AES-256, plaintext copy removed |
| 2 | `archive ./docs quickly` | type `y` | "quickly" → gzip -1 |
| 3 | `inspect archive ./docs.tar.gz` | — | Looks inside without extracting |
| 4 | `decrypt ../project.tar.xz.gpg and extract it` | type `y`, then the same passphrase | Decrypt + extract + clean-up in one sentence; files appear in `~/demo/project-extracted` |
| 5 | `rm -rf /` | — | Blocked by the safety guardrail |
| 6 | `archive ./docs; rm -rf ~` | — | Command injection blocked |
| 7 | `What is the weather today?` | — | Out of scope (belongs to another agent) |
| 8 | `exit` | — | Quits |

**Optional extras** (*where:* the project folder: `~/SMART-ARCHIVE-AGENT` on our laptop, `~/OS-SMART-ARCHIVE-AGENT` on another PC):

```bash
python3 examples/agentic_shell_example.py    # how the teacher's shell plugs our agent in (no LLM needed)
python3 benchmarks/evaluate.py               # accuracy 80% held-out, error recovery 18/18, timings
python3 -m smart_archive_agent --manifest    # the agent's "business card" for the shell's router
```

---

## D. If something goes wrong

| Problem | Fix |
|---|---|
| `No module named smart_archive_agent` | You opened a new terminal: run the `export PYTHONPATH=...` line from A4 / B5 again |
| `No module named pytest` | `sudo apt install -y python3-pytest` (or skip the test run) |
| `[MISSING] gpg` (or another tool) | Run the `sudo apt install ...` line that `--doctor` prints |
| Files are named `project-1.tar.xz.gpg` | Old demo files are still there; redo Step A4 (or `rm -rf ~/demo` and Step B5) |
| Decrypt says `wrong passphrase` | Type the passphrase used in demo step 1. Nothing is written when it is wrong |
| `Output already exists` | The agent never overwrites files; remove the old file or redo Step A4 / B5 |
| `git pull` refuses because of local changes | `git stash` and then `git pull` again |

**After the showcase on someone else's PC** (optional clean-up): `rm -rf ~/demo ~/OS-SMART-ARCHIVE-AGENT`
