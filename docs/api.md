# Smart Archive Agent API Reference

## Module: `app.agent`

### `SmartArchiveAgent`
Orchestrator class coordinating intent parsing, planning, validation, and execution.

- **`plan(intent: ArchiveIntent) -> List[PlanStep]`**: Generates step-by-step execution roadmap without applying filesystem changes.
- **`execute(query_or_intent: Union[str, ArchiveIntent], **overrides) -> AgentResult`**: Executes an archiving or crypto operation.
- **`audit_log: List[Dict[str, Any]]`**: History of all operations with execution status, timings, and checksums.

### `AgentResult`
Dataclass containing operation output:
- `success: bool`
- `action: str`
- `message: str`
- `output_files: List[str]`
- `metrics: Dict[str, Any]`
- `audit_id: Optional[str]`
- `plan: List[Dict[str, Any]]`
- `error: Optional[str]`

---

## Module: `app.intent`

### `ArchiveIntent`
Represents parsed intent:
- `action: ActionType` (ARCHIVE, EXTRACT, ENCRYPT, DECRYPT, LIST, VERIFY)
- `sources: List[str]`
- `destination: Optional[str]`
- `format: Optional[str]`
- `encrypt: bool`
- `decrypt: bool`
- `password: Optional[str]`
- `filters: Dict[str, Any]`
- `dry_run: bool`
- `confidence: float`

---

## Module: `app.security.validation`

- **`is_safe_path(base_dir: str | Path, target_path: str | Path) -> bool`**: Returns True if target is within base_dir.
- **`resolve_safe_path(base_dir: str | Path, target_path: str | Path) -> Path`**: Resolves path and raises `PathTraversalError` on traversal attempts.
- **`sanitize_filename(name: str) -> str`**: Cleans illegal filesystem characters.
- **`calculate_checksum(file_path: str | Path, algorithm: str = 'sha256') -> str`**: Calculates cryptographic digest.
- **`verify_checksum(file_path: str | Path, expected_hash: str, algorithm: str = 'sha256') -> bool`**: Constant-time verification.
- **`validate_archive_safety(archive_path: str | Path, ...)`**: Audits archives for Zip Slip and decompression bombs.

---

## Module: `app.tools.archive`

- **`create_archive(sources, dest_path, format=None, compression_level=6, filter_criteria=None) -> Path`**
- **`extract_archive(archive_path, dest_dir, safe=True, members=None) -> List[Path]`**
- **`list_archive(archive_path) -> List[Dict[str, Any]]`**
- **`inspect_archive(archive_path) -> Dict[str, Any]`**
- **`verify_archive(archive_path) -> bool`**

---

## Module: `app.tools.encryption`

- **`generate_key() -> str`**: Generates a 256-bit URL-safe base64 key.
- **`encrypt_bytes(data: bytes, key_or_password: str | bytes) -> bytes`**
- **`decrypt_bytes(payload: bytes, key_or_password: str | bytes) -> bytes`**
- **`encrypt_file(src_path, dest_path=None, password_or_key="") -> Path`**
- **`decrypt_file(src_path, dest_path=None, password_or_key="") -> Path`**
- **`is_encrypted_file(file_path) -> bool`**
