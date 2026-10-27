"""Token-budget context optimizer: selects maximal utility memory set under strict token constraints."""

from typing import Any, Dict, List, Optional

from memcore.graph import MemoryGraph
from memcore.models import ContextBuildResult, MemoryRecord, RetrievedMemory, VerificationStatus
from memcore.retrieval import MemoryRetriever
from memcore.scoring import MemoryScorer
from memcore.storage import BaseMemoryStore


class TokenBudgetOptimizer:
    """Builds optimal, grounded prompt context respecting strict token limits and dependencies."""

    def __init__(
        self,
        store: BaseMemoryStore,
        retriever: Optional[MemoryRetriever] = None,
        scorer: Optional[MemoryScorer] = None,
        graph: Optional[MemoryGraph] = None,
    ):
        self.store = store
        self.graph = graph or MemoryGraph(store)
        self.retriever = retriever or MemoryRetriever(store, self.graph)
        self.scorer = scorer or MemoryScorer(store, self.graph)

    def build_context(
        self,
        task_query: str,
        token_budget: int = 2000,
        project_id: str = "default",
        reserve_headroom_tokens: int = 150,
        must_include_protected: bool = True,
    ) -> ContextBuildResult:
        """Selects the highest utility, risk-aware context within token budget."""
        effective_budget = max(50, token_budget - reserve_headroom_tokens)
        
        # 1. Retrieve candidates
        candidates: List[RetrievedMemory] = self.retriever.retrieve(
            task_query=task_query,
            project_id=project_id,
            top_k=30,
        )

        selected: List[RetrievedMemory] = []
        excluded: List[Dict[str, Any]] = []
        used_tokens = 0
        preserved_dependencies: List[str] = []
        conflicts_detected: List[str] = []

        # Sort candidates: prioritize protected constraints and high relevance
        candidates.sort(
            key=lambda x: (
                1 if (must_include_protected and x.memory.is_protected) else 0,
                x.relevance_score,
            ),
            reverse=True,
        )

        selected_ids = set()

        for item in candidates:
            mem = item.memory
            cost = mem.token_count or 1

            if mem.verification_status == VerificationStatus.CONFLICT:
                conflicts_detected.append(f"Memory {mem.id[:8]} has conflict: {mem.verification_notes}")

            # Check if budget allows
            if used_tokens + cost <= effective_budget:
                selected.append(item)
                selected_ids.add(mem.id)
                used_tokens += cost

                # Check if this memory has critical dependencies that should also be brought in
                dep_ids = self.graph.get_outgoing_dependencies(mem.id)
                for dep_id in dep_ids:
                    if dep_id not in selected_ids:
                        dep_mem = self.store.get_memory(dep_id)
                        if dep_mem and dep_mem.status.value == "active":
                            dep_cost = dep_mem.token_count or 1
                            if used_tokens + dep_cost <= effective_budget:
                                dep_ret = RetrievedMemory(
                                    memory=dep_mem,
                                    relevance_score=item.relevance_score * 0.9,
                                    retrieval_reasons=[f"Dependency of selected memory {mem.id[:8]}"],
                                )
                                selected.append(dep_ret)
                                selected_ids.add(dep_id)
                                used_tokens += dep_cost
                                preserved_dependencies.append(f"{dep_id[:8]} for {mem.id[:8]}")
            else:
                excluded.append({
                    "id": mem.id,
                    "reason": "Exceeded token budget",
                    "cost": cost,
                    "relevance": round(item.relevance_score, 3),
                    "is_protected": mem.is_protected,
                })

        utilization = (used_tokens / token_budget) * 100.0

        return ContextBuildResult(
            project_id=project_id,
            task_query=task_query,
            token_budget=token_budget,
            used_tokens=used_tokens,
            budget_utilization_pct=round(utilization, 2),
            selected_memories=selected,
            excluded_memories=excluded,
            preserved_dependencies=preserved_dependencies,
            conflicts_detected=conflicts_detected,
            compression_applied=False,
        )
