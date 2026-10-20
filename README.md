# TEAM 12 — Smart Archive Agent

**MEMBERS:**
- **KUSH AGHERA** (24BCE0149)
- **SANDEEP MORE** (24BCE2883)

---

## Overview

**Smart Archive Agent** is an autonomous, security-centric file archiving, compression, and cryptographic protection system running on Ubuntu Linux (and WSL 2). It bridges natural-language user commands with safe, deterministic Linux system utilities (`tar`, `gzip`, `bzip2`, `xz`, `file`, `gpg`, `zip`, `unzip`).

### Key Capabilities
- **Natural Language Intent Parsing**: Automatically classifies user commands (create archive, extract, inspect, list, compress, decompress, encrypt, decrypt) and extracts source/output paths.
- **Enterprise-Grade Security Guardrails**:
  - **Zip Slip Prevention**: Scans archive headers before extraction to reject path traversal attacks (`../` and absolute paths).
  - **No Shell Injection**: Executes all system utilities with structured argument lists (`subprocess.run(shell=False)`).
  - **Non-Overwrite Safety**: Rejects overwriting existing files by default.
  - **Disjoint Inode Validation**: Rejects operations where source and destination resolve to the identical file.
  - **Least Privilege**: Runs purely with unprivileged user permissions (strictly avoids `sudo`).
- **Multi-Format Archiving**: `.tar`, `.tar.gz`, `.tar.bz2`, `.tar.xz`, and `.zip`.
- **Cryptographic Protection**: AES-256 symmetric encryption and decryption backed by GnuPG.
- **Dual Execution Modes**: Interactive conversational REPL shell or direct single-command CLI.

---

## Project Structure

```text
smart-archive-agent/
├── app/
│   ├── __init__.py
│   ├── main.py              # CLI and interactive REPL entrypoint
│   ├── agent.py             # Agent orchestrator and tool dispatcher
│   ├── intent.py            # Deterministic intent routing & regex tokenization
│   ├── security/
│   │   ├── __init__.py
│   │   └── validation.py    # Path validation, Zip-Slip guard & checksums
│   └── tools/
│       ├── __init__.py
│       ├── archive.py       # Multi-format archive tools & file compression
│       └── encryption.py    # GPG AES-256 authenticated encryption
├── tests/
│   ├── __init__.py
│   ├── test_end_to_end.py   # Full integration & security tests
│   └── test_intent.py       # Intent router unit tests
├── docs/
│   ├── architecture.png     # High-resolution system architecture diagram
│   ├── workflow.png         # High-resolution request execution workflow
│   ├── PROJECT_MEMORY.md    # Architecture decisions & implementation status
│   ├── Review_1_Smart_Archive_Agent.docx / .pdf
│   ├── Review_2_Smart_Archive_Agent.docx / .pdf
│   ├── Review_3_Smart_Archive_Agent.docx / .pdf
│   ├── Review 1 Template.docx
│   ├── Review 2 Template.docx
│   ├── Review 3 Template.docx
│   ├── architecture.md
│   ├── usage.md
│   └── api.md
├── pytest.ini               # Pytest configuration
├── requirements.txt         # Dependencies specification
├── README.md                # Project documentation
├── .gitignore
└── LICENSE                  # MIT License
```

---

## Setup & Installation

### Ubuntu / WSL 2 System Prerequisites:

```bash
sudo apt update
sudo apt install -y python3 python3-venv tar gzip bzip2 xz-utils gnupg file unzip zip python-is-python3
```

### Installation:

```bash
git clone https://github.com/redrighthand2007/SMART-ARCHIVE-AGENT.git
cd SMART-ARCHIVE-AGENT
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Usage

### 1. Interactive REPL Mode

Launch the agent shell:

```bash
python app/main.py
```

Try commands:
```text
agent> Create an archive of ./app ./app.tar.xz
agent> inspect archive ./app.tar.xz
agent> list archive ./app.tar.xz
agent> Extract ./app.tar.xz into ./restored
agent> compress ./notes.txt ./notes.txt.xz
agent> decompress ./notes.txt.xz ./notes.txt
agent> Encrypt ./backup.tar.xz ./backup.tar.xz.gpg
agent> Decrypt ./backup.tar.xz.gpg ./backup.tar.xz
agent> What is the weather today?    # (Intercepted by scope guardrail)
agent> exit
```

### 2. Direct CLI Mode

Run operations directly without opening the shell:

```bash
# Archive a folder
python app/main.py "Create an archive of ./app ./app.tar.xz"

# Inspect archive contents
python app/main.py "inspect archive ./app.tar.xz"

# Extract archive
python app/main.py "Extract ./app.tar.xz into ./output_folder"
```

---

## Running Automated Tests

Run the complete test suite with `pytest`:

```bash
pytest -v
```

All 14 tests across intent parsing, validation, path traversal defense, and end-to-end execution pass in **under 0.10 seconds**.

---

## Review Reports & Documentation

All formal course review reports are compiled and available in both `.docx` and `.pdf` formats inside [`docs/`](docs/):

| Report | Topics Covered | Formats |
| :--- | :--- | :--- |
| **Review 1** | Introduction, Problem Statement, Objectives, Scope/Limitations, Literature Review, MCP Overview, Comparison Table. | [DOCX](docs/Review_1_Smart_Archive_Agent.docx), [PDF](docs/Review_1_Smart_Archive_Agent.pdf) |
| **Review 2** | System Architecture, 5-stage loop, Fig 3.1, Component Design, Tool Mapping Table, Security Framework, Fig 4.1. | [DOCX](docs/Review_2_Smart_Archive_Agent.docx), [PDF](docs/Review_2_Smart_Archive_Agent.pdf) |
| **Review 3** | Test Cases & Scenarios, Performance Metrics Table, Conclusion, Challenges, Future Work, Chapter 7 Walkthrough. | [DOCX](docs/Review_3_Smart_Archive_Agent.docx), [PDF](docs/Review_3_Smart_Archive_Agent.pdf) |

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
