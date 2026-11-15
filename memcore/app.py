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
            "score": round(r.relevance_score, 3),
            "reasons": r.retrieval_reasons,
            "status": r.memory.status.value,
            "verification_status": r.memory.verification_status.value,
            "token_count": r.memory.token_count,
            "is_protected": r.memory.is_protected,
        }
        for r in results
    ]


@app.post("/api/context")
def build_context(req: ContextRequest):
    mc = get_mc()
    res = mc.build_context(
        task_query=req.task_query,
        token_budget=req.token_budget,
        project_id=req.project_id,
    )
    return res.model_dump()


@app.get("/api/gc/preview")
def preview_gc(project_id: str = "default"):
    mc = get_mc()
    recs = mc.preview_gc(project_id=project_id)
    return [r.model_dump() for r in recs]


@app.post("/api/gc/execute")
def execute_gc(req: GCExecuteRequest):
    mc = get_mc()
    res = mc.execute_gc(
        project_id=req.project_id,
        allow_delete=req.allow_delete,
        approved_memory_ids=req.approved_memory_ids,
    )
    return res


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
  <title>MemCore Dashboard</title>
  <style>
    :root {
      --bg: #141417;
      --card-bg: #1e1e24;
      --card-border: #2e2e38;
      --border-subtle: #25252e;
      --badge-bg: #282833;
      --badge-border: #383846;
      --text: #efeff4;
      --text-muted: #8e8e9c;
      --text-title: #d4d4dc;
      --dot-green: #4ade80;
      --accent-purple: #a78bfa;
      --accent-cyan: #38bdf8;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font-family);
      font-size: 13px;
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    header {
      padding: 14px 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-subtle);
      background-color: #1a1a20;
      position: sticky;
      top: 0;
      z-index: 50;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--dot-green);
    }

    .brand-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-title);
      letter-spacing: 0.2px;
    }

    .brand-tag {
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-muted);
      background: var(--badge-bg);
      border: 1px solid var(--badge-border);
      padding: 2px 8px;
      border-radius: 12px;
    }

    main {
      padding: 24px 28px;
      max-width: 1400px;
      margin: 0 auto;
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    /* Antigravity Metrics Cards */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 14px;
    }

    .metric-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .metric-label {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      font-weight: 500;
    }

    .metric-value {
      font-size: 24px;
      font-weight: 600;
      color: var(--text);
      font-family: var(--font-mono);
    }

    .metric-sub {
      font-size: 11px;
      color: var(--text-muted);
    }

    /* Neural Memory Matrix & Interactive Graph Container */
    .graph-container {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .graph-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .graph-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-title);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .canvas-wrap {
      position: relative;
      width: 100%;
      height: 240px;
      background: #18181e;
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      overflow: hidden;
    }

    canvas {
      display: block;
      width: 100%;
      height: 100%;
      cursor: crosshair;
    }

    .canvas-hud {
      position: absolute;
      top: 10px;
      left: 12px;
      font-size: 10px;
      font-family: var(--font-mono);
      color: var(--text-muted);
      pointer-events: none;
      display: flex;
      gap: 14px;
    }

    .canvas-hud span {
      color: var(--text);
      font-weight: 600;
    }

    /* Tabs Navigation */
    .tabs {
      display: flex;
      gap: 8px;
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 10px;
    }

    .tab-btn {
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 500;
      padding: 6px 14px;
      cursor: pointer;
      border-radius: 6px;
      transition: all 0.15s;
    }

    .tab-btn:hover {
      background: rgba(255, 255, 255, 0.04);
      color: var(--text);
    }

    .tab-btn.active {
      color: var(--text);
      background: var(--card-bg);
      border-color: var(--card-border);
    }

    .panel { display: none; }
    .panel.active { display: flex; flex-direction: column; gap: 14px; }

    .box {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 18px;
    }

    .box-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-title);
      margin-bottom: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .input-row {
      display: flex;
      gap: 10px;
      margin-bottom: 14px;
    }

    input, select, textarea {
      background: #17171d;
      border: 1px solid var(--card-border);
      border-radius: 6px;
      padding: 8px 12px;
      color: var(--text);
      font-family: inherit;
      font-size: 12px;
      outline: none;
    }

    input:focus, select:focus, textarea:focus {
      border-color: #4a4a58;
    }

    .btn {
      background: #2a2a35;
      color: var(--text);
      border: 1px solid var(--card-border);
      padding: 8px 16px;
      font-size: 12px;
      font-weight: 500;
      border-radius: 6px;
      cursor: pointer;
      transition: background 0.15s;
    }

    .btn:hover { background: #353544; }
    .btn-primary { background: #2f2f3e; border-color: #444456; color: #fff; }
    .btn-primary:hover { background: #3c3c4f; }
    .btn-danger { background: #3b2225; border-color: #5c292f; color: #fca5a5; }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      margin-top: 8px;
    }

    th {
      text-align: left;
      padding: 10px 12px;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-subtle);
      font-weight: 500;
      font-size: 11px;
      text-transform: uppercase;
    }

    td {
      padding: 10px 12px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.03);
      vertical-align: top;
    }

    .badge {
      display: inline-block;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 10px;
      font-family: var(--font-mono);
      font-weight: 500;
      text-transform: uppercase;
      background: var(--badge-bg);
      border: 1px solid var(--badge-border);
      color: var(--text-muted);
    }

    .badge-protected {
      color: #c084fc;
      border-color: rgba(192, 132, 252, 0.3);
      background: rgba(192, 132, 252, 0.08);
    }

    .badge-active {
      color: #4ade80;
      border-color: rgba(74, 222, 128, 0.3);
      background: rgba(74, 222, 128, 0.08);
    }

    code {
      font-family: var(--font-mono);
      font-size: 11px;
      background: rgba(255, 255, 255, 0.04);
      padding: 1px 4px;
      border-radius: 4px;
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="status-dot"></div>
      <span class="brand-title">MemCore Persistent Memory Engine</span>
      <span class="brand-tag">v0.1.0</span>
    </div>
    <div style="font-size: 11px; font-family: var(--font-mono); color: var(--text-muted);" id="header-tokens">
      Active Prompt: 0 tokens
    </div>
  </header>

  <main>
    <!-- Top Antigravity Metric Cards -->
    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-label">Active Tokens</div>
        <div class="metric-value" id="stat-tokens">0</div>
        <div class="metric-sub">Budgeted context prompt</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Total Memories</div>
        <div class="metric-value" id="stat-total">0</div>
        <div class="metric-sub">Stored in local graph</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Protected Invariants</div>
        <div class="metric-value" id="stat-protected" style="color: var(--accent-purple);">0</div>
        <div class="metric-sub">0.00% loss guarantee</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">AST Verification</div>
        <div class="metric-value" id="stat-conflicts">0</div>
        <div class="metric-sub">Detected conflicts</div>
      </div>
    </div>

    <!-- Live Neural Memory Matrix Canvas -->
    <div class="graph-container">
      <div class="graph-header">
        <div class="graph-title">
          <span>Neural Memory Constellation</span>
          <span style="font-size: 11px; font-family: var(--font-mono); font-weight: normal; color: var(--text-muted);" id="graph-node-count">0 nodes</span>
        </div>
        <div style="font-size: 11px; color: var(--text-muted);" id="node-inspector">
          Hover over nodes to inspect verified memory payload
        </div>
      </div>

      <div class="canvas-wrap">
        <canvas id="neuralCanvas"></canvas>
        <div class="canvas-hud">
          <div>TOPOLOGY: <span>HYBRID GRAPH</span></div>
          <div>MEMGC STATUS: <span>OPTIMIZED</span></div>
          <div>ZERO-LOSS INVARIANT: <span style="color: var(--accent-purple);">ENFORCED</span></div>
        </div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('memories-tab')">Memories</button>
      <button class="tab-btn" onclick="switchTab('retrieval-tab')">Context Optimizer</button>
      <button class="tab-btn" onclick="switchTab('gc-tab')">Risk-Aware GC</button>
      <button class="tab-btn" onclick="switchTab('verify-tab')">Code Verification</button>
      <button class="tab-btn" onclick="switchTab('history-tab')">Audit Provenance</button>
    </div>

    <!-- MEMORIES TAB -->
    <div id="memories-tab" class="panel active">
      <div class="box">
        <div class="box-title">Ingest Verified Memory</div>
        <div class="input-row">
          <input type="text" id="new-content" placeholder="E.g., SQLite configured with WAL mode and QueuePool max_size=10" style="flex: 4;">
          <select id="new-type" style="flex: 1.5;">
            <option value="general">General</option>
            <option value="architecture">Architecture</option>
            <option value="security_constraint">Security Constraint</option>
            <option value="api_contract">API Contract</option>
            <option value="bug_fix">Bug Fix</option>
          </select>
          <input type="number" id="new-importance" placeholder="Imp (0-1)" step="0.1" value="0.7" style="width: 100px;">
          <button class="btn btn-primary" onclick="submitMemory()">+ Add Memory</button>
        </div>
      </div>

      <div class="box">
        <div class="box-title">Active Knowledge Records</div>
        <table id="memories-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Content</th>
              <th>Type</th>
              <th>Tokens</th>
              <th>Verification</th>
              <th>Protection</th>
            </tr>
          </thead>
          <tbody>
            <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Loading memories...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- CONTEXT OPTIMIZER TAB -->
    <div id="retrieval-tab" class="panel">
      <div class="box">
        <div class="box-title">Task-Aware Context Budgeting</div>
        <div class="input-row">
          <input type="text" id="task-query" placeholder="Enter coding prompt (e.g. Implement JWT authentication token endpoint)" style="flex: 3;">
          <input type="number" id="token-budget" placeholder="Token Budget" value="1000" style="width: 120px;">
          <button class="btn btn-primary" onclick="testContextOptimization()">Optimize Context</button>
        </div>
        <div id="context-output" style="margin-top: 14px; display: none;"></div>
      </div>
    </div>

    <!-- GC TAB -->
    <div id="gc-tab" class="panel">
      <div class="box">
        <div class="box-title">
          <span>MemGC Risk-Aware Garbage Collection</span>
          <div>
            <button class="btn" onclick="loadGCPreview()">Preview GC</button>
            <button class="btn btn-danger" onclick="executeGC()">Execute GC</button>
          </div>
        </div>
        <table id="gc-table">
          <thead>
            <tr>
              <th>Memory ID</th>
              <th>Action</th>
              <th>Utility</th>
              <th>Risk Score</th>
              <th>Reasoning</th>
              <th>Safety Status</th>
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
      <div class="box">
        <div class="box-title">
          <span>Code-Grounded Verification</span>
          <button class="btn" onclick="runVerification()">Scan Codebase</button>
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
            <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Click "Scan Codebase" to verify AST references</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- HISTORY TAB -->
    <div id="history-tab" class="panel">
      <div class="box">
        <div class="box-title">Audit History & Provenance</div>
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
    // Tab switching
    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
      event.target.classList.add('active');
      document.getElementById(tabId).classList.add('active');
      if (tabId === 'history-tab') loadHistory();
      if (tabId === 'gc-tab') loadGCPreview();
    }

    // Graph Canvas Animation & Physics
    const canvas = document.getElementById('neuralCanvas');
    const ctx = canvas.getContext('2d');
    let width, height;
    let graphNodes = [];
    let mouse = { x: -100, y: -100 };

    function resizeCanvas() {
      const rect = canvas.getBoundingClientRect();
      width = canvas.width = rect.width * window.devicePixelRatio;
      height = canvas.height = rect.height * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    canvas.addEventListener('mousemove', (e) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;

      const w = canvas.getBoundingClientRect().width;
      const h = canvas.getBoundingClientRect().height;

      let hovered = null;
      graphNodes.forEach(n => {
        const nx = n.x * w;
        const ny = n.y * h;
        if (Math.hypot(mouse.x - nx, mouse.y - ny) < 14) {
          hovered = n;
        }
      });

      const inspector = document.getElementById('node-inspector');
      if (hovered) {
        inspector.innerHTML = `[${hovered.type}] <b>${hovered.content}</b> (${hovered.tokens} tokens)`;
      } else {
        inspector.textContent = 'Hover over nodes to inspect verified memory payload';
      }
    });

    function drawGraph() {
      const w = canvas.getBoundingClientRect().width;
      const h = canvas.getBoundingClientRect().height;
      ctx.clearRect(0, 0, w, h);

      // Edges
      ctx.lineWidth = 0.75;
      for (let i = 0; i < graphNodes.length; i++) {
        for (let j = i + 1; j < graphNodes.length; j++) {
          const a = graphNodes[i];
          const b = graphNodes[j];
          const ax = a.x * w;
          const ay = a.y * h;
          const bx = b.x * w;
          const by = b.y * h;
          const dist = Math.hypot(ax - bx, ay - by);

          if (dist < 120) {
            const alpha = (1 - dist / 120) * 0.18;
            ctx.strokeStyle = `rgba(142, 142, 156, ${alpha})`;
            ctx.beginPath();
            ctx.moveTo(ax, ay);
            ctx.lineTo(bx, by);
            ctx.stroke();
          }
        }
      }

      // Nodes
      graphNodes.forEach(n => {
        n.x += n.vx * 0.001;
        n.y += n.vy * 0.001;
        if (n.x < 0.08 || n.x > 0.92) n.vx *= -1;
        if (n.y < 0.12 || n.y > 0.88) n.vy *= -1;

        const nx = n.x * w;
        const ny = n.y * h;
        const isHovered = Math.hypot(mouse.x - nx, mouse.y - ny) < 14;

        if (n.is_protected) {
          ctx.beginPath();
          ctx.arc(nx, ny, isHovered ? 11 : 8, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(167, 139, 250, 0.2)';
          ctx.fill();
        }

        ctx.beginPath();
        ctx.arc(nx, ny, isHovered ? 6 : (n.is_protected ? 4.5 : 3.5), 0, Math.PI * 2);
        ctx.fillStyle = n.is_protected ? '#c084fc' : (isHovered ? '#38bdf8' : '#8e8e9c');
        ctx.fill();
        ctx.strokeStyle = '#1e1e24';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      });

      requestAnimationFrame(drawGraph);
    }
    drawGraph();

    // Stats & Memories API
    async function refreshAll() {
      await loadStats();
      await loadMemories();
    }

    async function loadStats() {
      try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        document.getElementById('stat-total').innerText = data.total_memories || 0;
        document.getElementById('stat-tokens').innerText = (data.active_tokens || 0).toLocaleString();
        document.getElementById('stat-protected').innerText = data.protected_count || 0;
        document.getElementById('stat-conflicts').innerText = data.conflicts_count || 0;
        document.getElementById('header-tokens').innerText = `Active Prompt: ${(data.active_tokens || 0).toLocaleString()} tokens`;
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
          tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No memories stored yet.</td></tr>';
          graphNodes = [];
          document.getElementById('graph-node-count').textContent = '0 nodes';
          return;
        }

        // Update Graph Nodes
        document.getElementById('graph-node-count').textContent = `${data.length} nodes`;
        graphNodes = data.map((m, idx) => ({
          id: m.id,
          content: m.content,
          type: m.memory_type,
          tokens: m.token_count,
          is_protected: m.is_protected,
          x: 0.15 + (Math.sin(idx + 1) * 0.35 + 0.35),
          y: 0.20 + (Math.cos(idx + 1) * 0.30 + 0.30),
          vx: (Math.sin(idx) > 0 ? 0.15 : -0.15),
          vy: (Math.cos(idx) > 0 ? 0.15 : -0.15)
        }));

        tbody.innerHTML = data.map(m => `
          <tr>
            <td><code>${m.id.substring(0, 8)}</code></td>
            <td style="max-width: 480px; word-break: break-word;">${escapeHtml(m.content)}</td>
            <td><span class="badge">${m.memory_type}</span></td>
            <td><code>${m.token_count}</code></td>
            <td><span class="badge badge-active">${m.verification_status}</span></td>
            <td>${m.is_protected ? '<span class="badge badge-protected">Protected</span>' : '<span style="color: var(--text-muted); font-size: 11px;">Standard</span>'}</td>
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
        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--card-border); padding: 14px; border-radius: 6px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span style="font-weight: 600;">Optimized Prompt Context</span>
            <span style="color: var(--dot-green); font-family: var(--font-mono);">${data.used_tokens} / ${data.token_budget} tokens (${data.budget_utilization_pct}%)</span>
          </div>
          <ul style="margin: 8px 0 8px 18px; font-size: 12px; color: var(--text);">
            ${data.selected_memories.map(m => `<li><b>[${m.memory.memory_type}]</b> ${escapeHtml(m.memory.content)} <span style="color: var(--text-muted);">(${m.memory.token_count}t)</span></li>`).join('')}
          </ul>
        </div>
      `;
    }

    async function loadGCPreview() {
      const res = await fetch('/api/gc/preview');
      const data = await res.json();
      const tbody = document.querySelector('#gc-table tbody');
      if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No GC recommendations at this time.</td></tr>';
        return;
      }
      tbody.innerHTML = data.map(r => `
        <tr>
          <td><code>${r.memory_id.substring(0, 8)}</code></td>
          <td><span class="badge">${r.action}</span></td>
          <td><code>${r.utility.toFixed(2)}</code></td>
          <td><code>${r.risk.toFixed(2)}</code></td>
          <td>${escapeHtml(r.reason)}</td>
          <td>${r.requires_approval ? '<span style="color: #fca5a5">Requires Approval</span>' : '<span style="color: #4ade80">Auto-Eligible</span>'}</td>
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
          <td><span class="badge badge-active">${v.status}</span></td>
          <td><code>${(v.confidence * 100).toFixed(0)}%</code></td>
          <td>${v.evidence.length ? escapeHtml(v.evidence.join('; ')) : 'None'}</td>
          <td style="color: #fca5a5;">${v.conflicts.length ? escapeHtml(v.conflicts.join('; ')) : 'None'}</td>
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
          <td style="white-space: nowrap; font-size: 11px; color: var(--text-muted);">${new Date(h.timestamp * 1000).toLocaleTimeString()}</td>
          <td><code>${h.memory_id.substring(0, 8)}</code></td>
          <td><span class="badge">${h.action}</span></td>
          <td>${h.actor}</td>
          <td>${escapeHtml(h.reason || '-')}</td>
        </tr>
      `).join('');
    }

    function escapeHtml(text) {
      if (!text) return '';
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    // Auto-init
    refreshAll();
    setInterval(refreshAll, 3000);
  </script>
</body>
</html>
"""
