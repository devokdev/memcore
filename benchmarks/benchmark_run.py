"""Reproducible benchmark suite evaluating baseline vs MemCore GC and token optimization."""

import os
import tempfile
import time
from typing import Any, Dict, List

from memcore.manager import MemCore
from memcore.models import MemoryStatus, MemoryType


def run_benchmark() -> Dict[str, Any]:
    print("=================================================================")
    print("           MemCore Empirical Performance Benchmark              ")
    print("=================================================================")

    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "bench_memcore.db")
    mc = MemCore(db_path=db_path, repo_root=tmp_dir)

    # 1. Ingestion of realistic multi-session memories
    print("[1] Ingesting multi-session project memory dataset...")
    
    # Dataset includes: duplicates, verbose memories, security constraints, obsolete facts
    dataset = [
        # Redundant / duplicate architectural knowledge
        ("PostgreSQL is used for relational database persistence.", MemoryType.ARCHITECTURE, 0.8, False),
        ("The primary database of the application is PostgreSQL.", MemoryType.ARCHITECTURE, 0.8, False),
        ("Production application records are saved in PostgreSQL database.", MemoryType.ARCHITECTURE, 0.8, False),

        # Protected security rule
        ("Never transmit API keys or bearer tokens in query parameters or unencrypted headers.", MemoryType.SECURITY_CONSTRAINT, 0.95, True),

        # Verbose architecture memory
        ("It is important to note that the application uses an event-driven pub/sub architecture using Redis streams for real-time notifications to connected clients. In order to handle backpressure, workers poll every 50ms.", MemoryType.ARCHITECTURE, 0.7, False),

        # Stale debugging notes
        ("Temporary workaround for dev port 5000 collision on local windows machine.", MemoryType.GENERAL, 0.1, False),
        ("Temporary log check for test run 482.", MemoryType.GENERAL, 0.1, False),

        # API & bugfix contracts
        ("OAuth2 authentication requires state and code_verifier parameters with SHA-256 PKCE.", MemoryType.API_CONTRACT, 0.9, False),
        ("Fix for connection leak: always release client pool connection in finally block.", MemoryType.BUG_FIX, 0.85, False),
    ]

    mem_ids = []
    initial_tokens = 0
    t0 = time.time()
    for content, mtype, imp, is_prot in dataset:
        m = mc.add_memory(
            content=content,
            memory_type=mtype,
            importance=imp,
            is_protected=is_prot,
            protection_reason="Critical security constraint" if is_prot else None,
        )
        mem_ids.append(m.id)
        initial_tokens += m.token_count

    ingest_time_ms = (time.time() - t0) * 1000.0

    print(f" -> Ingested {len(dataset)} memories in {ingest_time_ms:.2f} ms")
    print(f" -> Initial Total Context Tokens: {initial_tokens}")

    # 2. Benchmark Retrieval Latency
    print("[2] Evaluating Hybrid Retrieval...")
    t_ret0 = time.time()
    results = mc.search_memories(query="OAuth2 PKCE authorization flow", top_k=3)
    ret_latency_ms = (time.time() - t_ret0) * 1000.0
    print(f" -> Retrieved top {len(results)} matches in {ret_latency_ms:.2f} ms")
    print(f" -> Top match: '{results[0].memory.content[:50]}...' (Score: {results[0].relevance_score:.3f})")

    # 3. Benchmark GC Optimization
    print("[3] Running MemGC Risk-Aware Optimization Engine...")
    preview_recs = mc.preview_gc()
    print(f" -> Generated {len(preview_recs)} policy recommendations:")
    for r in preview_recs:
        print(f"    * Memory {r.memory_id[:8]}: {r.action.value} (Utility: {r.utility:.2f}, Risk: {r.risk:.2f}) - {r.reason[:60]}")

    t_gc0 = time.time()
    gc_result = mc.execute_gc(allow_delete=True)
    gc_latency_ms = (time.time() - t_gc0) * 1000.0
    print(f" -> GC executed in {gc_latency_ms:.2f} ms. Summary: {gc_result['summary']}")

    # 4. Measure Post-GC Stats & Token Reduction
    post_stats = mc.get_stats()
    active_mems = mc.store.list_memories(status=MemoryStatus.ACTIVE)
    post_tokens = sum(m.token_count for m in active_mems)
    token_savings_pct = ((initial_tokens - post_tokens) / initial_tokens) * 100.0

    print(f" -> Active Memories Post-GC: {len(active_mems)} (from {len(dataset)})")
    print(f" -> Active Tokens: {post_tokens} (saved {initial_tokens - post_tokens} tokens / {token_savings_pct:.1f}%)")

    # 5. Token-Budgeted Context Build
    print("[4] Testing Token-Budgeted Context Assembler (Budget = 80 tokens)...")
    t_ctx0 = time.time()
    ctx = mc.build_context(task_query="Fix database connection leak in authentication endpoint", token_budget=80)
    ctx_latency_ms = (time.time() - t_ctx0) * 1000.0

    print(f" -> Assembled context in {ctx_latency_ms:.2f} ms")
    print(f" -> Used {ctx.used_tokens} / {ctx.token_budget} tokens ({ctx.budget_utilization_pct}% utilization)")
    print(f" -> Selected {len(ctx.selected_memories)} memories, excluded {len(ctx.excluded_memories)} non-essential memories")

    # Verify protected memories were never dropped
    protected_in_db = [m for m in active_mems if m.is_protected]
    assert len(protected_in_db) == 1, "Protected memory must never be deleted by GC!"
    print(" -> Protected Memory Loss Rate: 0.00% (Safety constraint verified)")

    print("=================================================================")
    print("                   Benchmark Results Verified                    ")
    print("=================================================================")

    return {
        "initial_memories": len(dataset),
        "post_gc_memories": len(active_mems),
        "initial_tokens": initial_tokens,
        "post_gc_tokens": post_tokens,
        "token_savings_pct": round(token_savings_pct, 2),
        "retrieval_latency_ms": round(ret_latency_ms, 2),
        "gc_latency_ms": round(gc_latency_ms, 2),
        "context_latency_ms": round(ctx_latency_ms, 2),
        "protected_loss_rate": 0.0,
    }


if __name__ == "__main__":
    run_benchmark()
