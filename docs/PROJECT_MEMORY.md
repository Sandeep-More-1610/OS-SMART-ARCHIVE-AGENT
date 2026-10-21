# OS Project — Smart Archive Agent: Project Memory

## Decisions
- Project: Agentic Shell, Agent #12 Smart Archive Agent. Python on Ubuntu/WSL 2.
- One standalone agent that the teacher integrates into the class-wide shell with 34 other agents. It must run on his lab or personal machine, not only ours.
- The base shell owns the LLM. This agent provides tool definitions for function calling (`get_tools`) and runs them (`execute_tool`). It also has a built-in rule-based planner (`handle_request`) so it works with no API key or network.
- Package renamed from `app` to `smart_archive_agent` (2026-10-21) to avoid clashing with other teams' packages.
- Python 3.8+ syntax, standard library only; Linux tools: tar, gzip, bzip2, xz, gpg, file (`--doctor` checks them).
- Review templates: Review 1 = Ch 1–2, Review 2 = Ch 3–4, Review 3 = Ch 5–7 (Testing & Results, Conclusion & Future Scope, Screenshots).

## Accuracy rule
Never claim an LLM, MCP server, LangChain or any feature that is not in the source code. The agent exposes LLM-ready tool schemas; it does not call an LLM itself. MCP is future work.

## Status (2026-10-22)
- Brief's example "Zip up my project folder, compress it heavily, and encrypt it." works end to end: tar.xz (xz -9e) → GPG AES-256 → plaintext copy deleted.
- 52 tests pass on Ubuntu 26.04.1 (WSL 2), Python 3.14.
- Benchmark (`benchmarks/evaluate.py`): held-out intent accuracy 16/20 = 80%; development 65/65; error recovery 18/18; planning < 0.2 ms.
- Not verified: running on Python 3.8–3.13 (only 3.14 was available); `docs/architecture.png` and `docs/workflow.png` still show the old `app/` module names.
