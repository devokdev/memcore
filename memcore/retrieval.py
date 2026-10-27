"""Hybrid memory retrieval system combining keyword, semantic similarity, recency, and dependencies."""

import math
import time
from typing import Dict, List, Optional

from memcore.embeddings import BaseEmbeddingProvider, LocalFastEmbedder, cosine_similarity
from memcore.graph import MemoryGraph
from memcore.models import (
    MemoryRecord,
    MemoryStatus,
    RetrievedMemory,
    VerificationStatus,
)
from memcore.storage import BaseMemoryStore


class MemoryRetriever:
    """Intelligent memory retrieval with hybrid ranking, explanation, and dependency awareness."""

    def __init__(
        self,
        store: BaseMemoryStore,
        graph: Optional[MemoryGraph] = None,
        embedder: Optional[BaseEmbeddingProvider] = None,
    ):
        self.store = store
        self.graph = graph or MemoryGraph(store)
        self.embedder = embedder or LocalFastEmbedder()

    def retrieve(
        self,
        task_query: str,
        project_id: str = "default",
        top_k: int = 10,
        status: Optional[MemoryStatus] = MemoryStatus.ACTIVE,
        include_superseded: bool = False,
    ) -> List[RetrievedMemory]:
        """Hybrid search combining keyword FTS match, semantic vector similarity, importance, and recency."""
        now = time.time()
        
        # 1. Fetch candidate pool (active or requested status)
        candidates = self.store.list_memories(
            project_id=project_id,
            status=status if not include_superseded else None,
            limit=150,
        )

        if not candidates:
            return []

        # 2. Compute query embedding
        query_vec = self.embedder.embed_text(task_query)
        task_lower = task_query.lower()
        query_words = set(w for w in task_lower.split() if len(w) > 2)

        scored_results: List[RetrievedMemory] = []

        for mem in candidates:
            if not include_superseded and mem.status == MemoryStatus.SUPERSEDED:
                continue

            reasons: List[str] = []
            
            # Semantic similarity
            mem_vec = self.embedder.embed_text(mem.content)
            sem_sim = cosine_similarity(query_vec, mem_vec)
            if sem_sim > 0.35:
                reasons.append(f"Semantic similarity match ({sem_sim:.2f})")

            # Keyword lexical match
            mem_lower = mem.content.lower()
            matched_words = [w for w in query_words if w in mem_lower]
            keyword_score = len(matched_words) / (len(query_words) or 1)
            if matched_words:
                reasons.append(f"Keyword match for: {', '.join(list(matched_words)[:3])}")

            # Associated files / symbols match
            file_sym_match = False
            for f in mem.associated_files:
                if f.lower() in task_lower:
                    file_sym_match = True
                    reasons.append(f"Referenced file matched: {f}")
                    break
            for s in mem.associated_symbols:
                if s.lower() in task_lower:
                    file_sym_match = True
                    reasons.append(f"Referenced symbol matched: {s}")
                    break

            # Recency factor: half-life of 30 days (2592000s)
            age_seconds = max(0.0, now - mem.updated_at)
            recency_factor = math.exp(-age_seconds / 2592000.0)

            # Verification modifier
            verification_mod = 1.0
            if mem.verification_status == VerificationStatus.VERIFIED:
                verification_mod = 1.25
                reasons.append("Grounding verified in repository")
            elif mem.verification_status == VerificationStatus.STALE:
                verification_mod = 0.7
                reasons.append("Warning: marked stale")
            elif mem.verification_status == VerificationStatus.CONFLICT:
                verification_mod = 0.5
                reasons.append("Warning: repository conflict detected")

            # Base relevance composite score
            # 0.45 * semantic + 0.30 * keyword + 0.15 * importance + 0.10 * recency + (0.2 if file_sym_match)
            composite_score = (
                (0.45 * sem_sim)
                + (0.30 * keyword_score)
                + (0.15 * mem.importance)
                + (0.10 * recency_factor)
                + (0.20 if file_sym_match else 0.0)
            ) * verification_mod * mem.confidence

            # Protection boost for critical constraints
            if mem.is_protected:
                composite_score *= 1.15
                reasons.append(f"Protected memory ({mem.protection_reason or 'core'})")

            # Fetch immediate relationships for context
            rels = self.graph.get_neighbors(mem.id)

            scored_results.append(
                RetrievedMemory(
                    memory=mem,
                    relevance_score=composite_score,
                    retrieval_reasons=reasons,
                    relationships=rels,
                )
            )

        # Sort descending by composite score
        scored_results.sort(key=lambda x: x.relevance_score, reverse=True)

        # Update access count & timestamp for retrieved items
        top_results = scored_results[:top_k]
        for item in top_results:
            item.memory.usage_count += 1
            item.memory.last_accessed_at = now
            self.store.update_memory(item.memory)

        return top_results
