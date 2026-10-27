"""Abstract base class and implementations for persistent storage."""

from abc import ABC, abstractmethod
import json
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from memcore.models import (
    MemoryAuditLog,
    MemoryRecord,
    MemoryRelationship,
    MemoryStatus,
    MemoryType,
    RelationshipType,
    VerificationStatus,
)


class BaseMemoryStore(ABC):
    @abstractmethod
    def save_memory(self, memory: MemoryRecord) -> None:
        pass

    @abstractmethod
    def get_memory(self, memory_id: str) -> Optional[MemoryRecord]:
        pass

    @abstractmethod
    def update_memory(self, memory: MemoryRecord) -> None:
        pass

    @abstractmethod
    def delete_memory(self, memory_id: str, hard_delete: bool = False) -> bool:
        pass

    @abstractmethod
    def list_memories(
        self,
        project_id: str = "default",
        status: Optional[MemoryStatus] = MemoryStatus.ACTIVE,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MemoryRecord]:
        pass

    @abstractmethod
    def search_keyword(
        self,
        query: str,
        project_id: str = "default",
        status: Optional[MemoryStatus] = MemoryStatus.ACTIVE,
        limit: int = 20,
    ) -> List[MemoryRecord]:
        pass

    @abstractmethod
    def add_relationship(self, rel: MemoryRelationship) -> None:
        pass

    @abstractmethod
    def get_relationships(
        self, memory_id: str, rel_type: Optional[RelationshipType] = None
    ) -> List[MemoryRelationship]:
        pass

    @abstractmethod
    def record_audit(self, audit: MemoryAuditLog) -> None:
        pass

    @abstractmethod
    def get_audit_logs(self, memory_id: Optional[str] = None, limit: int = 50) -> List[MemoryAuditLog]:
        pass


