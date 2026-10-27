"""Model Context Protocol (MCP) Server for MemCore."""

import os
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from memcore.manager import MemCore
from memcore.models import MemoryType

# Initialize FastMCP Server
mcp_server = FastMCP("MemCore")

# MemCore instance
_memcore_instance: Optional[MemCore] = None


def get_memcore() -> MemCore:
    global _memcore_instance
    if _memcore_instance is None:
        db_path = os.environ.get("MEMCORE_DB_PATH", "memcore.db")
        repo_root = os.environ.get("MEMCORE_REPO_ROOT", os.getcwd())
        _memcore_instance = MemCore(db_path=db_path, repo_root=repo_root)
    return _memcore_instance


@mcp_server.tool()
def memory_add(
    content: str,
    memory_type: str = "general",
    project_id: str = "default",
    importance: float = 0.5,
    associated_files: Optional[List[str]] = None,
    associated_symbols: Optional[List[str]] = None,
    is_protected: bool = False,
    protection_reason: Optional[str] = None,
):
    """Store a new verified memory in MemCore with automatic secret redaction and token counting."""
    mc = get_memcore()
    try:
        mtype = MemoryType(memory_type)
    except ValueError:
        mtype = MemoryType.GENERAL

    record = mc.add_memory(
        content=content,
        memory_type=mtype,
        project_id=project_id,
        importance=importance,
        associated_files=associated_files or [],
        associated_symbols=associated_symbols or [],
        is_protected=is_protected,
        protection_reason=protection_reason,
    )
    return {
        "status": "success",
        "memory_id": record.id,
        "token_count": record.token_count,
        "is_protected": record.is_protected,
    }


@mcp_server.tool()
def memory_search(
    query: str,
    project_id: str = "default",
    top_k: int = 5,
    include_superseded: bool = False,
):
    """Search project memories using hybrid semantic + keyword + recency retrieval."""
    mc = get_memcore()
    results = mc.search_memories(
        query=query,
        project_id=project_id,
        top_k=top_k,
        include_superseded=include_superseded,
    )
    return [
        {
            "id": r.memory.id,
            "content": r.memory.content,
            "type": r.memory.memory_type.value,
            "score": round(r.relevance_score, 3),
            "reasons": r.retrieval_reasons,
            "verification_status": r.memory.verification_status.value,
            "is_protected": r.memory.is_protected,
            "token_count": r.memory.token_count,
        }
        for r in results
    ]


@mcp_server.tool()
def memory_get(memory_id: str):
    """Retrieve full details of a specific memory record."""
    mc = get_memcore()
    mem = mc.get_memory(memory_id)
    if not mem:
        return {"error": f"Memory {memory_id} not found"}
    return mem.model_dump()


@mcp_server.tool()
def memory_update(
    memory_id: str,
    content: Optional[str] = None,
    importance: Optional[float] = None,
    associated_files: Optional[List[str]] = None,
    associated_symbols: Optional[List[str]] = None,
):
    """Update an existing memory with version tracking and audit logging."""
    mc = get_memcore()
    updated = mc.update_memory(
        memory_id=memory_id,
        content=content,
        importance=importance,
        associated_files=associated_files,
        associated_symbols=associated_symbols,
    )
    if not updated:
        return {"error": f"Memory {memory_id} not found"}
    return {"status": "success", "version": updated.version, "memory_id": updated.id}


@mcp_server.tool()
def memory_verify(memory_id: str):
    """Verify a memory against current repository files and symbols."""
    mc = get_memcore()
    res = mc.verify_memory(memory_id)
    if not res:
        return {"error": f"Memory {memory_id} not found"}
    return res.model_dump()


@mcp_server.tool()
def memory_protect(memory_id: str, reason: str = "Protected by user"):
    """Mark a memory as protected to prevent automated deletion or destructive changes."""
    mc = get_memcore()
    record = mc.protect_memory(memory_id, reason=reason)
    if not record:
        return {"error": f"Memory {memory_id} not found"}
    return {"status": "success", "memory_id": memory_id, "is_protected": True}


@mcp_server.tool()
def memory_context_build(
    task_query: str,
    token_budget: int = 2000,
    project_id: str = "default",
):
    """Build optimized context within a specified token budget."""
    mc = get_memcore()
    res = mc.build_context(task_query=task_query, token_budget=token_budget, project_id=project_id)
    return {
        "used_tokens": res.used_tokens,
        "token_budget": res.token_budget,
        "budget_utilization_pct": res.budget_utilization_pct,
        "selected_memories_count": len(res.selected_memories),
        "selected_memories": [
            {
                "id": m.memory.id,
                "content": m.memory.content,
                "relevance": round(m.relevance_score, 3),
                "token_count": m.memory.token_count,
            }
            for m in res.selected_memories
        ],
        "excluded_count": len(res.excluded_memories),
        "preserved_dependencies": res.preserved_dependencies,
        "conflicts": res.conflicts_detected,
    }


@mcp_server.tool()
def memory_gc_preview(project_id: str = "default"):
    """Preview risk-aware garbage collection decisions without altering stored memories."""
    mc = get_memcore()
    recs = mc.preview_gc(project_id)
    return [
        {
            "memory_id": r.memory_id,
            "action": r.action.value,
            "utility": round(r.utility, 2),
            "risk": round(r.risk, 2),
            "reason": r.reason,
            "requires_approval": r.requires_approval,
        }
        for r in recs
    ]


@mcp_server.tool()
def memory_gc_execute(
    project_id: str = "default",
    allow_delete: bool = False,
    approved_memory_ids: Optional[List[str]] = None,
):
    """Execute risk-aware garbage collection adhering to safety thresholds."""
    mc = get_memcore()
    res = mc.execute_gc(
        project_id=project_id,
        allow_delete=allow_delete,
        approved_memory_ids=approved_memory_ids or [],
    )
    return res


@mcp_server.tool()
def memory_stats(project_id: str = "default"):
    """Get project memory statistics, active token counts, and health status."""
    mc = get_memcore()
    return mc.get_stats(project_id)


def start_server():
    """Start standard MCP server over stdio."""
    mcp_server.run()


if __name__ == "__main__":
    start_server()
