# TEAM 12- Smart Archive Agent

**MEMBERS:**
- **KUSH AGHERA** (24BCE0149)
- **SANDEEP MORE** ()

---

## Overview

**Smart Archive Agent** is an intelligent, security-first archiving and encryption system. It allows users to manage, compress, extract, verify, and encrypt files using either natural language commands or a rich CLI.

### Key Features
- **Natural Language Intent Parsing**: Automatically detects user intentions (archive, extract, encrypt, decrypt, list, verify) with smart format and filter deduction.
- **Enterprise-Grade Security**:
  - **Zip Slip Prevention**: Guards against path traversal directory escapes (`../`, drive letters, and root escapes).
  - **Decompression Bomb Detection**: Inspects archive headers to protect against excessive compression ratios and memory flooding.
  - **Constant-time Hash Verification**: Verifies SHA-256 integrity checks without timing side channels.
- **Authenticated Cryptography**: Uses AES-256-GCM authenticated cipher with PBKDF2-HMAC-SHA256 key derivation.
- **Multi-Format Support**: `.zip`, `.tar`, `.tar.gz` (`.tgz`), `.tar.bz2`, and `.tar.xz`.
- **Execution Auditing**: Immutable audit records for every action taken, with timestamps, output paths, and SHA-256 hashes.
- **Interactive REPL & CLI**: Interactive chat session or standalone CLI commands.

---

## Project Structure

```text
smart-archive-agent/
├── app/
│   ├── __init__.py
│   ├── main.py              # CLI and interactive REPL entrypoint
│   ├── agent.py             # Agent orchestrator and planning
│   ├── intent.py            # Natural language intent parser
│   ├── security/
│   │   ├── __init__.py
│   │   └── validation.py    # Path traversal & zip bomb prevention
│   └── tools/
│       ├── __init__.py
│       ├── archive.py       # Multi-format archive tools & filters
│       └── encryption.py    # AES-256-GCM authenticated encryption
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_archive.py
│   ├── test_encryption.py
│   ├── test_intent.py
│   └── test_validation.py
├── docs/
│   ├── architecture.md
│   ├── usage.md
│   └── api.md
├── requirements.txt
├── README.md
├── .gitignore
└── LICENSE
```

---

## Installation

```bash
git clone https://github.com/redrighthand2007/SMART-ARCHIVE-AGENT.git
cd SMART-ARCHIVE-AGENT
pip install -r requirements.txt
```

---

## Quickstart

### 1. Natural Language Agent
```bash
# Archive with natural language
python -m app.main agent "archive app/ into backup.tar.gz"

# Archive and encrypt with password
python -m app.main agent "archive app/ into secure.zip and encrypt with password MySecret123"

# Dry run simulation
python -m app.main agent "archive app/ into test.zip --dry-run"

# Safe extraction
python -m app.main agent "extract secure.zip into ./restored with password MySecret123"
```

### 2. Interactive Mode
```bash
python -m app.main interactive
```

### 3. Dedicated CLI Commands
```bash
# Direct archive
python -m app.main archive ./app -o app_backup.zip

# List contents
python -m app.main list app_backup.zip

# Verify archive integrity
python -m app.main verify app_backup.zip

# Encrypt & Decrypt files
python -m app.main encrypt secret.txt -o secret.txt.enc
python -m app.main decrypt secret.txt.enc -o secret_restored.txt
```

---

## Running Tests

Run the test suite with `pytest`:

```bash
pytest -v
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
