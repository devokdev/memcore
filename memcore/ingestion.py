"""Memory ingestion engine: handles sanitization, secret redaction, token counting, and storage."""

import logging
import time
from typing import Any, Dict, List, Optional

from memcore.models import (
    MemoryAuditLog,
    MemoryRecord,
    MemoryStatus,
    MemoryType,
    VerificationStatus,
)
from memcore.security import redact_secrets, sanitize_untrusted_input
from memcore.storage import BaseMemoryStore
from memcore.tokenizer import count_tokens

logger = logging.getLogger(__name__)


class MemoryIngestionEngine:
    """Ingests memories from conversations, coding sessions, repo analysis, and tool outputs."""

    def __init__(self, store: BaseMemoryStore):
        self.store = store

    def ingest(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.GENERAL,
        project_id: str = "default",
        source: str = "agent",
        provenance: Optional[Dict[str, Any]] = None,
        confidence: float = 0.8,
        importance: float = 0.5,
        associated_files: Optional[List[str]] = None,
        associated_symbols: Optional[List[str]] = None,
        associated_components: Optional[List[str]] = None,
        is_protected: bool = False,
        protection_reason: Optional[str] = None,
        parent_memory_ids: Optional[List[str]] = None,
    ) -> MemoryRecord:
        """Ingests, cleans, counts tokens, redacts secrets, and saves memory."""
        # 1. Sanitize untrusted text input
        cleaned_content = sanitize_untrusted_input(content)

        # 2. Secret Redaction
        redacted_content, was_redacted = redact_secrets(cleaned_content)
        prov = provenance.copy() if provenance else {}
        if was_redacted:
            prov["secrets_redacted"] = True

        # 3. Token counting
        token_count, is_estimated = count_tokens(redacted_content)

        record = MemoryRecord(
            project_id=project_id,
            content=redacted_content,
            memory_type=memory_type,
            source=source,
            provenance=prov,
            confidence=max(0.0, min(1.0, confidence)),
            importance=max(0.0, min(1.0, importance)),
            token_count=token_count,
            estimated_token=is_estimated,
            associated_files=associated_files or [],
            associated_symbols=associated_symbols or [],
            associated_components=associated_components or [],
            status=MemoryStatus.ACTIVE,
            version=1,
            is_protected=is_protected,
            protection_reason=protection_reason,
            parent_memory_ids=parent_memory_ids or [],
        )

        self.store.save_memory(record)

        # Audit entry
        self.store.record_audit(
            MemoryAuditLog(
                memory_id=record.id,
                action="ingest",
                actor=source,
                new_state=record.model_dump(),
                reason="Initial memory ingestion",
            )
        )

        return record

    def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        confidence: Optional[float] = None,
        importance: Optional[float] = None,
        associated_files: Optional[List[str]] = None,
        associated_symbols: Optional[List[str]] = None,
        verification_status: Optional[VerificationStatus] = None,
        verification_notes: Optional[str] = None,
        reason: Optional[str] = None,
        actor: str = "agent",
    ) -> Optional[MemoryRecord]:
        record = self.store.get_memory(memory_id)
        if not record:
            return None

        prev_state = record.model_dump()

        if content is not None:
            cleaned = sanitize_untrusted_input(content)
            redacted, was_redacted = redact_secrets(cleaned)
            record.content = redacted
            token_count, is_estimated = count_tokens(redacted)
            record.token_count = token_count
            record.estimated_token = is_estimated
            if was_redacted:
                record.provenance["secrets_redacted"] = True

        if confidence is not None:
            record.confidence = max(0.0, min(1.0, confidence))
        if importance is not None:
            record.importance = max(0.0, min(1.0, importance))
        if associated_files is not None:
            record.associated_files = associated_files
        if associated_symbols is not None:
            record.associated_symbols = associated_symbols
        if verification_status is not None:
            record.verification_status = verification_status
            record.last_verified_at = time.time()
        if verification_notes is not None:
            record.verification_notes = verification_notes

        record.version += 1
        record.updated_at = time.time()

        self.store.update_memory(record)

        self.store.record_audit(
            MemoryAuditLog(
                memory_id=record.id,
                action="update",
                actor=actor,
                previous_state=prev_state,
                new_state=record.model_dump(),
                reason=reason or "Memory update",
            )
        )

        return record
