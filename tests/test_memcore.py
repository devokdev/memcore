"""Comprehensive test suite for MemCore."""

import os
import tempfile
import pytest

from memcore.manager import MemCore
from memcore.models import (
    GCAction,
    MemoryStatus,
    MemoryType,
    RelationshipType,
    VerificationStatus,
)
from memcore.security import redact_secrets
from memcore.tokenizer import count_tokens


@pytest.fixture
def temp_memcore():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test_memcore.db")
    mc = MemCore(db_path=db_path, repo_root=tmp_dir)
    yield mc, tmp_dir
    try:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass


def test_secret_redaction():
    text = "Connecting with sk-proj-1234567890abcdef1234567890abcdef1234567890 and password='mysecretpassword123'"
    sanitized, was_redacted = redact_secrets(text)
    assert was_redacted is True
    assert "sk-proj" not in sanitized
    assert "mysecretpassword123" not in sanitized
    assert "[REDACTED" in sanitized


def test_token_counting():
    text = "MemCore provides intelligent memory infrastructure for AI coding agents."
    tokens, is_est = count_tokens(text)
    assert tokens > 0
    assert isinstance(tokens, int)


def test_persistence_and_retrieval(temp_memcore):
    mc, _ = temp_memcore
    # Add memories
    m1 = mc.add_memory(
        content="The authentication system uses OAuth2 with PKCE flow in auth/service.py",
        memory_type=MemoryType.ARCHITECTURE,
        importance=0.9,
        associated_files=["auth/service.py"],
        associated_symbols=["OAuthService"],
    )
    m2 = mc.add_memory(
        content="UI uses Tailwind and CSS dark theme for frontend components",
        memory_type=MemoryType.CONVENTION,
        importance=0.4,
    )

    # Retrieval
    results = mc.search_memories(query="OAuth authentication security flow", top_k=5)
    assert len(results) > 0
    assert results[0].memory.id == m1.id
    assert "Semantic similarity" in results[0].retrieval_reasons[0] or "Keyword" in results[0].retrieval_reasons[0]


def test_token_budget_optimizer(temp_memcore):
    mc, _ = temp_memcore
    for i in range(15):
        mc.add_memory(
            content=f"Important architectural detail item number {i} regarding database sharding and indexes.",
            memory_type=MemoryType.ARCHITECTURE,
            importance=0.5 + (i * 0.03),
        )

    # Request small budget
    ctx = mc.build_context(task_query="database indexes", token_budget=150)
    assert ctx.used_tokens <= 150
    assert len(ctx.selected_memories) > 0
    assert len(ctx.excluded_memories) > 0
    assert ctx.budget_utilization_pct <= 100.0


def test_repository_verification(temp_memcore):
    mc, tmpdir = temp_memcore
    # Create an actual file on disk
    src_dir = os.path.join(tmpdir, "src")
    os.makedirs(src_dir, exist_ok=True)
    file_path = os.path.join(src_dir, "db.py")
    with open(file_path, "w") as f:
        f.write("class DatabaseConnectionPool:\n    pass\n")

    # Add verified memory
    m_valid = mc.add_memory(
        content="DatabaseConnectionPool handles all query pooling in src/db.py",
        memory_type=MemoryType.CODE_LOCATION,
        associated_files=["src/db.py"],
        associated_symbols=["DatabaseConnectionPool"],
    )
    # Add stale memory with missing file
    m_stale = mc.add_memory(
        content="Redis cache manager in src/cache.py",
        memory_type=MemoryType.CODE_LOCATION,
        associated_files=["src/cache.py"],
        associated_symbols=["CacheManager"],
    )

    res_valid = mc.verify_memory(m_valid.id)
    assert res_valid.status == VerificationStatus.VERIFIED
    assert len(res_valid.evidence) > 0

    res_stale = mc.verify_memory(m_stale.id)
    assert res_stale.status == VerificationStatus.STALE
    assert len(res_stale.conflicts) > 0


def test_memgc_protection_and_rules(temp_memcore):
    mc, _ = temp_memcore
    # Add protected security constraint
    sec_mem = mc.add_memory(
        content="Never log raw authorization tokens or passwords in console logs",
        memory_type=MemoryType.SECURITY_CONSTRAINT,
        importance=0.95,
        is_protected=True,
        protection_reason="Critical security baseline",
    )

    # Add low-utility obsolete memory
    obs_mem = mc.add_memory(
        content="Temporary scratch note for debugging port 8080 collision",
        memory_type=MemoryType.GENERAL,
        importance=0.1,
    )

    recs = mc.preview_gc()
    rec_dict = {r.memory_id: r for r in recs}

    # Protected rule check
    assert rec_dict[sec_mem.id].action == GCAction.PROTECT
    # Obsolete memory should be candidate for deletion or archival
    assert rec_dict[obs_mem.id].action in (GCAction.DELETE, GCAction.ARCHIVE)

    # Attempting to delete protected memory must fail
    with pytest.raises(PermissionError):
        mc.delete_memory(sec_mem.id)


def test_memory_merging_and_superseding(temp_memcore):
    mc, _ = temp_memcore
    m1 = mc.add_memory(
        content="The application uses PostgreSQL for persistent data.",
        memory_type=MemoryType.ARCHITECTURE,
    )
    m2 = mc.add_memory(
        content="The production database is PostgreSQL for all persistent application records.",
        memory_type=MemoryType.ARCHITECTURE,
    )

    recs = mc.preview_gc()
    merge_recs = [r for r in recs if r.action == GCAction.MERGE]
    assert len(merge_recs) > 0

    # Execute GC
    res = mc.execute_gc()
    assert res["summary"]["MERGE"] >= 1
    # Check that m2 is now superseded
    m2_updated = mc.get_memory(m2.id)
    assert m2_updated.status == MemoryStatus.SUPERSEDED
    assert m2_updated.superseded_by == m1.id
