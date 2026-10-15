# Smart Archive Agent Usage Guide

## Quickstart

Run the agent from the command line:

```bash
# Natural Language request
python -m app.main agent "archive app/ to backup.zip and encrypt with password MySecretKey!"

# Interactive Agent Mode
python -m app.main interactive
```

---

## Command Line Interface (CLI)

### 1. Natural Language Agent (`agent`)
```bash
# Archive with auto-detection
python -m app.main agent "archive src into dist.tar.gz"

# Dry run (preview without altering filesystem)
python -m app.main agent "archive logs to logs.zip --dry-run"

# Safe extract with password
python -m app.main agent "extract backup.zip.enc into ./restored with password MySecretKey!"
```

### 2. Manual Archive (`archive`)
```bash
# Basic zip
python -m app.main archive ./src -o bundle.zip

# Filter only specific extensions (.py and .json)
python -m app.main archive ./src -o py_code.tar.gz -f tar.gz --filter-ext .py --filter-ext .json

# Archive and encrypt
python -m app.main archive ./confidential -o confidential.zip --encrypt -p "MyStrongPassword"
```

### 3. Safe Extraction (`extract`)
```bash
python -m app.main extract bundle.zip -d ./output_dir
```

### 4. File Encryption and Decryption (`encrypt` / `decrypt`)
```bash
# Encrypt
python -m app.main encrypt sensitive.txt -o sensitive.txt.enc

# Decrypt
python -m app.main decrypt sensitive.txt.enc -o restored.txt
```

### 5. Inspect and Verify (`list` / `verify`)
```bash
# List contents
python -m app.main list bundle.zip

# Verify integrity and checksums
python -m app.main verify bundle.zip
```

---

## Python API Usage

You can embed the agent inside existing Python applications:

```python
from app.agent import SmartArchiveAgent

agent = SmartArchiveAgent()

# Execute high-level command
result = agent.execute("archive logs/ to logs_backup.zip and encrypt with password Secret42")

if result.success:
    print("Archive created:", result.output_files)
    print("SHA-256:", result.metrics["checksum"])
else:
    print("Failed:", result.error)
```
