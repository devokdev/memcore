// Rotating Agent Slot (Claude Code -> Cursor -> Codex -> Antigravity -> OpenClaw -> Hermes)
function initAgentCycling() {
  const agents = document.querySelectorAll('.slot-agents .slot-agent-item');
  if (agents.length > 0) {
    let agentIdx = 0;
    setInterval(() => {
      agents[agentIdx].classList.remove('active');
      agents[agentIdx].classList.add('prev');
      setTimeout(() => {
        document.querySelectorAll('.slot-agents .slot-agent-item.prev').forEach(el => el.classList.remove('prev'));
      }, 500);
      agentIdx = (agentIdx + 1) % agents.length;
      agents[agentIdx].classList.add('active');
    }, 2500);
  }
}
document.addEventListener('DOMContentLoaded', initAgentCycling);
if (document.readyState === 'interactive' || document.readyState === 'complete') {
  initAgentCycling();
}

// MemCore Canvas Memory Field Simulation
const canvas = document.getElementById('memory-canvas');
if (canvas) {
  const ctx = canvas.getContext('2d');
  let width, height;
  let mouse = { x: -1000, y: -1000 };

  const clusters = [
    { x: 0.25, y: 0.35, label: "Auth & Tokens", count: 48, color: "#ff7a17" },
    { x: 0.72, y: 0.28, label: "Database Schema", count: 64, color: "#10b981" },
    { x: 0.48, y: 0.70, label: "Risk-Aware GC Rules", count: 52, color: "#00d2ff" },
    { x: 0.82, y: 0.75, label: "Token Budget Optimizer", count: 36, color: "#a855f7" },
    { x: 0.20, y: 0.80, label: "Code-Grounded Verification", count: 30, color: "#f59e0b" }
  ];

  let points = [];

  function resize() {
    const rect = canvas.parentElement.getBoundingClientRect();
    width = canvas.width = rect.width;
    height = canvas.height = rect.height;
    initPoints();
  }

  function initPoints() {
    points = [];
    clusters.forEach(c => {
      const cx = c.x * width;
      const cy = c.y * height;
      for (let i = 0; i < c.count; i++) {
        const radius = Math.random() * 65;
        const angle = Math.random() * Math.PI * 2;
        points.push({
          x: cx + Math.cos(angle) * radius,
          y: cy + Math.sin(angle) * radius,
          baseX: cx + Math.cos(angle) * radius,
          baseY: cy + Math.sin(angle) * radius,
          cluster: c,
          vx: (Math.random() - 0.5) * 0.4,
          vy: (Math.random() - 0.5) * 0.4,
          radius: 1.8 + Math.random() * 1.5,
          color: c.color
        });
      }
    });
  }

  window.addEventListener('resize', resize);
  resize();

  canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
  });

  canvas.addEventListener('mouseleave', () => {
    mouse.x = -1000;
    mouse.y = -1000;
  });

  function draw() {
    ctx.clearRect(0, 0, width, height);

    // Find 5 closest points to mouse
    let sorted = [];
    if (mouse.x > 0 && mouse.y > 0) {
      sorted = points
        .map(p => ({ point: p, dist: Math.hypot(p.x - mouse.x, p.y - mouse.y) }))
        .sort((a, b) => a.dist - b.dist)
        .slice(0, 5);
    }

    // Draw cluster centers & label glow
    clusters.forEach(c => {
      const cx = c.x * width;
      const cy = c.y * height;
      ctx.beginPath();
      ctx.arc(cx, cy, 55, 0, Math.PI * 2);
      ctx.fillStyle = c.color + "08";
      ctx.fill();

      ctx.font = "11px 'Geist Mono', monospace";
      ctx.fillStyle = c.color + "99";
      ctx.fillText(c.label, cx - 40, cy - 65);
    });

    // Draw cluster edges
    ctx.lineWidth = 0.5;
    ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
    for (let i = 0; i < points.length; i += 2) {
      for (let j = i + 1; j < points.length; j += 4) {
        if (points[i].cluster === points[j].cluster) {
          const d = Math.hypot(points[i].x - points[j].x, points[i].y - points[j].y);
          if (d < 45) {
            ctx.beginPath();
            ctx.moveTo(points[i].x, points[i].y);
            ctx.lineTo(points[j].x, points[j].y);
            ctx.stroke();
          }
        }
      }
    }

    // Connect mouse recall ray to 5 nearest memories
    if (sorted.length > 0) {
      // Mouse hub
      ctx.beginPath();
      ctx.arc(mouse.x, mouse.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = "#ff7a17";
      ctx.fill();

      ctx.beginPath();
      ctx.arc(mouse.x, mouse.y, 16, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(255, 122, 23, 0.4)";
      ctx.lineWidth = 1;
      ctx.stroke();

      sorted.forEach((item, index) => {
        ctx.beginPath();
        ctx.moveTo(mouse.x, mouse.y);
        ctx.lineTo(item.point.x, item.point.y);
        ctx.strokeStyle = "rgba(255, 122, 23, " + Math.max(0.2, (1 - item.dist / 300)) + ")";
        ctx.lineWidth = 1.2;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Highlight hit point
        ctx.beginPath();
        ctx.arc(item.point.x, item.point.y, item.point.radius + 3, 0, Math.PI * 2);
        ctx.fillStyle = "#ff7a17";
        ctx.fill();

        // Label rank
        ctx.font = "10px 'Geist Mono', monospace";
        ctx.fillStyle = "#ffffff";
        ctx.fillText(`rank #${index + 1} (${(1 - item.dist/500).toFixed(2)})`, item.point.x + 8, item.point.y - 4);
      });
    }

    // Draw all points
    points.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      if (Math.hypot(p.x - p.baseX, p.y - p.baseY) > 20) {
        p.vx *= -1;
        p.vy *= -1;
      }

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 4;
      ctx.fill();
      ctx.shadowBlur = 0;
    });

    requestAnimationFrame(draw);
  }

  draw();
}

