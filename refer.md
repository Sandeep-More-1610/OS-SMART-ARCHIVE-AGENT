# Smart Archive Agent — Personal Reference & Viva Guide
**Author Reference Sheet | Team 12 (Kush Aghera & Sandeep More)**

> **Keep this file open or printed during your review/viva presentation.** It contains the exact commands to run in front of the teacher, quick answers to common professor questions, and file paths.

---

## ⚡ 1. Live Demonstration Cheat Sheet (2-Minute Demo)

In your VS Code terminal (WSL Ubuntu: `adminredrighthand2007@SuperSonic:~/SMART-ARCHIVE-AGENT$`), run:

```bash
# Step 1: Activate the virtual environment
source .venv/bin/activate

# Step 2: Launch the Agent
python app/main.py
```

### Type these exact commands in order when showing the teacher:

1. **Create an Archive (Show Packaging + Compression)**:
   ```text
   Create an archive of ./app ./app.tar.xz
   ```
   *Explanation to teacher*: "The agent detects the intent to bundle `./app` using XZ compression, resolves the path, and calls GNU Tar with `-cJf`."

2. **Inspect the Archive (Show Inspection without Extracting)**:
   ```text
   inspect archive ./app.tar.xz
   ```
   *Explanation to teacher*: "The agent inspects file headers and prints the internal structure without decompressing to disk."

3. **Extract the Archive (Show Safe Decompression)**:
   ```text
   Extract ./app.tar.xz into ./restored
   ```
   *Explanation to teacher*: "The agent checks for Zip Slip attacks before extracting to `./restored`."

4. **Show Security Guardrail (Out-of-Scope Protection)**:
   ```text
   Delete everything on my drive
   ```
   *Explanation to teacher*: "The agent checks domain boundaries. Since 'delete' is not an archive operation, it politely blocks the action with: *'That request is outside the Smart Archive Agent's scope.'*"

5. **Exit the Agent**:
   ```text
   exit
   ```

6. **Run Automated Tests (Show 100% Pass Rate)**:
   ```bash
   pytest -v
   ```
   *Result*: All 14 tests pass in `0.07 seconds`.

---

## 🧠 2. Viva / Defense Questions & Bulletproof Answers

### Q1: Why didn't you connect directly to a remote LLM API (like OpenAI GPT-4 or Gemini)?
> **Answer**: "We deliberately separated intent understanding from system execution. Running an unvetted LLM directly against an OS shell creates hallucination and security hazards. Our baseline uses a local deterministic intent router that runs with zero latency, zero cloud cost, and no internet dependency, while matching the exact function schemas required to plug into an LLM or Model Context Protocol (MCP) server."

### Q2: How does your code prevent the Zip Slip vulnerability?
> **Answer**: "In `app/tools/archive.py` (`extract_archive`), before any member is extracted, we resolve the canonical target path using `.resolve()`. We verify that `destination.resolve() in target.parents`. If an archive header contains relative `../` or absolute root paths attempting to escape the destination, it is intercepted and halted with a `ValidationError`."

### Q3: Why do you use `subprocess.run(shell=False)`?
> **Answer**: "When `shell=True` is used, the input string is evaluated by the system shell, which allows shell command chaining like `; rm -rf /` or `| cat /etc/passwd`. By using `shell=False` and passing explicit argument vectors (e.g. `['tar', '-cJf', output, '-C', parent, name]`), parameters are treated strictly as data and cannot execute arbitrary shell syntax."

### Q4: What is the difference between archiving and compression in your project?
> **Answer**: 
> - **Archiving (`create_archive`)**: Bundles multiple files and directories into a single file container (`.tar` or `.zip`).
> - **Compression (`compress_file`)**: Reduces the byte size of an individual file using algorithms like `xz`, `gzip`, or `bzip2`. 
> - We support both standalone file compression and combined compressed archives (`.tar.xz`).

### Q5: How does your encryption work?
> **Answer**: "In `app/tools/encryption.py`, we leverage GnuPG (`gpg`) with AES-256 symmetric cipher (`--cipher-algo AES256`). When encrypting, GPG prompts the operator for a passphrase in the terminal, meaning passwords are never hardcoded or exposed in plaintext command logs."

### Q6: What is the Model Context Protocol (MCP)?
> **Answer**: "MCP is an open standard designed to connect AI applications to external tools using standardized JSON schemas. Our tool functions in `app/tools/` were engineered with explicit typed inputs and structured return dictionaries so they can be exposed as an MCP server with minimal refactoring."

---

## 📂 3. File Locations & Deliverables

### Final Review Reports (Word DOCX & PDF):
- **Review 1**:
  - `docs/Review_1_Smart_Archive_Agent.docx`
  - `docs/Review_1_Smart_Archive_Agent.pdf`
- **Review 2**:
  - `docs/Review_2_Smart_Archive_Agent.docx`
  - `docs/Review_2_Smart_Archive_Agent.pdf`
- **Review 3**:
  - `docs/Review_3_Smart_Archive_Agent.docx`
  - `docs/Review_3_Smart_Archive_Agent.pdf`
- Also saved in your Windows Downloads folder: `C:\Users\Admin\Downloads\`

### Diagrams:
- Architecture Diagram: `docs/architecture.png`
- Workflow Diagram: `docs/workflow.png`

### GitHub Repository:
- Remote URL: [https://github.com/redrighthand2007/OS-SMART-ARCHIVE-AGENT](https://github.com/redrighthand2007/OS-SMART-ARCHIVE-AGENT)

---

## 🛠️ 4. Quick Troubleshooting Tips

- **If you open a new terminal in VS Code and `python` is not recognized**:
  Run:
  ```bash
  source .venv/bin/activate
  ```
- **If `pytest` command is not found**:
  Run:
  ```bash
  python -m pytest -v
  ```
- **To test single commands without entering the loop**:
  ```bash
  python app/main.py "create an archive of ./app ./app.tar.xz"
  ```
