"""FastAPI application providing REST endpoints and serving the modern Developer Dashboard."""

import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from memcore.manager import MemCore
from memcore.models import MemoryType, RelationshipType

app = FastAPI(title="MemCore API & Dashboard", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_memcore: Optional[MemCore] = None


def get_mc() -> MemCore:
    global _memcore
    if _memcore is None:
        db_path = os.environ.get("MEMCORE_DB_PATH", "memcore.db")
        repo_root = os.environ.get("MEMCORE_REPO_ROOT", os.getcwd())
        _memcore = MemCore(db_path=db_path, repo_root=repo_root)
    return _memcore


class AddMemoryRequest(BaseModel):
    content: str
    memory_type: str = "general"
    project_id: str = "default"
    importance: float = 0.5
    associated_files: List[str] = []
    associated_symbols: List[str] = []
    is_protected: bool = False
    protection_reason: Optional[str] = None


class ContextRequest(BaseModel):
    task_query: str
    token_budget: int = 2000
    project_id: str = "default"


class GCExecuteRequest(BaseModel):
    project_id: str = "default"
    allow_delete: bool = False
    approved_memory_ids: List[str] = []


@app.get("/api/stats")
def get_stats(project_id: str = "default"):
    return get_mc().get_stats(project_id=project_id)


@app.get("/api/memories")
def list_memories(project_id: str = "default", status: Optional[str] = "active"):
    mc = get_mc()
    # status None if "all"
    stat_enum = None if status == "all" else (status or "active")
    mems = mc.store.list_memories(project_id=project_id, status=stat_enum, limit=200)
    return [m.model_dump() for m in mems]


@app.post("/api/memories")
def add_memory(req: AddMemoryRequest):
    mc = get_mc()
    try:
        mtype = MemoryType(req.memory_type)
    except ValueError:
        mtype = MemoryType.GENERAL

    rec = mc.add_memory(
        content=req.content,
        memory_type=mtype,
        project_id=req.project_id,
        importance=req.importance,
        associated_files=req.associated_files,
        associated_symbols=req.associated_symbols,
        is_protected=req.is_protected,
        protection_reason=req.protection_reason,
    )
    return rec.model_dump()


@app.post("/api/retrieve")
def search_memories(query: str, project_id: str = "default", top_k: int = 10):
    mc = get_mc()
    results = mc.search_memories(query=query, project_id=project_id, top_k=top_k)
    return [
        {
            "id": r.memory.id,
            "content": r.memory.content,
            "type": r.memory.memory_type.value,
            "relevance_score": round(r.relevance_score, 3),
            "reasons": r.retrieval_reasons,
            "token_count": r.memory.token_count,
            "is_protected": r.memory.is_protected,
            "status": r.memory.status.value,
        }
        for r in results
    ]


@app.post("/api/context")
def build_context(req: ContextRequest):
    mc = get_mc()
    return mc.build_context(
        task_query=req.task_query,
        token_budget=req.token_budget,
        project_id=req.project_id,
    ).model_dump()


@app.get("/api/gc/preview")
def gc_preview(project_id: str = "default"):
    mc = get_mc()
    recs = mc.preview_gc(project_id=project_id)
    return [r.model_dump() for r in recs]


@app.post("/api/gc/execute")
def gc_execute(req: GCExecuteRequest):
    mc = get_mc()
    return mc.execute_gc(
        project_id=req.project_id,
        allow_delete=req.allow_delete,
        approved_memory_ids=req.approved_memory_ids,
    )


@app.post("/api/verify/all")
def verify_all(project_id: str = "default"):
    mc = get_mc()
    res = mc.verify_all(project_id=project_id)
    return [r.model_dump() for r in res]


@app.get("/api/history")
def get_history(memory_id: Optional[str] = None, limit: int = 50):
    mc = get_mc()
    logs = mc.get_history(memory_id=memory_id, limit=limit)
    return [l.model_dump() for l in logs]


@app.get("/", response_class=HTMLResponse)
def dashboard_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MemCore — AI Memory Infrastructure</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #0a0d14;
      --card-bg: rgba(18, 24, 38, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --primary: #6366f1;
      --primary-glow: rgba(99, 102, 241, 0.25);
      --accent: #06b6d4;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: radial-gradient(circle at top right, #131b2e, var(--bg-dark));
      color: var(--text);
      font-family: 'Outfit', -apple-system, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      padding: 18px 36px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--card-border);
      background: rgba(10, 13, 20, 0.8);
      backdrop-filter: blur(12px);
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .logo-container { display: flex; align-items: center; gap: 12px; }
    .logo-badge {
      background: linear-gradient(135deg, var(--primary), var(--accent));
      width: 36px;
      height: 36px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      box-shadow: 0 0 20px var(--primary-glow);
    }
    .tagline { color: var(--text-muted); font-size: 0.85rem; }
    main { padding: 32px 36px; max-width: 1400px; margin: 0 auto; width: 100%; display: flex; flex-direction: column; gap: 28px; }
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; }
    .stat-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 22px;
      backdrop-filter: blur(16px);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
      transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .stat-card:hover { transform: translateY(-2px); border-color: rgba(99, 102, 241, 0.4); }
    .stat-title { font-size: 0.85rem; color: var(--text-muted); font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
    .stat-value { font-size: 2rem; font-weight: 700; margin-top: 8px; color: #fff; font-family: 'JetBrains Mono', monospace; }
    .tabs { display: flex; gap: 12px; border-bottom: 1px solid var(--card-border); padding-bottom: 12px; }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.95rem;
      font-weight: 600;
      padding: 8px 18px;
      cursor: pointer;
      border-radius: 8px;
      transition: all 0.2s;
    }
    .tab-btn.active, .tab-btn:hover { background: rgba(255, 255, 255, 0.07); color: #fff; }
    .tab-btn.active { color: var(--accent); background: rgba(6, 182, 212, 0.1); }
    .panel { display: none; }
    .panel.active { display: flex; flex-direction: column; gap: 20px; }
    .glass-box {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 24px;
      backdrop-filter: blur(16px);
    }
    .btn {
      background: linear-gradient(135deg, var(--primary), #4f46e5);
      color: white;
      border: none;
      padding: 10px 20px;
      font-weight: 600;
      border-radius: 8px;
      cursor: pointer;
      transition: opacity 0.2s, box-shadow 0.2s;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .btn:hover { opacity: 0.95; box-shadow: 0 0 16px var(--primary-glow); }
    .btn-secondary { background: rgba(255, 255, 255, 0.08); }
    .btn-secondary:hover { background: rgba(255, 255, 255, 0.12); box-shadow: none; }
    .btn-danger { background: linear-gradient(135deg, var(--danger), #b91c1c); }
    .input-row { display: flex; gap: 12px; margin-bottom: 16px; }
    input, select, textarea {
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 10px 14px;
      color: white;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s;
    }
    input:focus, select:focus, textarea:focus { border-color: var(--primary); }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 0.9rem; }
    th { text-align: left; padding: 12px 14px; color: var(--text-muted); border-bottom: 1px solid var(--card-border); }
    td { padding: 14px; border-bottom: 1px solid rgba(255, 255, 255, 0.04); vertical-align: top; }
    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
    }
    .badge-protected { background: rgba(245, 158, 11, 0.15); color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-active { background: rgba(16, 185, 129, 0.15); color: var(--success); }
    .badge-verified { background: rgba(6, 182, 212, 0.15); color: var(--accent); }
    .badge-conflict { background: rgba(239, 68, 68, 0.15); color: var(--danger); }
    code { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px; }
  </style>
</head>
<body>
  <header>
    <div class="logo-container">
      <div class="logo-badge">MC</div>
      <div>
        <h2 style="font-size: 1.25rem; font-weight: 700;">MemCore</h2>
        <p class="tagline">Intelligent Memory Infrastructure for AI Coding Agents</p>
      </div>
    </div>
    <div>
      <button class="btn btn-secondary" onclick="refreshAll()">🔄 Refresh</button>
    </div>
  </header>

  <main>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-title">Total Memories</div>
        <div class="stat-value" id="stat-total">-</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Active Context Tokens</div>
        <div class="stat-value" id="stat-tokens">-</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Protected Rules</div>
        <div class="stat-value" id="stat-protected" style="color: var(--warning);">-</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Repo Conflicts</div>
        <div class="stat-value" id="stat-conflicts" style="color: var(--danger);">-</div>
      </div>
    </div>

    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('memories-tab')">Memories</button>
      <button class="tab-btn" onclick="switchTab('retrieval-tab')">Retrieval & Context</button>
      <button class="tab-btn" onclick="switchTab('gc-tab')">Garbage Collection</button>
      <button class="tab-btn" onclick="switchTab('verify-tab')">Repo Verification</button>
      <button class="tab-btn" onclick="switchTab('history-tab')">Audit History</button>
    </div>

    <!-- MEMORIES TAB -->
    <div id="memories-tab" class="panel active">
      <div class="glass-box">
        <h3 style="margin-bottom: 16px;">Add New Knowledge Memory</h3>
        <div class="input-row">
          <input type="text" id="new-content" placeholder="E.g., PostgreSQL connection pool max_size is set to 20" style="flex: 3;">
          <select id="new-type" style="flex: 1;">
            <option value="general">General</option>
            <option value="architecture">Architecture</option>
            <option value="security_constraint">Security Constraint</option>
            <option value="db_schema">DB Schema</option>
            <option value="api_contract">API Contract</option>
            <option value="bug_fix">Bug Fix</option>
          </select>
          <input type="number" id="new-importance" placeholder="Importance (0-1)" step="0.1" value="0.7" style="width: 120px;">
          <button class="btn" onclick="submitMemory()">+ Add Memory</button>
        </div>
      </div>

      <div class="glass-box">
        <h3>Stored Memories</h3>
        <table id="memories-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Content</th>
              <th>Type</th>
              <th>Tokens</th>
              <th>Verification</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Loading memories...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- RETRIEVAL TAB -->
    <div id="retrieval-tab" class="panel">
      <div class="glass-box">
        <h3 style="margin-bottom: 16px;">Task-Aware Context Optimization</h3>
        <div class="input-row">
          <input type="text" id="task-query" placeholder="Enter coding task (e.g. Fix PostgreSQL connection pool exhaustion)" style="flex: 3;">
          <input type="number" id="token-budget" placeholder="Token Budget" value="1000" style="width: 140px;">
          <button class="btn" onclick="testContextOptimization()">Optimize Context</button>
        </div>
        <div id="context-output" style="margin-top: 18px; display: none;"></div>
      </div>
    </div>

    <!-- GC TAB -->
    <div id="gc-tab" class="panel">
      <div class="glass-box">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <div>
            <h3>MemGC Risk-Aware Garbage Collection</h3>
            <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 4px;">Evaluates utility vs deletion hazard. Protected memories are never deleted.</p>
          </div>
          <div>
            <button class="btn btn-secondary" onclick="loadGCPreview()">Preview GC</button>
            <button class="btn btn-danger" onclick="executeGC()">Execute GC</button>
          </div>
        </div>
        <table id="gc-table">
          <thead>
            <tr>
              <th>Memory ID</th>
              <th>Action</th>
              <th>Utility Score</th>
              <th>Risk Score</th>
              <th>Reasoning</th>
              <th>Requires Approval</th>
            </tr>
          </thead>
          <tbody>
            <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Click "Preview GC" to run analysis</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- VERIFY TAB -->
    <div id="verify-tab" class="panel">
      <div class="glass-box">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <div>
            <h3>Code-Grounded Verification</h3>
            <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 4px;">Inspects active source tree for symbol existence and stale references.</p>
          </div>
          <button class="btn" onclick="runVerification()">Verify All Active</button>
        </div>
        <table id="verify-table">
          <thead>
            <tr>
              <th>Memory ID</th>
              <th>Status</th>
              <th>Confidence</th>
              <th>Evidence Found</th>
              <th>Conflicts Detected</th>
            </tr>
          </thead>
          <tbody>
            <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Click "Verify All Active" to scan codebase</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- HISTORY TAB -->
    <div id="history-tab" class="panel">
      <div class="glass-box">
        <h3 style="margin-bottom: 16px;">Audit Log & Provenance History</h3>
        <table id="history-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Memory ID</th>
              <th>Action</th>
              <th>Actor</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Loading audit history...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </main>

  <script>
    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
      event.target.classList.add('active');
      document.getElementById(tabId).classList.add('active');
      if (tabId === 'history-tab') loadHistory();
      if (tabId === 'gc-tab') loadGCPreview();
    }

    async function refreshAll() {
      await loadStats();
      await loadMemories();
    }

    async function loadStats() {
      try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        document.getElementById('stat-total').innerText = data.total_memories || 0;
        document.getElementById('stat-tokens').innerText = data.active_tokens || 0;
        document.getElementById('stat-protected').innerText = data.protected_count || 0;
        document.getElementById('stat-conflicts').innerText = data.conflicts_count || 0;
      } catch (err) {
        console.error(err);
      }
    }

    async function loadMemories() {
      try {
        const res = await fetch('/api/memories?status=all');
        const data = await res.json();
        const tbody = document.querySelector('#memories-table tbody');
        if (!data.length) {
          tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No memories recorded yet.</td></tr>';
          return;
        }
        tbody.innerHTML = data.map(m => `
          <tr>
            <td><code>${m.id.substring(0, 8)}</code></td>
            <td>${m.content}</td>
            <td><span class="badge ${m.is_protected ? 'badge-protected' : 'badge-active'}">${m.memory_type}</span></td>
            <td><code>${m.token_count}</code></td>
            <td><span class="badge ${m.verification_status === 'verified' ? 'badge-verified' : (m.verification_status === 'conflict' ? 'badge-conflict' : '')}">${m.verification_status}</span></td>
            <td>${m.status}</td>
          </tr>
        `).join('');
      } catch (err) {
        console.error(err);
      }
    }

    async function submitMemory() {
      const content = document.getElementById('new-content').value.trim();
      const type = document.getElementById('new-type').value;
      const importance = parseFloat(document.getElementById('new-importance').value) || 0.5;
      if (!content) return;
      await fetch('/api/memories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, memory_type: type, importance })
      });
      document.getElementById('new-content').value = '';
      await refreshAll();
    }

    async function testContextOptimization() {
      const query = document.getElementById('task-query').value.trim();
      const budget = parseInt(document.getElementById('token-budget').value) || 1000;
      if (!query) return;
      const res = await fetch('/api/context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_query: query, token_budget: budget })
      });
      const data = await res.json();
      const out = document.getElementById('context-output');
      out.style.display = 'block';
      out.innerHTML = `
        <div style="background: rgba(0,0,0,0.4); border: 1px solid var(--card-border); padding: 16px; border-radius: 8px;">
          <h4>Context Optimization Results</h4>
          <p style="margin: 8px 0; color: var(--accent);">Tokens Used: <b>${data.used_tokens}</b> / ${data.token_budget} (${data.budget_utilization_pct}% budget utilization)</p>
          <p style="color: var(--text-muted); font-size: 0.85rem;">Selected Memories (${data.selected_memories.length}):</p>
          <ul style="margin: 10px 0 10px 20px; font-size: 0.9rem;">
            ${data.selected_memories.map(m => `<li><b>[${m.memory.memory_type}]</b> ${m.memory.content} (cost: ${m.memory.token_count} tokens)</li>`).join('')}
          </ul>
          ${data.excluded_memories.length ? `<p style="color: var(--warning); font-size: 0.85rem;">Excluded due to budget: ${data.excluded_memories.length} memories</p>` : ''}
        </div>
      `;
    }

    async function loadGCPreview() {
      const res = await fetch('/api/gc/preview');
      const data = await res.json();
      const tbody = document.querySelector('#gc-table tbody');
      if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No recommendations at this time.</td></tr>';
        return;
      }
      tbody.innerHTML = data.map(r => `
        <tr>
          <td><code>${r.memory_id.substring(0, 8)}</code></td>
          <td><span class="badge ${r.action === 'DELETE' ? 'badge-conflict' : (r.action === 'PROTECT' ? 'badge-protected' : 'badge-active')}">${r.action}</span></td>
          <td><code>${r.utility.toFixed(2)}</code></td>
          <td><code>${r.risk.toFixed(2)}</code></td>
          <td>${r.reason}</td>
          <td>${r.requires_approval ? '<span style="color: var(--danger)">Yes (Requires Approval)</span>' : '<span style="color: var(--success)">Auto-Eligible</span>'}</td>
        </tr>
      `).join('');
    }

    async function executeGC() {
      if (!confirm('Execute garbage collection for eligible safe memories?')) return;
      const res = await fetch('/api/gc/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ allow_delete: false })
      });
      const data = await res.json();
      alert(`GC Executed! Summary: ` + JSON.stringify(data.summary));
      await refreshAll();
      await loadGCPreview();
    }

    async function runVerification() {
      const res = await fetch('/api/verify/all', { method: 'POST' });
      const data = await res.json();
      const tbody = document.querySelector('#verify-table tbody');
      tbody.innerHTML = data.map(v => `
        <tr>
          <td><code>${v.memory_id.substring(0, 8)}</code></td>
          <td><span class="badge ${v.status === 'verified' ? 'badge-verified' : (v.status === 'conflict' ? 'badge-conflict' : '')}">${v.status}</span></td>
          <td><code>${(v.confidence * 100).toFixed(0)}%</code></td>
          <td>${v.evidence.length ? v.evidence.join('; ') : 'None'}</td>
          <td style="color: var(--danger);">${v.conflicts.length ? v.conflicts.join('; ') : 'None'}</td>
        </tr>
      `).join('');
      await refreshAll();
    }

    async function loadHistory() {
      const res = await fetch('/api/history');
      const data = await res.json();
      const tbody = document.querySelector('#history-table tbody');
      if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No audit events recorded.</td></tr>';
        return;
      }
      tbody.innerHTML = data.map(h => `
        <tr>
          <td style="white-space: nowrap; font-size: 0.8rem; color: var(--text-muted);">${new Date(h.timestamp * 1000).toLocaleTimeString()}</td>
          <td><code>${h.memory_id.substring(0, 8)}</code></td>
          <td><span class="badge badge-active">${h.action}</span></td>
          <td>${h.actor}</td>
          <td>${h.reason || '-'}</td>
        </tr>
      `).join('');
    }

    // Auto-init
    refreshAll();
  </script>
</body>
</html>
"""
