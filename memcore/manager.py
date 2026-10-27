"""Unified MemCore Manager providing a clean programmatic interface."""

import os
from typing import Any, Dict, List, Optional

from memcore.compression import MemoryCompressor
from memcore.counterfactual import CounterfactualTester
from memcore.gc import MemoryGCEngine
from memcore.graph import MemoryGraph
from memcore.ingestion import MemoryIngestionEngine
from memcore.models import (
    ContextBuildResult,
    GCRecommendation,
    MemoryAuditLog,
    MemoryRecord,
    MemoryRelationship,
    MemoryStatus,
    MemoryType,
    RelationshipType,
    RetrievedMemory,
    VerificationResult,
    VerificationStatus,
)
from memcore.optimizer import TokenBudgetOptimizer
from memcore.retrieval import MemoryRetriever
from memcore.scoring import MemoryScorer
from memcore.storage import BaseMemoryStore, SQLiteMemoryStore
from memcore.verification import RepositoryVerifier


class MemCore:
    """Primary facade for MemCore memory management."""

    def __init__(self, db_path: str = "memcore.db", repo_root: Optional[str] = None):
        self.repo_root = os.path.abspath(repo_root or os.getcwd())
        self.store = SQLiteMemoryStore(db_path=db_path)
        self.graph = MemoryGraph(self.store)
        self.ingestion = MemoryIngestionEngine(self.store)
        self.retriever = MemoryRetriever(self.store, self.graph)
        self.scorer = MemoryScorer(self.store, self.graph)
        self.compressor = MemoryCompressor()
        self.verifier = RepositoryVerifier(self.repo_root, self.store)
        self.gc_engine = MemoryGCEngine(self.store, self.scorer, self.compressor, self.graph)
        self.optimizer = TokenBudgetOptimizer(self.store, self.retriever, self.scorer, self.graph)
        self.tester = CounterfactualTester(self.store, self.optimizer)

    # Ingestion & Mutation
    def add_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.GENERAL,
        project_id: str = "default",
        source: str = "user",
        confidence: float = 0.8,
        importance: float = 0.5,
        associated_files: Optional[List[str]] = None,
        associated_symbols: Optional[List[str]] = None,
        associated_components: Optional[List[str]] = None,
        is_protected: bool = False,
        protection_reason: Optional[str] = None,
    ) -> MemoryRecord:
        return self.ingestion.ingest(
            content=content,
            memory_type=memory_type,
            project_id=project_id,
            source=source,
            confidence=confidence,
            importance=importance,
            associated_files=associated_files,
            associated_symbols=associated_symbols,
            associated_components=associated_components,
            is_protected=is_protected,
            protection_reason=protection_reason,
        )

    def get_memory(self, memory_id: str) -> Optional[MemoryRecord]:
        return self.store.get_memory(memory_id)

    def update_memory(self, memory_id: str, **kwargs) -> Optional[MemoryRecord]:
        return self.ingestion.update(memory_id, **kwargs)

    def delete_memory(self, memory_id: str, hard_delete: bool = False) -> bool:
        mem = self.store.get_memory(memory_id)
        if not mem:
            return False
        if mem.is_protected:
            raise PermissionError(f"Cannot delete protected memory {memory_id}: {mem.protection_reason}")
        return self.store.delete_memory(memory_id, hard_delete=hard_delete)

    def restore_memory(self, memory_id: str) -> Optional[MemoryRecord]:
        mem = self.store.get_memory(memory_id)
        if not mem:
            return None
        mem.status = MemoryStatus.ACTIVE
        self.store.update_memory(mem)
        self.store.record_audit(
            MemoryAuditLog(
                memory_id=mem.id,
                action="restore",
                actor="user",
                reason="Restored soft deleted or archived memory",
            )
        )
        return mem

    def protect_memory(self, memory_id: str, reason: str = "Protected by user") -> Optional[MemoryRecord]:
        mem = self.store.get_memory(memory_id)
        if not mem:
            return None
        mem.is_protected = True
        mem.protection_reason = reason
        self.store.update_memory(mem)
        self.store.record_audit(
            MemoryAuditLog(
                memory_id=mem.id,
                action="protect",
                actor="user",
                reason=reason,
            )
        )
        return mem

    # Search & Retrieval
    def search_memories(
        self,
        query: str,
        project_id: str = "default",
        top_k: int = 10,
        include_superseded: bool = False,
    ) -> List[RetrievedMemory]:
        return self.retriever.retrieve(
            task_query=query,
            project_id=project_id,
            top_k=top_k,
            include_superseded=include_superseded,
        )

    def build_context(
        self,
        task_query: str,
        token_budget: int = 2000,
        project_id: str = "default",
    ) -> ContextBuildResult:
        return self.optimizer.build_context(
            task_query=task_query,
            token_budget=token_budget,
            project_id=project_id,
        )

    # Graph Relationships
    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationshipType,
        confidence: float = 1.0,
    ) -> MemoryRelationship:
        return self.graph.link(source_id, target_id, rel_type, confidence)

    def get_related(self, memory_id: str) -> List[MemoryRelationship]:
        return self.graph.get_neighbors(memory_id)

    # Verification
    def verify_memory(self, memory_id: str) -> Optional[VerificationResult]:
        mem = self.store.get_memory(memory_id)
        if not mem:
            return None
        return self.verifier.verify_memory(mem)

    def verify_all(self, project_id: str = "default") -> List[VerificationResult]:
        return self.verifier.verify_all_active(project_id=project_id)

    # Garbage Collection
    def preview_gc(self, project_id: str = "default") -> List[GCRecommendation]:
        return self.gc_engine.preview_gc(project_id)

    def execute_gc(
        self,
        project_id: str = "default",
        allow_delete: bool = False,
        approved_memory_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return self.gc_engine.execute_gc(
            project_id=project_id,
            allow_delete=allow_delete,
            approved_memory_ids=approved_memory_ids,
        )

    # Audit History & Stats
    def get_history(self, memory_id: Optional[str] = None, limit: int = 50) -> List[MemoryAuditLog]:
        return self.store.get_audit_logs(memory_id, limit=limit)

    def get_stats(self, project_id: str = "default") -> Dict[str, Any]:
        all_memories = self.store.list_memories(project_id=project_id, status=None, limit=2000)
        
        status_counts = {}
        type_counts = {}
        total_tokens = 0
        protected_count = 0
        conflicts = 0

        for m in all_memories:
            status_counts[m.status.value] = status_counts.get(m.status.value, 0) + 1
            type_counts[m.memory_type.value] = type_counts.get(m.memory_type.value, 0) + 1
            if m.status == MemoryStatus.ACTIVE:
                total_tokens += m.token_count
            if m.is_protected:
                protected_count += 1
            if m.verification_status == VerificationStatus.CONFLICT:
                conflicts += 1

        return {
            "total_memories": len(all_memories),
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "active_tokens": total_tokens,
            "protected_count": protected_count,
            "conflicts_count": conflicts,
        }
