"""Smart Archive Agent core orchestrator.

Coordinates intent parsing, security validation, archiving operations,
and cryptographic protections with execution auditing and safety guards.
"""

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.intent import ActionType, ArchiveIntent, IntentParser
from app.security.validation import (
    calculate_checksum,
    resolve_safe_path,
    validate_archive_safety,
    SecurityError,
)
from app.tools.archive import (
    create_archive,
    extract_archive,
    inspect_archive,
    list_archive,
    verify_archive,
)
from app.tools.encryption import (
    decrypt_file,
    encrypt_file,
    is_encrypted_file,
    DecryptionError,
)


@dataclass
class PlanStep:
    """An individual step planned by the Smart Archive Agent."""
    step_number: int
    name: str
    description: str
    target: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Structured result returned by the agent upon execution."""
    success: bool
    action: str
    message: str
    output_files: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    audit_id: Optional[str] = None
    plan: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to serializable dict."""
        return {
            "success": self.success,
            "action": self.action,
            "message": self.message,
            "output_files": self.output_files,
            "metrics": self.metrics,
            "audit_id": self.audit_id,
            "plan": self.plan,
            "error": self.error,
        }


class SmartArchiveAgent:
    """Intelligent agent orchestrating safe archive and encryption operations."""

    def __init__(self, parser: Optional[IntentParser] = None):
        self.parser = parser or IntentParser()
        self.audit_log: List[Dict[str, Any]] = []

    def _record_audit(
        self,
        action: str,
        sources: List[str],
        outputs: List[str],
        status: str,
        duration_ms: float,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> str:
        """Append an entry to the audit log."""
        audit_id = f"audit-{int(time.time() * 1000)}"
        entry = {
            "audit_id": audit_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "sources": sources,
            "outputs": outputs,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "details": details or {},
            "error": error,
        }
        self.audit_log.append(entry)
        return audit_id

    def plan(self, intent: ArchiveIntent) -> List[PlanStep]:
        """Formulate an execution plan without executing actions."""
        steps: List[PlanStep] = []
        step_idx = 1

        if intent.action == ActionType.ARCHIVE:
            dest = intent.destination or "archive.zip"
            if intent.encrypt and not dest.endswith(".enc"):
                archive_file = dest
                enc_dest = f"{dest}.enc"
            else:
                archive_file = dest
                enc_dest = None

            steps.append(
                PlanStep(
                    step_number=step_idx,
                    name="ValidateSources",
                    description=f"Validate accessibility and security of sources: {intent.sources}",
                    target=", ".join(intent.sources),
                )
            )
            step_idx += 1

            steps.append(
                PlanStep(
                    step_number=step_idx,
                    name="CreateArchive",
                    description=f"Compress files into '{archive_file}' using {intent.format or 'auto-detected'} format",
                    target=archive_file,
                    details={"filters": intent.filters},
                )
            )
            step_idx += 1

            if intent.encrypt:
                steps.append(
                    PlanStep(
                        step_number=step_idx,
                        name="EncryptArchive",
                        description=f"Encrypt '{archive_file}' using AES-256-GCM authenticated cipher",
                        target=enc_dest or archive_file,
                    )
                )

        elif intent.action == ActionType.EXTRACT:
            src = intent.sources[0] if intent.sources else "archive.zip"
            dest = intent.destination or "./extracted"

            if intent.decrypt or src.endswith(".enc"):
                steps.append(
                    PlanStep(
                        step_number=step_idx,
                        name="DecryptArchive",
                        description=f"Decrypt encrypted archive '{src}'",
                        target=src,
                    )
                )
                step_idx += 1

            steps.append(
                PlanStep(
                    step_number=step_idx,
                    name="SecurityAudit",
                    description=f"Audit archive '{src}' for Zip-Slip traversal and decompression bombs",
                    target=src,
                )
            )
            step_idx += 1

            steps.append(
                PlanStep(
                    step_number=step_idx,
                    name="ExtractSafely",
                    description=f"Safely extract files into destination directory '{dest}'",
                    target=dest,
                )
            )

        elif intent.action == ActionType.ENCRYPT:
            src = intent.sources[0] if intent.sources else ""
            dest = intent.destination or f"{src}.enc"
            steps.append(
                PlanStep(
                    step_number=step_idx,
                    name="EncryptFile",
                    description=f"Encrypt '{src}' to '{dest}' using AES-256-GCM",
                    target=dest,
                )
            )

        elif intent.action == ActionType.DECRYPT:
            src = intent.sources[0] if intent.sources else ""
            dest = intent.destination or src.replace(".enc", "")
            steps.append(
                PlanStep(
                    step_number=step_idx,
                    name="DecryptFile",
                    description=f"Decrypt '{src}' to '{dest}'",
                    target=dest,
                )
            )

        elif intent.action == ActionType.LIST:
            src = intent.sources[0] if intent.sources else ""
            steps.append(
                PlanStep(
                    step_number=step_idx,
                    name="ListContents",
                    description=f"List and analyze entries of archive '{src}'",
                    target=src,
                )
            )

        elif intent.action == ActionType.VERIFY:
            src = intent.sources[0] if intent.sources else ""
            steps.append(
                PlanStep(
                    step_number=step_idx,
                    name="VerifyIntegrity",
                    description=f"Verify structural and cryptographic integrity of '{src}'",
                    target=src,
                )
            )

        return steps

    def execute(
        self,
        query_or_intent: Union[str, ArchiveIntent],
        **overrides: Any,
    ) -> AgentResult:
        """Parse, validate, plan, and execute an archiving instruction."""
        start_time = time.time()

        if isinstance(query_or_intent, str):
            intent = self.parser.parse(query_or_intent)
        else:
            intent = query_or_intent

        # Apply any runtime overrides
        for k, v in overrides.items():
            if hasattr(intent, k):
                setattr(intent, k, v)

        plan = self.plan(intent)
        plan_dicts = [
            {"step": s.step_number, "name": s.name, "description": s.description, "target": s.target}
            for s in plan
        ]

        if intent.dry_run:
            duration_ms = (time.time() - start_time) * 1000
            audit_id = self._record_audit(
                action=intent.action.value,
                sources=intent.sources,
                outputs=[intent.destination] if intent.destination else [],
                status="DRY_RUN",
                duration_ms=duration_ms,
                details={"plan": plan_dicts},
            )
            return AgentResult(
                success=True,
                action=intent.action.value,
                message=f"Dry run complete. Generated {len(plan)} execution steps.",
                output_files=[],
                metrics={"dry_run": True, "steps_count": len(plan)},
                audit_id=audit_id,
                plan=plan_dicts,
            )

        try:
            if intent.action == ActionType.ARCHIVE:
                result = self._execute_archive(intent, plan_dicts, start_time)
            elif intent.action == ActionType.EXTRACT:
                result = self._execute_extract(intent, plan_dicts, start_time)
            elif intent.action == ActionType.ENCRYPT:
                result = self._execute_encrypt(intent, plan_dicts, start_time)
            elif intent.action == ActionType.DECRYPT:
                result = self._execute_decrypt(intent, plan_dicts, start_time)
            elif intent.action == ActionType.LIST:
                result = self._execute_list(intent, plan_dicts, start_time)
            elif intent.action == ActionType.VERIFY:
                result = self._execute_verify(intent, plan_dicts, start_time)
            else:
                raise ValueError(f"Unsupported action: {intent.action}")

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            audit_id = self._record_audit(
                action=intent.action.value if hasattr(intent.action, "value") else str(intent.action),
                sources=intent.sources,
                outputs=[],
                status="FAILED",
                duration_ms=duration_ms,
                error=str(e),
            )
            return AgentResult(
                success=False,
                action=intent.action.value if hasattr(intent.action, "value") else str(intent.action),
                message=f"Execution failed: {str(e)}",
                audit_id=audit_id,
                plan=plan_dicts,
                error=str(e),
            )

    def _execute_archive(
        self, intent: ArchiveIntent, plan_dicts: List[Dict[str, Any]], start_time: float
    ) -> AgentResult:
        if not intent.sources:
            raise ValueError("No source files or directories provided for archiving.")

        dest = intent.destination or "archive.zip"
        needs_encryption = intent.encrypt

        # Intermediate archive if encryption requested
        if needs_encryption and not dest.endswith(".enc"):
            final_target = f"{dest}.enc"
            temp_archive = dest
        elif needs_encryption and dest.endswith(".enc"):
            final_target = dest
            temp_archive = dest[:-4]
        else:
            final_target = dest
            temp_archive = dest

        created_archive = create_archive(
            sources=intent.sources,
            dest_path=temp_archive,
            format=intent.format,
            filter_criteria=intent.filters,
        )

        output_files = [str(created_archive)]
        checksum = calculate_checksum(created_archive)

        if needs_encryption:
            if not intent.password:
                raise ValueError("Encryption requested but no password or key was provided.")
            encrypted_file = encrypt_file(
                src_path=created_archive,
                dest_path=final_target,
                password_or_key=intent.password,
            )
            if str(created_archive) != str(encrypted_file) and created_archive.exists():
                created_archive.unlink()  # Clean up plain intermediate archive
            output_files = [str(encrypted_file)]
            checksum = calculate_checksum(encrypted_file)

        duration_ms = (time.time() - start_time) * 1000
        audit_id = self._record_audit(
            action="archive",
            sources=intent.sources,
            outputs=output_files,
            status="SUCCESS",
            duration_ms=duration_ms,
            details={"checksum": checksum, "encrypted": needs_encryption},
        )

        return AgentResult(
            success=True,
            action="archive",
            message=f"Successfully created archive: {output_files[0]}",
            output_files=output_files,
            metrics={"checksum": checksum, "encrypted": needs_encryption},
            audit_id=audit_id,
            plan=plan_dicts,
        )

    def _execute_extract(
        self, intent: ArchiveIntent, plan_dicts: List[Dict[str, Any]], start_time: float
    ) -> AgentResult:
        if not intent.sources:
            raise ValueError("No archive file specified for extraction.")

        archive_src = Path(intent.sources[0]).resolve()
        dest_dir = Path(intent.destination or "./extracted").resolve()

        cleanup_temp = False
        working_archive = archive_src

        # Decrypt first if encrypted
        if is_encrypted_file(archive_src) or intent.decrypt:
            if not intent.password:
                raise ValueError("Encrypted archive requires a password or decryption key.")
            decrypted_temp = archive_src.parent / f"_temp_dec_{archive_src.stem}"
            working_archive = decrypt_file(archive_src, decrypted_temp, intent.password)
            cleanup_temp = True

        try:
            # Audit safety
            safety_info = validate_archive_safety(working_archive)
            extracted = extract_archive(working_archive, dest_dir, safe=True)
        finally:
            if cleanup_temp and working_archive.exists():
                working_archive.unlink()

        output_paths = [str(p) for p in extracted]
        duration_ms = (time.time() - start_time) * 1000
        audit_id = self._record_audit(
            action="extract",
            sources=[str(archive_src)],
            outputs=output_paths,
            status="SUCCESS",
            duration_ms=duration_ms,
            details={"extracted_count": len(output_paths), "safety_metrics": safety_info},
        )

        return AgentResult(
            success=True,
            action="extract",
            message=f"Successfully extracted {len(output_paths)} files into {dest_dir}",
            output_files=output_paths,
            metrics={"file_count": len(output_paths), "destination": str(dest_dir)},
            audit_id=audit_id,
            plan=plan_dicts,
        )

    def _execute_encrypt(
        self, intent: ArchiveIntent, plan_dicts: List[Dict[str, Any]], start_time: float
    ) -> AgentResult:
        if not intent.sources:
            raise ValueError("No file provided to encrypt.")
        if not intent.password:
            raise ValueError("Encryption requires a password or key.")

        src = Path(intent.sources[0]).resolve()
        dest = Path(intent.destination).resolve() if intent.destination else None
        enc_path = encrypt_file(src, dest, intent.password)

        checksum = calculate_checksum(enc_path)
        duration_ms = (time.time() - start_time) * 1000
        audit_id = self._record_audit(
            action="encrypt",
            sources=[str(src)],
            outputs=[str(enc_path)],
            status="SUCCESS",
            duration_ms=duration_ms,
            details={"checksum": checksum},
        )

        return AgentResult(
            success=True,
            action="encrypt",
            message=f"Successfully encrypted file to {enc_path}",
            output_files=[str(enc_path)],
            metrics={"checksum": checksum},
            audit_id=audit_id,
            plan=plan_dicts,
        )

    def _execute_decrypt(
        self, intent: ArchiveIntent, plan_dicts: List[Dict[str, Any]], start_time: float
    ) -> AgentResult:
        if not intent.sources:
            raise ValueError("No file provided to decrypt.")
        if not intent.password:
            raise ValueError("Decryption requires a password or key.")

        src = Path(intent.sources[0]).resolve()
        dest = Path(intent.destination).resolve() if intent.destination else None
        dec_path = decrypt_file(src, dest, intent.password)

        checksum = calculate_checksum(dec_path)
        duration_ms = (time.time() - start_time) * 1000
        audit_id = self._record_audit(
            action="decrypt",
            sources=[str(src)],
            outputs=[str(dec_path)],
            status="SUCCESS",
            duration_ms=duration_ms,
            details={"checksum": checksum},
        )

        return AgentResult(
            success=True,
            action="decrypt",
            message=f"Successfully decrypted file to {dec_path}",
            output_files=[str(dec_path)],
            metrics={"checksum": checksum},
            audit_id=audit_id,
            plan=plan_dicts,
        )

    def _execute_list(
        self, intent: ArchiveIntent, plan_dicts: List[Dict[str, Any]], start_time: float
    ) -> AgentResult:
        if not intent.sources:
            raise ValueError("No archive file provided to list.")

        src = Path(intent.sources[0]).resolve()
        contents = list_archive(src)

        duration_ms = (time.time() - start_time) * 1000
        audit_id = self._record_audit(
            action="list",
            sources=[str(src)],
            outputs=[],
            status="SUCCESS",
            duration_ms=duration_ms,
            details={"entry_count": len(contents)},
        )

        return AgentResult(
            success=True,
            action="list",
            message=f"Archive contains {len(contents)} items.",
            output_files=[],
            metrics={"entries": contents, "count": len(contents)},
            audit_id=audit_id,
            plan=plan_dicts,
        )

    def _execute_verify(
        self, intent: ArchiveIntent, plan_dicts: List[Dict[str, Any]], start_time: float
    ) -> AgentResult:
        if not intent.sources:
            raise ValueError("No archive provided for verification.")

        src = Path(intent.sources[0]).resolve()
        valid = verify_archive(src)
        checksum = calculate_checksum(src)

        duration_ms = (time.time() - start_time) * 1000
        audit_id = self._record_audit(
            action="verify",
            sources=[str(src)],
            outputs=[],
            status="SUCCESS" if valid else "CORRUPTED",
            duration_ms=duration_ms,
            details={"integrity_valid": valid, "sha256": checksum},
        )

        return AgentResult(
            success=valid,
            action="verify",
            message=f"Integrity check {'passed' if valid else 'failed'} for {src.name}",
            output_files=[],
            metrics={"integrity_valid": valid, "sha256": checksum},
            audit_id=audit_id,
            plan=plan_dicts,
        )
