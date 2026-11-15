# MemCore 🧠

> **Persistent, risk-aware memory for AI coding agents.**  
> *Remember what matters. Retrieve what is relevant. Forget what is safe.*

---

## 🌟 What is MemCore in Simple Words?

Every time you open an AI coding agent like **Claude Code**, **Cursor**, **Codex**, or **Antigravity**, **it starts with complete amnesia**.

You waste time re-explaining the same project rules:
- *"We use pnpm, not npm."*
- *"Never mock the database in integration tests."*
- *"Authentication tokens are validated in `auth.py`."*

If you try to paste all past conversations into the agent, the prompt gets **bloated with 20,000+ tokens**, which slows things down, costs a lot of money, and causes the AI to hallucinate.

**MemCore fixes this.** It acts like a smart brain on your computer:
1. **Captures** what the agent learned in previous sessions.
2. **Prunes the junk** and merges duplicates using **MemGC (risk-aware garbage collection)**.
3. **Verifies claims against real code** on your disk using AST parsing so the agent doesn't reference deleted functions.
4. **Protects critical rules** (security constraints, database contracts) with a **Zero-Loss Guarantee** ($0.00\%$ loss).
5. **Packs the best 1,500 tokens** into the prompt so the AI stays focused and fast.
6. **100% Local-first**: Everything runs on `127.0.0.1` on your machine. Zero bytes leave localhost.

---

## 🚀 Quickstart

### 1. Installation

Make sure you have **Python 3.10+** installed:

```bash
git clone https://github.com/devokdev/memcore.git
cd memcore
pip install -e .
```

---

## ⚡ Instant One-Command Setup for Any Project

To activate MemCore in **any new or existing project folder**, open a terminal in that project and run:

```bash
memcore init
```
*(or `python -m memcore.cli init`)*

### What this single command does automatically:
1. **Initializes Local Memory**: Sets up the project's local `memcore.db`.
2. **Registers the Global Antigravity Plugin**: Installs MemCore into `~/.gemini/config/plugins/memcore/` and configures MCP server tools (`memory_add`, `memory_context_build`, `memory_gc`, etc.) so Antigravity instantly gains persistent memory across all workspaces.
3. **Auto-Spawns the Floating Token HUD**: Launches the frameless, draggable Antigravity-styled pill bar floating right above your chatbox that tracks active tokens, pruned savings %, and protected invariants in real time.

---

## 💻 All Commands You Can Use

Here is the complete list of all commands available in MemCore:

### 1. Start the Web Dashboard & REST API
Starts the real-time visual dashboard and REST API on `http://127.0.0.1:8000`:
```bash
python -m uvicorn memcore.app:app --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser to inspect memories, run GC previews, and view verification reports.

### 2. Run the Showcase Landing Website
Runs the [agent-memory.dev](https://www.agent-memory.dev/) style interactive showcase page:
```bash
python -m http.server 3000 --directory website
```
Open **[http://localhost:3000](http://localhost:3000)** to interact with the 2D memory field canvas, token funnel simulator, and benchmark dot matrix.

### 3. Run the Performance & GC Benchmark
Measures hybrid retrieval latency, token reduction, and validates the Zero Protected Memory Loss invariant:
```bash
python -m benchmarks.benchmark_run
```

### 4. Run the Full Test Suite
Runs unit and integration tests across storage, verification, scoring, and MCP tools:
```bash
python -m pytest tests/ -v
```

### 5. Run the Pitch & Token Savings Experiment
Compares standard prompts vs. MemCore-optimized prompts to measure token savings:
```bash
python run_pitch_experiment.py
```

### 6. Run the Interactive Presentation Demo
Demonstrates the 5-step MemCore pipeline in your terminal:
```bash
python demo_presentation.py
```

### 7. Run the Model Context Protocol (MCP) Server
Runs the MCP stdio server to connect with Claude Desktop, Cursor, or Antigravity:
```bash
python -m memcore.mcp_server
```

### 8. Launch the Visual Token Counter & HUD
Launch the real-time visual token counter to monitor token consumption and savings while interacting with the agent or testing:
```bash
# Launch sleek floating desktop overlay (always-on-top, draggable)
python memcore_hud.py

