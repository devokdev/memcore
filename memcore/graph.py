"""Lightweight memory relationship graph manager."""

from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple

from memcore.models import MemoryRelationship, RelationshipType
from memcore.storage import BaseMemoryStore


class MemoryGraph:
    """Manages directed knowledge relationships between memory records."""

    def __init__(self, store: BaseMemoryStore):
        self.store = store

    def link(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationshipType,
        confidence: float = 1.0,
        metadata: Optional[Dict] = None,
    ) -> MemoryRelationship:
        rel = MemoryRelationship(
            source_id=source_id,
            target_id=target_id,
            rel_type=rel_type,
            confidence=confidence,
            metadata=metadata or {},
        )
        self.store.add_relationship(rel)
        return rel

    def get_neighbors(self, memory_id: str) -> List[MemoryRelationship]:
        return self.store.get_relationships(memory_id)

    def get_incoming_dependencies(self, memory_id: str) -> List[str]:
        """Find other memories that DEPEND_ON, DERIVED_FROM, or are USED_BY this memory."""
        rels = self.store.get_relationships(memory_id)
        incoming = []
        for r in rels:
            # If target is this memory and source depends on it
            if r.target_id == memory_id and r.rel_type in (RelationshipType.DEPENDS_ON, RelationshipType.DERIVED_FROM):
                incoming.append(r.source_id)
            elif r.source_id == memory_id and r.rel_type == RelationshipType.USED_BY:
                incoming.append(r.target_id)
        return incoming

    def get_outgoing_dependencies(self, memory_id: str) -> List[str]:
        """Find memories that this memory depends on or is supported by."""
        rels = self.store.get_relationships(memory_id)
        outgoing = []
        for r in rels:
            if r.source_id == memory_id and r.rel_type in (RelationshipType.DEPENDS_ON, RelationshipType.DERIVED_FROM, RelationshipType.SUPPORTED_BY):
                outgoing.append(r.target_id)
            elif r.target_id == memory_id and r.rel_type == RelationshipType.USED_BY:
                outgoing.append(r.source_id)
        return outgoing

    def traverse_subgraph(self, root_id: str, max_depth: int = 2) -> Set[str]:
        """BFS exploration of connected memories."""
        visited: Set[str] = {root_id}
        queue = deque([(root_id, 0)])

        while queue:
            curr, depth = queue.popleft()
            if depth >= max_depth:
                continue

            rels = self.store.get_relationships(curr)
            for r in rels:
                neighbor = r.target_id if r.source_id == curr else r.source_id
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))

        return visited
