# Smart Archive Agent — API Reference

## Package `smart_archive_agent`

| Name | Description |
| :--- | :--- |
| `AGENT_NAME` | `"smart_archive_agent"` |
| `AGENT_DESCRIPTION` | One-line description for the shell's agent router |
| `get_tools(style="generic")` | Tool definitions. `"generic"`: `{name, description, parameters}`; `"openai"`: `{type: "function", function: {...}}`; `"anthropic"`: `{name, description, input_schema}` |
| `execute_tool(name, args, passphrase=None) -> dict` | Validates and runs one tool call. Never raises. |
| `handle_request(text, confirm=None, passphrase=None) -> dict` | Plans and runs a plain-English request. `confirm(plan) -> bool` is called before writing (None = approved). `passphrase` is a string or `function(tool_name) -> str`. |

## Tools

| Tool | Required arguments | Optional arguments |
| :--- | :--- | :--- |
| `create_archive` | `source_path`, `output_path` | `compression`: `auto`, `none`, `gz`, `bz2`, `xz`, `zip` (default `auto`, from the extension); `level`: `fast`, `normal`, `max` |
| `extract_archive` | `archive_path`, `destination_path` | — |
| `list_archive` | `archive_path` | — |
| `inspect_archive` | `archive_path` | — |
| `compress_file` | `source_path`, `output_path` | `algorithm`: `gz`, `bz2`, `xz`; `level` |
| `decompress_file` | `source_path`, `output_path` | — |
| `encrypt_file` | `source_path`, `output_path` | passphrase passed separately |
| `decrypt_file` | `source_path`, `output_path` | passphrase passed separately |

## Result dictionary

| Key | When |
| :--- | :--- |
| `success` | always |
| `operation` | always: the tool name, `plan`, `blocked`, `unrelated`, `cancelled`, ... |
| `message` | always, human readable |
| `output` | path of the file or folder produced |
| `original_bytes`, `archive_bytes` | archive and compression results |
| `entries`, `entries_count`, `entries_preview`, `type` | list / inspect results |
| `steps`, `plan` | multi-step requests: each step's result and the plan shown to the user |
| `missing` | a required detail could not be found in the request |
| `error`, `completed_steps` | failures; `completed_steps` says how far a plan got |

## Internal modules

* `intent.classify(text) -> Intent(operation, args, missing, message)`
* `planner.plan_local(text) -> Plan(status, steps, message, missing, operation)`, `validate_plan(plan) -> list[str]`, `describe(plan) -> list[str]`
* `security.guardrails.check_request(text) -> str | None`, `PROTECTED_DIRS`
* `security.validation.resolve_existing_path`, `resolve_output_path`, `reject_same_path`, `calculate_checksum`, `ValidationError`