# Or launch rich terminal live HUD
python memcore_hud.py --mode terminal

# Point to a specific database (e.g. from an experiment)
python memcore_hud.py --db pitch_experiment/project_b_with_memcore/memcore.db
```

---

## 🔌 Connecting to AI Agents via MCP

Add MemCore to your AI agent's config file (e.g., `claude_desktop_config.json`, Antigravity settings, or Cursor MCP configuration):

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

### Native MCP Tools Available to Agents:
- `memory_add`: Add a new persistent memory with optional protection flag.
- `memory_search`: Perform fast hybrid search (FTS5 BM25 + vector similarity).
- `memory_get`: Retrieve full memory details by ID.
- `memory_update`: Modify an existing memory.
- `memory_protect`: Lock a memory so it can never be pruned or deleted.
- `memory_verify`: Check whether code symbols referenced in memory still exist on disk.
- `memory_context_build`: Pack highest-utility context within a strict token budget.
- `memory_gc_preview`: Preview MemGC pruning decisions without applying changes.
- `memory_gc_execute`: Apply garbage collection decisions (merge, supersede, archive).
- `memory_stats`: View total memories, protected count, and project metrics.

---

## 🐍 Using MemCore in Python

```python
from memcore.manager import MemCore
from memcore.models import MemoryType

# 1. Initialize MemCore
mc = MemCore(db_path="memcore.db", repo_root=".")

# 2. Add a critical security rule (Guaranteed zero loss)
mc.add_memory(
    content="Always validate OAuth2 PKCE code_verifier before issuing tokens.",
    memory_type=MemoryType.SECURITY_CONSTRAINT,
    importance=0.95,
    is_protected=True,
    protection_reason="Security baseline"
)

# 3. Hybrid Search (~18.4 ms)
results = mc.search_memories("How is OAuth implemented?", top_k=5)
for r in results:
    print(f"[{r.relevance_score:.2f}] {r.memory.content}")

# 4. Pack optimal context within a 500-token budget
context = mc.build_context(
    task_query="Fix login token refresh issue",
    token_budget=500
)
print(f"Used {context.used_tokens} / {context.token_budget} tokens")
print(context.formatted_prompt)
```

---

## 📊 Measured Benchmark Highlights

- **Retrieval Latency**: `~18.4 ms` (P50 hybrid recall over 1,000+ observations).
- **GC Decision & Execution**: `~50.9 ms` across 320 records.
- **Context Assembly Speed**: `~42.0 ms`.
- **Token Reduction**: **Up to 92%** fewer tokens injected into LLM prompts compared to raw dumps.
- **Critical Memory Loss Rate**: **0.00%** (Protected memories guaranteed safe).
- **LongMemEval-S Recall@5**: **95.2%** gold context found in top 5 results.

---

## 🛡️ Architecture & Security

```
[Agent Prompts & Tool Events]
           │
           ▼
┌─────────────────────────┐
│ 1. Ingestion & Redact   │ ──► Strips API keys, passwords, and sanitizes untrusted inputs
└──────────┬──────────────┘
           ▼
┌─────────────────────────┐
│ 2. Hybrid SQLite Store  │ ──► FTS5 BM25 Lexical + 384d Vector Embeddings + Recency Decay
└──────────┬──────────────┘
           ▼
┌─────────────────────────┐
│ 3. AST Code Grounding   │ ──► Validates files, classes, and function signatures against disk
└──────────┬──────────────┘
           ▼
┌─────────────────────────┐
│ 4. MemGC Risk Engine    │ ──► Evaluates Utility (U) & Risk (R) across 8 lifecycle actions
└──────────┬──────────────┘
           ▼
┌─────────────────────────┐
│ 5. Knapsack Packing     │ ──► Delivers optimal context within prompt budget (e.g., 1,500 tokens)
└─────────────────────────┘
```

- **Secret Redaction**: Detects and redacts AWS keys, OpenAI tokens, GitHub tokens, Bearer headers, and DB connection strings before saving to disk.
- **Air-Gapped & Local**: Binds exclusively to `127.0.0.1`. No telemetry, no external accounts, no cloud dependencies.

---

## 📜 License

Distributed under the **Apache-2.0** License. Open source and free for commercial and private use.