// Interactive Use Cases Tab switching
const useCaseData = {
  agents: {
    why: "MemCore connects Claude Code, Cursor, Codex, and Antigravity to a single, zero-loss memory substrate.",
    col1Title: "claude-code · monday 14:02",
    col1Logs: [
      { prompt: ">", text: "fix oauth token leak on session expiration" },
      { dot: true, text: "Edit(src/auth/oauth.py)" },
      { dot: true, text: "Run(pytest tests/test_auth.py)" },
      { out: true, text: "⎿ 42 passed, 0 warnings" },
      { hook: true, text: "PostToolUse → memcore.record_memory()" }
    ],
    hubTag: "memcore · 127.0.0.1:8000",
    hubContent: "Always validate OAuth2 PKCE code_verifier before issuing tokens. Protected rule tagged.",
    hubFrom: "captured from claude-code",
    col2Title: "cursor · tuesday 10:15",
    col2Chat: [
      { bubble: "How should authentication tokens be validated?" },
      { chip: "memcore_hybrid_recall · 1 protected result" },
      { reply: "Validate code_verifier with SHA-256 PKCE contract; established Monday in oauth.py. Flagged with 100% confidence." }
    ],
    withoutText: "Without MemCore: Each session starts blank. You re-prompt token constraints and risk regressions."
  },
  gc: {
    why: "MemGC Risk-Aware Pruning automatically merges redundant memories while guaranteeing Zero Protected Loss.",
    col1Title: "memcore-daemon · nightly-audit",
    col1Logs: [
      { prompt: "$", text: "python -m memcore.gc --dry-run=false" },
      { dot: true, text: "EvaluateUtility(U) & Risk(R) across 320 records" },
      { out: true, text: "⎿ 18 duplicate observations merged" },
      { out: true, text: "⎿ 24 stale temporary edits superseded" },
      { hook: true, text: "MemGC Action: 8 superseded, 14 protected kept" }
    ],
    hubTag: "memcore · MemGC Risk Engine",
    hubContent: "Protected Security Baseline & Contracts: ZERO loss guarantee (Risk score R = 1.0 -> NEVER prune).",
    hubFrom: "MemGC lifecycle engine",
    col2Title: "claude-code · next session",
    col2Chat: [
      { bubble: "implement refresh token rotation" },
      { chip: "context_build · 380 tokens packed (1,200 tokens pruned)" },
      { reply: "Ready. Consolidated memory keeps exactly what's needed without prompt noise or lost guardrails." }
    ],
    withoutText: "Without MemCore: Unpruned memory stores blow past context limits with duplicate chat noise."
  },
  verify: {
    why: "Repository-Grounded Verification continuously validates memory claims against current code ASTs.",
    col1Title: "verification-worker · background",
    col1Logs: [
      { prompt: "$", text: "memcore verify --repo-root=." },
      { dot: true, text: "AST check: src/auth/oauth.py :: validate_pkce()" },
      { out: true, text: "⎿ Symbol exists on disk, AST signature matches" },
      { hook: true, text: "Verification status: VERIFIED (confidence: 98%)" }
    ],
    hubTag: "memcore · Code AST Checker",
    hubContent: "Flags contradictions immediately if a refactor renames or removes classes/functions.",
    hubFrom: "disk AST ground-truth",
    col2Title: "antigravity · active refactor",
    col2Chat: [
      { bubble: "rename validate_pkce to verify_pkce_token" },
      { chip: "memcore_verify · dependency alert" },
      { reply: "Memory updated: mapped symbol rename across 3 linked prompt rules and updated callers." }
    ],
    withoutText: "Without MemCore: Agent hallucinates outdated APIs and old function signatures."
  },
  optimizer: {
    why: "Token-Budgeted Context Optimizer fits maximal-utility context within any strict prompt window.",
    col1Title: "agent-session · prompt prep",
    col1Logs: [
      { prompt: ">", text: "optimize context for task 'fix race in cache'" },
      { dot: true, text: "Budget constraint: 1,000 tokens" },
      { dot: true, text: "Graph knapsack selection: 4 critical nodes chosen" },
      { out: true, text: "⎿ Packed 842 / 1000 tokens (158 tokens headroom)" },
      { hook: true, text: "Zero truncation, highest utility preserved" }
    ],
    hubTag: "memcore · Knapsack Optimizer",
    hubContent: "Prioritizes high-utility security contracts + direct dependencies before general notes.",
    hubFrom: "utility-budget optimizer",
    col2Title: "session context · ready",
    col2Chat: [
      { bubble: "Context loaded seamlessly" },
      { chip: "token_efficiency · 92% reduction" },
      { reply: "Cache locking logic and concurrency invariant injected with zero irrelevant fluff." }
    ],
    withoutText: "Without MemCore: Full logs overwhelm LLM context, spiking API costs and causing attention loss."
  },
  security: {
    why: "Automatic Secret Redaction strips API keys and passwords before persistence, stopping prompt injections.",
    col1Title: "agent · terminal command",
    col1Logs: [
      { prompt: ">", text: "fetch auth headers with AWS_SECRET_KEY and Bearer token" },
      { dot: true, text: "memcore.security.sanitize_input()" },
      { out: true, text: "⎿ Detected Bearer token & AWS key" },
      { hook: true, text: "Redacted to [REDACTED_SECRET] prior to disk write" }
    ],
    hubTag: "memcore · Secret Redactor",
    hubContent: "Sanitizes untrusted memory inputs. Prevents prompt injection attacks from malicious files.",
    hubFrom: "security boundary",
    col2Title: "mcp-server · query",
    col2Chat: [
      { bubble: "show recent auth memories" },
      { chip: "zero_credentials_leaked · safe" },
      { reply: "Clean memories returned with redacted secrets. Local database remains fully compliant." }
    ],
    withoutText: "Without MemCore: Agent logs credentials to plaintext files, creating major security hazards."
  },
  local: {
    why: "100% Local-First: Runs on your machine with SQLite FTS5, local vectors, and zero mandatory cloud keys.",
    col1Title: "terminal · localhost:8000",
    col1Logs: [
      { prompt: "$", text: "pip install memcore && memcore start" },
      { dot: true, text: "Binding 127.0.0.1:8000 (REST & MCP)" },
      { dot: true, text: "SQLite FTS5 + on-device embeddings initialized" },
      { out: true, text: "⎿ 0 telemetry, 0 network requests" },
      { hook: true, text: "Status: Online, keyless mode enabled" }
    ],
    hubTag: "memcore · 127.0.0.1:8000",
    hubContent: "Your proprietary code never leaves localhost. Apache-2.0 licensed.",
    hubFrom: "local machine store",
    col2Title: "developer · privacy",
    col2Chat: [
      { bubble: "Does any proprietary data cross the network?" },
      { chip: "air_gapped_ready · 100% on-device" },
      { reply: "Zero network outbound. Full persistence, indexing, and GC run completely on localhost." }
    ],
    withoutText: "Without MemCore: Proprietary codebase context is transmitted to third-party memory SaaS APIs."
  }
};

