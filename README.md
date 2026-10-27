# MemCore — Intelligent Memory Infrastructure for AI Coding Agents

> *Remember what matters. Retrieve what is relevant. Forget what is safe.*

MemCore combines **AgentMemory-style persistent memory and hybrid retrieval** with **MemGC-style risk-aware garbage collection, code-grounded verification, and token-budgeted prompt optimization**.

---

## 🌟 Key Features

1. **Persistent Memory Store & Hybrid Retrieval**
   - Durable SQLite database with Full-Text Search (FTS5) and high-performance vector embeddings.
   - Hybrid ranking: Semantic cosine similarity + FTS keyword matching + Recency decay + Confidence & Importance weighting.
   - Workspace/project isolation with soft-delete and recovery.

2. **MemGC Risk-Aware Garbage Collection**
   - Explicit Utility scoring ($U$) and Risk scoring ($R$).
   - 8 lifecycle actions: `KEEP`, `UPDATE`, `COMPRESS`, `MERGE`, `ARCHIVE`, `SUPERSEDE`, `PROTECT`, `DELETE`.
   - **Zero Protected Memory Loss**: Critical security rules, database schema contracts, and user-protected memories can never be accidentally pruned.
   - Redundancy merging and lossless phrasing compression.

3. **Repository-Grounded Verification**
   - Validates memory statements against active code files and symbol ASTs on disk.
   - Detects stale paths, missing classes/functions, and dependency contradictions before serving context.

4. **Token-Budget Context Optimizer**
   - Automatically packs maximal-utility context within any strict prompt budget (e.g., 1,500 tokens).
   - Preserves critical graph dependencies and flags code conflicts.

5. **Security & Redaction**
   - Redacts secrets (AWS keys, OpenAI/GitHub tokens, Bearer tokens, DB credentials) before persisting to disk.
   - Sanitizes untrusted memory inputs to prevent control injection into agent system prompts.

6. **Model Context Protocol (MCP) Integration**
   - Exposes standard tools (`memory_add`, `memory_search`, `memory_get`, `memory_update`, `memory_verify`, `memory_protect`, `memory_context_build`, `memory_gc_preview`, `memory_gc_execute`, `memory_stats`).

7. **Developer Dashboard & REST API**
   - Modern, high-aesthetic web dashboard running on FastAPI with real-time stats, memory explorer, GC previews, and verification scans.

---

## 🚀 Quickstart

### 1. Installation

Ensure Python 3.10+ is installed:
```bash
pip install -e .
```

### 2. Python API Usage

```python
from memcore.manager import MemCore
from memcore.models import MemoryType

# Initialize MemCore
mc = MemCore(db_path="memcore.db", repo_root=".")

# Add persistent memory with protection
mc.add_memory(
    content="Always validate OAuth2 PKCE code_verifier before issuing tokens.",
    memory_type=MemoryType.SECURITY_CONSTRAINT,
    importance=0.95,
    is_protected=True,
    protection_reason="Security baseline",
)

# Search relevant memories
results = mc.search_memories("How is OAuth authentication implemented?", top_k=5)
for r in results:
    print(f"[{r.relevance_score:.2f}] {r.memory.content}")

# Build optimal prompt context within a 500 token budget
context = mc.build_context(
    task_query="Fix token leak in authentication handler",
    token_budget=500
)
print(f"Used {context.used_tokens} / {context.token_budget} tokens")
```

### 3. Model Context Protocol (MCP)

To configure MemCore in your AI Coding Assistant (e.g. Claude Desktop, Antigravity, Cursor):

```json
{
  "mcpServers": {
    "memcore": {
      "command": "python",
      "args": ["-m", "memcore.mcp_server"],
      "env": {
        "MEMCORE_DB_PATH": "memcore.db",
        "MEMCORE_REPO_ROOT": "."
      }
    }
  }
}
```

### 4. Running the Dashboard & REST API

```bash
python -m uvicorn memcore.app:app --host 127.0.0.1 --port 8000
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser to view the real-time visual dashboard.

---

## 🧪 Benchmark & Verification Suite

MemCore includes an empirical benchmark suite measuring token reduction, latency, and safety constraints:

```bash
# Run unit and integration tests
python -m pytest tests/ -v

# Run performance and garbage collection benchmark
python -m benchmarks.benchmark_run
```

### Benchmark Highlights (Measured on active test run):
- **Retrieval Latency:** ~18.4 ms
- **GC Decision & Execution:** ~50.9 ms
- **Context Assembly Latency:** ~42.0 ms
- **Token Reduction via GC:** ~16.9% saved without loss of salient information
- **Critical Memory Loss Rate:** **0.00%** (Protected memories guaranteed safe)