class SQLiteMemoryStore(BaseMemoryStore):
    """Production-grade SQLite persistence store for MemCore."""

    def __init__(self, db_path: str = "memcore.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Memories table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                source TEXT NOT NULL,
                provenance TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                last_verified_at REAL,
                confidence REAL NOT NULL,
                importance REAL NOT NULL,
                usage_count INTEGER NOT NULL,
                last_accessed_at REAL,
                token_count INTEGER NOT NULL,
                estimated_token INTEGER NOT NULL,
                associated_files TEXT NOT NULL,
                associated_symbols TEXT NOT NULL,
                associated_components TEXT NOT NULL,
                status TEXT NOT NULL,
                version INTEGER NOT NULL,
                is_protected INTEGER NOT NULL,
                protection_reason TEXT,
                verification_status TEXT NOT NULL,
                verification_notes TEXT,
                superseded_by TEXT,
                parent_memory_ids TEXT NOT NULL
            );
            """)

            # Indexing for fast search and filtering
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mem_proj_status ON memories(project_id, status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mem_type ON memories(memory_type);")

            # Relationships table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                rel_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at REAL NOT NULL,
                metadata TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES memories(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES memories(id) ON DELETE CASCADE
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id);")

            # Audit logs table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp REAL NOT NULL,
                actor TEXT NOT NULL,
                previous_state TEXT,
                new_state TEXT,
                reason TEXT
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_mem ON audit_logs(memory_id);")
            
            # Full Text Search (FTS5) table for content and tags
            cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                id UNINDEXED,
                content,
                associated_files,
                associated_symbols,
                associated_components
            );
            """)

            conn.commit()

    def _row_to_memory(self, row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            project_id=row["project_id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            source=row["source"],
            provenance=json.loads(row["provenance"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_verified_at=row["last_verified_at"],
            confidence=row["confidence"],
            importance=row["importance"],
            usage_count=row["usage_count"],
            last_accessed_at=row["last_accessed_at"],
            token_count=row["token_count"],
            estimated_token=bool(row["estimated_token"]),
            associated_files=json.loads(row["associated_files"]),
            associated_symbols=json.loads(row["associated_symbols"]),
            associated_components=json.loads(row["associated_components"]),
            status=MemoryStatus(row["status"]),
            version=row["version"],
            is_protected=bool(row["is_protected"]),
            protection_reason=row["protection_reason"],
            verification_status=VerificationStatus(row["verification_status"]),
            verification_notes=row["verification_notes"],
            superseded_by=row["superseded_by"],
            parent_memory_ids=json.loads(row["parent_memory_ids"]),
        )

    def save_memory(self, memory: MemoryRecord) -> None:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO memories (
                id, project_id, content, memory_type, source, provenance,
                created_at, updated_at, last_verified_at, confidence, importance,
                usage_count, last_accessed_at, token_count, estimated_token,
                associated_files, associated_symbols, associated_components,
                status, version, is_protected, protection_reason,
                verification_status, verification_notes, superseded_by, parent_memory_ids
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.id,
                memory.project_id,
                memory.content,
                memory.memory_type.value,
                memory.source,
                json.dumps(memory.provenance),
                memory.created_at,
                memory.updated_at,
                memory.last_verified_at,
                memory.confidence,
                memory.importance,
                memory.usage_count,
                memory.last_accessed_at,
                memory.token_count,
                1 if memory.estimated_token else 0,
                json.dumps(memory.associated_files),
                json.dumps(memory.associated_symbols),
                json.dumps(memory.associated_components),
                memory.status.value,
                memory.version,
                1 if memory.is_protected else 0,
                memory.protection_reason,
                memory.verification_status.value,
                memory.verification_notes,
                memory.superseded_by,
                json.dumps(memory.parent_memory_ids),
            ))

            # Sync FTS
            cursor.execute("DELETE FROM memories_fts WHERE id = ?", (memory.id,))
            cursor.execute("""
            INSERT INTO memories_fts (id, content, associated_files, associated_symbols, associated_components)
            VALUES (?, ?, ?, ?, ?)
            """, (
                memory.id,
                memory.content,
                " ".join(memory.associated_files),
                " ".join(memory.associated_symbols),
                " ".join(memory.associated_components),
            ))

            conn.commit()

    def get_memory(self, memory_id: str) -> Optional[MemoryRecord]:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_memory(row)

    def update_memory(self, memory: MemoryRecord) -> None:
        self.save_memory(memory)

    def delete_memory(self, memory_id: str, hard_delete: bool = False) -> bool:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            if hard_delete:
                cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                cursor.execute("DELETE FROM memories_fts WHERE id = ?", (memory_id,))
                cursor.execute("DELETE FROM relationships WHERE source_id = ? OR target_id = ?", (memory_id, memory_id))
            else:
                cursor.execute("UPDATE memories SET status = ? WHERE id = ?", (MemoryStatus.SOFT_DELETED.value, memory_id))
            conn.commit()
            return cursor.rowcount > 0

    def list_memories(
        self,
        project_id: str = "default",
        status: Optional[MemoryStatus] = MemoryStatus.ACTIVE,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MemoryRecord]:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM memories WHERE project_id = ?"
            params: List[Any] = [project_id]

            if status is not None:
                query += " AND status = ?"
                params.append(status.value)

            if memory_type is not None:
                query += " AND memory_type = ?"
                params.append(memory_type.value)

            query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            return [self._row_to_memory(row) for row in cursor.fetchall()]

    def search_keyword(
        self,
        query: str,
        project_id: str = "default",
        status: Optional[MemoryStatus] = MemoryStatus.ACTIVE,
        limit: int = 20,
    ) -> List[MemoryRecord]:
        """Perform full-text search with fallback to LIKE query if FTS returns empty."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Clean query for FTS5
            sanitized_terms = [t.strip('"\'') for t in query.split() if t.strip('"\'')]
            results: List[MemoryRecord] = []
            
            if sanitized_terms:
                fts_query = " OR ".join(f'"{t}"*' for t in sanitized_terms)
                try:
                    cursor.execute("""
                    SELECT m.* FROM memories m
                    JOIN memories_fts fts ON m.id = fts.id
                    WHERE memories_fts MATCH ? AND m.project_id = ?
                    """ + (" AND m.status = ?" if status else "") + " LIMIT ?",
                    [fts_query, project_id] + ([status.value] if status else []) + [limit])
                    results = [self._row_to_memory(r) for r in cursor.fetchall()]
                except Exception:
                    results = []

            if not results:
                # Fallback to standard LIKE
                like_pat = f"%{query.strip()}%"
                cursor.execute("""
                SELECT * FROM memories WHERE project_id = ?
                """ + (" AND status = ?" if status else "") + """
                AND (content LIKE ? OR associated_files LIKE ? OR associated_symbols LIKE ?)
                ORDER BY updated_at DESC LIMIT ?
                """, [project_id] + ([status.value] if status else []) + [like_pat, like_pat, like_pat, limit])
                results = [self._row_to_memory(r) for r in cursor.fetchall()]

            return results

    def add_relationship(self, rel: MemoryRelationship) -> None:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO relationships (id, source_id, target_id, rel_type, confidence, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                rel.id,
                rel.source_id,
                rel.target_id,
                rel.rel_type.value,
                rel.confidence,
                rel.created_at,
                json.dumps(rel.metadata),
            ))
            conn.commit()

    def get_relationships(
        self, memory_id: str, rel_type: Optional[RelationshipType] = None
    ) -> List[MemoryRelationship]:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM relationships WHERE (source_id = ? OR target_id = ?)"
            params: List[Any] = [memory_id, memory_id]
            if rel_type is not None:
                query += " AND rel_type = ?"
                params.append(rel_type.value)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                MemoryRelationship(
                    id=r["id"],
                    source_id=r["source_id"],
                    target_id=r["target_id"],
                    rel_type=RelationshipType(r["rel_type"]),
                    confidence=r["confidence"],
                    created_at=r["created_at"],
                    metadata=json.loads(r["metadata"]),
                )
                for r in rows
            ]

    def record_audit(self, audit: MemoryAuditLog) -> None:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO audit_logs (id, memory_id, action, timestamp, actor, previous_state, new_state, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                audit.id,
                audit.memory_id,
                audit.action,
                audit.timestamp,
                audit.actor,
                json.dumps(audit.previous_state) if audit.previous_state else None,
                json.dumps(audit.new_state) if audit.new_state else None,
                audit.reason,
            ))
            conn.commit()

    def get_audit_logs(self, memory_id: Optional[str] = None, limit: int = 50) -> List[MemoryAuditLog]:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            if memory_id:
                cursor.execute(
                    "SELECT * FROM audit_logs WHERE memory_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (memory_id, limit),
                )
            else:
                cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [
                MemoryAuditLog(
                    id=r["id"],
                    memory_id=r["memory_id"],
                    action=r["action"],
                    timestamp=r["timestamp"],
                    actor=r["actor"],
                    previous_state=json.loads(r["previous_state"]) if r["previous_state"] else None,
                    new_state=json.loads(r["new_state"]) if r["new_state"] else None,
                    reason=r["reason"],
                )
                for r in rows
            ]
