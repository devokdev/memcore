"""Utility and risk scoring models inspired by MemGC with explicit safety policies."""

import math
import time
from typing import Dict, List, Optional

from memcore.graph import MemoryGraph
from memcore.models import (
    MemoryRecord,
    MemoryType,
    RiskScore,
    UtilityScore,
    VerificationStatus,
)
from memcore.storage import BaseMemoryStore


class MemoryScorer:
    """Computes interpretable utility and risk scores for memory management and GC."""

    def __init__(self, store: BaseMemoryStore, graph: Optional[MemoryGraph] = None):
        self.store = store
        self.graph = graph or MemoryGraph(store)

    def calculate_utility(
        self,
        memory: MemoryRecord,
        task_query: Optional[str] = None,
        task_relevance: float = 0.0,
    ) -> UtilityScore:
        """Calculates utility based on relevance, importance, recency, usage, and verification."""
        now = time.time()
        age_seconds = max(0.0, now - memory.updated_at)
        # Recency score [0..1], decay over ~30 days
        recency = math.exp(-age_seconds / 2592000.0)

        # Frequency score normalized (saturates at 10 uses)
        frequency = min(1.0, memory.usage_count / 10.0)

        # Verification bonus
        v_bonus = 0.0
        if memory.verification_status == VerificationStatus.VERIFIED:
            v_bonus = 0.2
        elif memory.verification_status in (VerificationStatus.STALE, VerificationStatus.CONFLICT):
            v_bonus = -0.3

        # Connected dependencies bonus
        dependents = self.graph.get_incoming_dependencies(memory.id)
        dep_weight = min(0.3, len(dependents) * 0.1)

        # Base utility formulation
        # For memories with 0 usage, recency alone shouldn't inflate low-importance scratch memories
        # Recency is weighted more when the memory has been used or has baseline importance
        effective_recency = recency * (0.5 + 0.5 * memory.importance) if memory.usage_count == 0 else recency
        base = (
            (0.40 * memory.importance)
            + (0.15 * effective_recency)
            + (0.20 * frequency)
            + (0.15 * memory.confidence)
            + (0.10 * min(1.0, len(dependents) / 3.0))
            + v_bonus
        )

        if task_query:
            # If task query provided, blend 50% task relevance with 50% persistent utility
            composite = 0.5 * task_relevance + 0.5 * base
        else:
            composite = base

        score = max(0.0, min(1.0, composite))

        return UtilityScore(
            memory_id=memory.id,
            score=score,
            relevance=task_relevance,
            recency=recency,
            frequency=frequency,
            importance=memory.importance,
            confidence=memory.confidence,
            verification_bonus=v_bonus,
            dependency_weight=dep_weight,
            breakdown={
                "base_utility": base,
                "recency": recency,
                "frequency": frequency,
                "dependents_count": len(dependents),
                "verification_bonus": v_bonus,
            },
        )

    def calculate_risk(self, memory: MemoryRecord) -> RiskScore:
        """Calculates risk of deleting or heavily compressing this memory."""
        factors: List[str] = []
        security_risk = 0.0
        type_risk = 0.0
        dep_risk = 0.0
        prot_risk = 0.0

        # 1. Protected memory is maximum risk to delete
        if memory.is_protected:
            prot_risk = 1.0
            factors.append(f"Memory explicitly protected ({memory.protection_reason or 'No reason provided'})")

        # 2. Critical types (Security constraint, DB schema, Bug fix lesson, Architecture)
        if memory.memory_type == MemoryType.SECURITY_CONSTRAINT:
            type_risk = 0.95
            security_risk = 0.95
            factors.append("Security constraint: accidental removal poses vulnerability hazard")
        elif memory.memory_type == MemoryType.DB_SCHEMA:
            type_risk = 0.85
            factors.append("Database schema contract: critical for migration and persistence integrity")
        elif memory.memory_type == MemoryType.BUG_FIX:
            type_risk = 0.75
            factors.append("Bug fix lesson: prevents re-introducing known regression")
        elif memory.memory_type == MemoryType.ARCHITECTURE:
            type_risk = 0.70
            factors.append("Architecture decision: foundational structural knowledge")

        # 3. Graph Dependency risk
        dependents = self.graph.get_incoming_dependencies(memory.id)
        if dependents:
            dep_risk = min(0.9, 0.4 + 0.15 * len(dependents))
            factors.append(f"Depended upon by {len(dependents)} other active memory records")

        # Composite risk: take maximum of dominant factors with slight accumulation
        combined = max(prot_risk, security_risk, type_risk, dep_risk)
        if memory.importance >= 0.8 and combined < 0.8:
            combined = 0.8
            factors.append(f"High user-assigned importance ({memory.importance})")

        return RiskScore(
            memory_id=memory.id,
            risk_score=min(1.0, combined),
            security_risk=security_risk,
            critical_type_risk=type_risk,
            dependency_risk=dep_risk,
            protected_risk=prot_risk,
            factors=factors,
        )