window.switchUseCase = function(key, btn) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  const data = useCaseData[key];
  if (!data) return;

  const stage = document.getElementById('use-case-stage');
  stage.style.opacity = '0.4';
  
  setTimeout(() => {
    document.getElementById('uc-why').textContent = data.why;
    document.getElementById('uc-col1-title').textContent = data.col1Title;
    
    const logsWrap = document.getElementById('uc-col1-logs');
    logsWrap.innerHTML = data.col1Logs.map(l => {
      if (l.prompt) return `<div><span class="term-prompt">${l.prompt}</span> ${l.text}</div>`;
      if (l.dot) return `<div><span style="color:var(--accent);">⏺</span> ${l.text}</div>`;
      if (l.out) return `<div class="term-success">${l.text}</div>`;
      if (l.hook) return `<div class="term-badge">${l.text}</div>`;
      return `<div>${l.text}</div>`;
    }).join('');

    document.getElementById('uc-hub-tag').textContent = data.hubTag;
    document.getElementById('uc-hub-content').textContent = data.hubContent;
    document.getElementById('uc-hub-from').textContent = data.hubFrom;

    document.getElementById('uc-col2-title').textContent = data.col2Title;
    const chatWrap = document.getElementById('uc-col2-chat');
    chatWrap.innerHTML = data.col2Chat.map(c => {
      return `
        <div style="background:var(--bg-subtle); padding:8px 12px; border-radius:6px; margin-bottom:6px;">
          <div style="font-weight:600; color:var(--text); margin-bottom:2px;">› ${c.bubble}</div>
          <div class="term-badge" style="display:inline-block; margin-bottom:4px;">${c.chip}</div>
          <div style="color:var(--text-muted); font-size:0.78rem;">${c.reply}</div>
        </div>
      `;
    }).join('');

    document.getElementById('uc-without').textContent = data.withoutText;
    stage.style.opacity = '1';
  }, 150);
};

