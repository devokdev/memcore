"""MemGC-style Risk-Aware Garbage Collection Engine."""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from memcore.compression import MemoryCompressor
from memcore.graph import MemoryGraph
from memcore.models import (
    GCAction,
    GCRecommendation,
    MemoryAuditLog,
    MemoryRecord,
    MemoryStatus,
    RelationshipType,
    VerificationStatus,
)
from memcore.scoring import MemoryScorer
from memcore.storage import BaseMemoryStore
from memcore.tokenizer import count_tokens

logger = logging.getLogger(__name__)


class MemoryGCEngine:
    """Intelligent risk-aware garbage collector and optimizer for long-term agent memory."""

    def __init__(
        self,
        store: BaseMemoryStore,
        scorer: Optional[MemoryScorer] = None,
        compressor: Optional[MemoryCompressor] = None,
        graph: Optional[MemoryGraph] = None,
        utility_threshold: float = 0.25,
        risk_delete_threshold: float = 0.40,
    ):
        self.store = store
        self.graph = graph or MemoryGraph(store)
        self.scorer = scorer or MemoryScorer(store, self.graph)
        self.compressor = compressor or MemoryCompressor()
        self.utility_threshold = utility_threshold
        self.risk_delete_threshold = risk_delete_threshold

    def preview_gc(self, project_id: str = "default") -> List[GCRecommendation]:
        """Analyzes active memories and generates recommendations without applying them."""
        memories = self.store.list_memories(project_id=project_id, status=MemoryStatus.ACTIVE, limit=500)
        # Sort by created_at ascending so earlier canonical memories absorb newer duplicate additions
        memories.sort(key=lambda m: m.created_at)
        recommendations: List[GCRecommendation] = []

        # Find potential merge candidates
        checked_pairs = set()

        for i, mem in enumerate(memories):
            u_score = self.scorer.calculate_utility(mem)
            r_score = self.scorer.calculate_risk(mem)

            # Check protected rule #1: Protected memories must not be automatically deleted
            if mem.is_protected:
                recommendations.append(
                    GCRecommendation(
                        memory_id=mem.id,
                        action=GCAction.PROTECT,
                        utility=u_score.score,
                        risk=r_score.risk_score,
                        reason=f"Protected: {mem.protection_reason or 'Explicit policy'}",
                        requires_approval=False,
                    )
                )
                continue

            # Check for duplicates or mergeable pairs
            merged_candidate_found = False
            for j in range(i + 1, len(memories)):
                other = memories[j]
                pair_key = tuple(sorted([mem.id, other.id]))
                if pair_key in checked_pairs:
                    continue

                compatible, reason = self.compressor.are_compatible_to_merge(mem, other)
                if compatible:
                    checked_pairs.add(pair_key)
                    recommendations.append(
                        GCRecommendation(
                            memory_id=mem.id,
                            action=GCAction.MERGE,
                            utility=u_score.score,
                            risk=r_score.risk_score,
                            reason=f"High redundancy with memory {other.id[:8]}: {reason}",
                            candidate_merge_with=other.id,
                            requires_approval=r_score.risk_score >= 0.9,
                        )
                    )
                    merged_candidate_found = True
                    break

            if merged_candidate_found:
                continue

            # Check if stale or conflicting with code
            if mem.verification_status == VerificationStatus.CONFLICT:
                recommendations.append(
                    GCRecommendation(
                        memory_id=mem.id,
                        action=GCAction.UPDATE,
                        utility=u_score.score,
                        risk=r_score.risk_score,
                        reason=f"Repository conflict detected: {mem.verification_notes or 'Requires sync'}",
                        requires_approval=True,
                    )
                )
                continue

            # Check if verbose and compressible
            if mem.token_count > 60:
                compressed_text, ratio = self.compressor.compress_text(mem.content)
                if ratio > 0.20:
                    recommendations.append(
                        GCRecommendation(
                            memory_id=mem.id,
                            action=GCAction.COMPRESS,
                            utility=u_score.score,
                            risk=r_score.risk_score,
                            reason=f"Potential {ratio*100:.1f}% token reduction without losing key constraints",
                            target_content=compressed_text,
                            requires_approval=r_score.risk_score > 0.6,
                        )
                    )
                    continue

            # If low utility
            if u_score.score < self.utility_threshold:
                # If high risk or has dependents, archive instead of deleting
                if r_score.risk_score > self.risk_delete_threshold:
                    recommendations.append(
                        GCRecommendation(
                            memory_id=mem.id,
                            action=GCAction.ARCHIVE,
                            utility=u_score.score,
                            risk=r_score.risk_score,
                            reason=f"Low recent utility ({u_score.score:.2f}) but retained due to risk factors ({'; '.join(r_score.factors)})",
                            requires_approval=False,
                        )
                    )
                else:
                    # Safe to delete candidate
                    recommendations.append(
                        GCRecommendation(
                            memory_id=mem.id,
                            action=GCAction.DELETE,
                            utility=u_score.score,
                            risk=r_score.risk_score,
                            reason=f"Low utility ({u_score.score:.2f}) and low risk ({r_score.risk_score:.2f})",
                            requires_approval=True,  # Safety safeguard: deletes require approval
                        )
                    )
            else:
                recommendations.append(
                    GCRecommendation(
                        memory_id=mem.id,
                        action=GCAction.KEEP,
                        utility=u_score.score,
                        risk=r_score.risk_score,
                        reason=f"Healthy memory (Utility: {u_score.score:.2f}, Risk: {r_score.risk_score:.2f})",
                    )
                )

        return recommendations

    def execute_gc(
        self,
        project_id: str = "default",
        allow_delete: bool = False,
        approved_memory_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Executes garbage collection operations adhering to policy constraints."""
        approved = set(approved_memory_ids or [])
        recommendations = self.preview_gc(project_id)
        
        counts = {action.value: 0 for action in GCAction}
        applied_actions = []

        for rec in recommendations:
            mem = self.store.get_memory(rec.memory_id)
            if not mem:
                continue

            prev_state = mem.model_dump()

            if rec.action == GCAction.KEEP or rec.action == GCAction.PROTECT:
                counts[rec.action.value] += 1
                continue

            # If action requires approval and not approved, keep/skip
            if rec.requires_approval and mem.id not in approved and not allow_delete:
                logger.info(f"Skipping unapproved destructive/high-risk action {rec.action.value} on {mem.id}")
                counts[GCAction.KEEP.value] += 1
                continue

            if rec.action == GCAction.ARCHIVE:
                mem.status = MemoryStatus.ARCHIVED
                mem.updated_at = time.time()
                self.store.update_memory(mem)
                self.store.record_audit(
                    MemoryAuditLog(
                        memory_id=mem.id,
                        action="archive",
                        actor="mem_gc",
                        previous_state=prev_state,
                        new_state=mem.model_dump(),
                        reason=rec.reason,
                    )
                )
                counts[GCAction.ARCHIVE.value] += 1
                applied_actions.append({"memory_id": mem.id, "action": "ARCHIVE", "reason": rec.reason})

            elif rec.action == GCAction.COMPRESS and rec.target_content:
                mem.content = rec.target_content
                mem.token_count, mem.estimated_token = count_tokens(rec.target_content)
                mem.status = MemoryStatus.COMPRESSED
                mem.updated_at = time.time()
                mem.version += 1
                self.store.update_memory(mem)
                self.store.record_audit(
                    MemoryAuditLog(
                        memory_id=mem.id,
                        action="compress",
                        actor="mem_gc",
                        previous_state=prev_state,
                        new_state=mem.model_dump(),
                        reason=rec.reason,
                    )
                )
                counts[GCAction.COMPRESS.value] += 1
                applied_actions.append({"memory_id": mem.id, "action": "COMPRESS", "reason": rec.reason})

            elif rec.action == GCAction.MERGE and rec.candidate_merge_with:
                other = self.store.get_memory(rec.candidate_merge_with)
                if other and other.status == MemoryStatus.ACTIVE:
                    merged_content, files, symbols = self.compressor.merge_memories(mem, other)
                    # Update mem with merged content
                    mem.content = merged_content
                    mem.associated_files = files
                    mem.associated_symbols = symbols
                    mem.token_count, mem.estimated_token = count_tokens(merged_content)
                    mem.parent_memory_ids = list(set(mem.parent_memory_ids + [other.id]))
                    mem.version += 1
                    mem.updated_at = time.time()
                    self.store.update_memory(mem)

                    # Mark other as SUPERSEDED
                    other_prev = other.model_dump()
                    other.status = MemoryStatus.SUPERSEDED
                    other.superseded_by = mem.id
                    other.updated_at = time.time()
                    self.store.update_memory(other)

                    # Link in graph
                    self.graph.link(
                        source_id=mem.id,
                        target_id=other.id,
                        rel_type=RelationshipType.SUPERSEDES,
                        metadata={"action": "merge_gc"},
                    )

                    self.store.record_audit(
                        MemoryAuditLog(
                            memory_id=mem.id,
                            action="merge",
                            actor="mem_gc",
                            previous_state=prev_state,
                            new_state=mem.model_dump(),
                            reason=f"Merged with {other.id}",
                        )
                    )
                    self.store.record_audit(
                        MemoryAuditLog(
                            memory_id=other.id,
                            action="supersede",
                            actor="mem_gc",
                            previous_state=other_prev,
                            new_state=other.model_dump(),
                            reason=f"Merged into {mem.id}",
                        )
                    )
                    counts[GCAction.MERGE.value] += 1
                    applied_actions.append({"memory_id": mem.id, "action": "MERGE", "merged_with": other.id})

            elif rec.action == GCAction.DELETE:
                if allow_delete or mem.id in approved:
                    self.store.delete_memory(mem.id, hard_delete=False)
                    self.store.record_audit(
                        MemoryAuditLog(
                            memory_id=mem.id,
                            action="soft_delete",
                            actor="mem_gc",
                            previous_state=prev_state,
                            new_state={"status": "soft_deleted"},
                            reason=rec.reason,
                        )
                    )
                    counts[GCAction.DELETE.value] += 1
                    applied_actions.append({"memory_id": mem.id, "action": "DELETE", "reason": rec.reason})

        return {
            "summary": counts,
            "actions_applied": applied_actions,
            "total_evaluated": len(recommendations),
        }
