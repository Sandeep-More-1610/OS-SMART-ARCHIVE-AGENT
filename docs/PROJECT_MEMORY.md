# OS Project — Smart Archive Agent: Project Memory

## User-confirmed decisions (2026-10-15)
- Project: Agentic Shell — Smart Archive Agent.
- Start coding from scratch; there was no existing implementation.
- Use Python and Ubuntu.
- Build one standalone terminal agent, not the class-wide 35-agent system.
- Accept human input in the terminal.
- If a request belongs to archive/storage operations, route it to the relevant predefined operation; otherwise say it is outside this agent's scope.
- Required capabilities: archive creation, compression, extraction, inspection, encryption, decryption, decompression.
- No separate LLM-selection exercise is required at this stage.
- Review 1 and Review 2 templates define required chapters.
- Review 2 must include diagrams, flowcharts, explanations for each, structure, architecture, and workflow.
- Do not prioritize class-wide integration/interface contract at this stage.

## Template mapping
- Review 1: Chapter 1 Introduction; Chapter 2 Literature Review & Theoretical Background.
- Review 2: Chapter 3 System Architecture & Design; Chapter 4 Implementation Methodology.

## Important accuracy rule
Do not claim an LLM, MCP, LangChain, or any other framework is implemented unless it is actually in the source code. The initial source package currently uses a deterministic local intent router as a runnable baseline. A model-backed intent adapter is a planned enhancement, not implemented functionality.

## Current package contents
- `app/main.py`: entry point
- `app/agent.py`: terminal loop and operation dispatch
- `app/intent.py`: deterministic intent classification
- `app/tools/archive.py`: archive, list, inspect, extract, compression and decompression functions
- `app/tools/encryption.py`: GPG encryption/decryption functions
- `app/security/validation.py`: basic path validation
- `tests/test_intent.py`: initial intent tests
- `README.md`: setup and usage
- `docs/PROJECT_MEMORY.md`: persistent project decisions and status

## Known limitations requiring next iteration
- Natural-language parsing is keyword-based and does not yet call an LLM.
- Some intent/path extraction cases need testing and refinement.
- Full end-to-end Linux execution tests have not been run in this hosted environment.
- Security checks and archive extraction behavior require careful testing before use on important data.
- Report documents describe the current implementation honestly and identify planned LLM integration separately.