// Clipboard toast helper
window.copyCmd = function(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const toast = document.getElementById('toast');
    toast.textContent = `Copied to clipboard: ${text}`;
    toast.classList.add('show');
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = `<span style="color:var(--green)">✓ copied</span>`;
      setTimeout(() => { btn.innerHTML = orig; }, 1800);
    }
    setTimeout(() => { toast.classList.remove('show'); }, 2500);
  });
};

// Theme Toggle
window.toggleTheme = function() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('memcore-theme', next);
};

// Load saved theme
(function() {
  const saved = localStorage.getItem('memcore-theme');
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
  }
})();

// Benchmark interactive dot matrix toggle (top 5 vs top 10)
window.setBenchMode = function(k, btn) {
  document.querySelectorAll('.bench-toggle button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  const groups = document.querySelectorAll('.b-dot');
  if (k === 5) {
    document.getElementById('bench-verdict').innerHTML = `<strong>476 of 500</strong> questions found gold context in top 5 (<strong>95.2%</strong> Recall@5).`;
    groups.forEach((d, i) => {
      if (i % 21 === 0) {
        d.className = 'b-dot miss';
      } else {
        d.className = 'b-dot hit';
      }
    });
  } else {
    document.getElementById('bench-verdict').innerHTML = `<strong>493 of 500</strong> questions found gold context in top 10 (<strong>98.6%</strong> Recall@10).`;
    groups.forEach((d, i) => {
      if (i % 71 === 0) {
        d.className = 'b-dot miss';
      } else {
        d.className = 'b-dot hit';
      }
    });
  }
};

// Interactive Context & MemGC Simulator
window.updateSim = function() {
  const rawTokens = parseInt(document.getElementById('sim-raw').value, 10);
  const gcLevel = parseInt(document.getElementById('sim-gc').value, 10);
  const budget = parseInt(document.getElementById('sim-budget').value, 10);

  document.getElementById('sim-raw-val').textContent = rawTokens.toLocaleString();
  document.getElementById('sim-gc-val').textContent = `${gcLevel}%`;
  document.getElementById('sim-budget-val').textContent = `${budget.toLocaleString()} tokens`;

  // Compute GC savings
  const tokensAfterGC = Math.round(rawTokens * (1 - (gcLevel * 0.0075)));
  const savedTokens = rawTokens - tokensAfterGC;
  const packedTokens = Math.min(tokensAfterGC, budget);
  const reductionPercent = Math.round(((rawTokens - packedTokens) / rawTokens) * 100);

  document.getElementById('sim-packed').textContent = `${packedTokens.toLocaleString()} tokens`;
  document.getElementById('sim-saved').textContent = `${savedTokens.toLocaleString()} tokens pruned (${reductionPercent}% total savings)`;

  const usedPct = Math.min(100, Math.round((packedTokens / rawTokens) * 100));
  const savedPct = Math.min(100 - usedPct, Math.round((savedTokens / rawTokens) * 100));

  document.getElementById('sim-bar-used').style.width = `${usedPct}%`;
  document.getElementById('sim-bar-saved').style.width = `${savedPct}%`;
};

// Wire agent connect command selector
window.selectAgentCmd = function(name, btn) {
  document.querySelectorAll('.Install-module__Pi_Eza__chip, .agent-chip').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const code = document.getElementById('agent-connect-code');
  if (code) {
    code.textContent = `python -m memcore.connect ${name.toLowerCase().replace(/\s+/g, '-')}`;
  }
};
