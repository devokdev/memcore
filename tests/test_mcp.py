"""Fast test verifying all MCP tools execute with valid schemas and return expected contracts."""

import os
import tempfile
import pytest

from memcore.mcp_server import (
    get_memcore,
    memory_add,
    memory_context_build,
    memory_gc_execute,
    memory_gc_preview,
    memory_get,
    memory_protect,
    memory_search,
    memory_stats,
    memory_update,
    memory_verify,
)


@pytest.fixture(autouse=True)
def setup_mcp_env():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "mcp_test.db")
    os.environ["MEMCORE_DB_PATH"] = db_path
    os.environ["MEMCORE_REPO_ROOT"] = tmp_dir
    # Reset singleton
    import memcore.mcp_server as srv
    srv._memcore_instance = None
    yield
    try:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass


def test_mcp_tools_lifecycle():
    # 1. memory_add
    res_add = memory_add(
        content="JWT secret key must be stored in environment variables, never hardcoded",
        memory_type="security_constraint",
        importance=0.95,
        is_protected=True,
        protection_reason="Security policy",
    )
    assert res_add["status"] == "success"
    mem_id = res_add["memory_id"]
    assert mem_id is not None
    assert res_add["is_protected"] is True

    # 2. memory_get
    record = memory_get(mem_id)
    assert record["id"] == mem_id
    assert "JWT secret key" in record["content"]

    # 3. memory_search
    results = memory_search(query="JWT secret key security", top_k=3)
    assert len(results) > 0
    assert results[0]["id"] == mem_id

    # 4. memory_update
    up_res = memory_update(memory_id=mem_id, importance=0.99)
    assert up_res["status"] == "success"
    assert up_res["version"] == 2

    # 5. memory_verify
    v_res = memory_verify(mem_id)
    assert "status" in v_res

    # 6. memory_context_build
    ctx = memory_context_build(task_query="Configure JWT auth", token_budget=500)
    assert ctx["used_tokens"] > 0
    assert len(ctx["selected_memories"]) > 0

    # 7. memory_gc_preview & execute
    preview = memory_gc_preview()
    assert len(preview) > 0
    # Protected memory must recommend PROTECT
    assert preview[0]["action"] == "PROTECT"

    gc_exec = memory_gc_execute(allow_delete=False)
    assert "summary" in gc_exec

    # 8. memory_stats
    stats = memory_stats()
    assert stats["total_memories"] >= 1
    assert stats["protected_count"] >= 1
