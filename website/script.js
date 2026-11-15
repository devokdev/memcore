// MemCore Canvas Memory Field Simulation
const canvas = document.getElementById('memory-canvas');
if (canvas) {
  const ctx = canvas.getContext('2d');
  let width, height;
  let mouse = { x: -1000, y: -1000 };

  const clusters = [
    { x: 0.25, y: 0.35, label: "Auth & Security Tokens", count: 48, color: "#c084fc", protected: true },
    { x: 0.68, y: 0.30, label: "Database Schemas & Pools", count: 64, color: "#8e8e9c", protected: false },
    { x: 0.45, y: 0.65, label: "Risk-Aware MemGC Rules", count: 52, color: "#38bdf8", protected: false },
    { x: 0.78, y: 0.68, label: "Token Budget Optimizer", count: 36, color: "#4ade80", protected: false },
    { x: 0.20, y: 0.75, label: "AST-Grounded Verification", count: 30, color: "#8e8e9c", protected: false }
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
      for (let i = 0; i < 9; i++) {
        points.push({
          x: cx + (Math.random() - 0.5) * 80,
          y: cy + (Math.random() - 0.5) * 80,
          vx: (Math.random() - 0.5) * 0.4,
          vy: (Math.random() - 0.5) * 0.4,
          label: c.label,
          color: c.color,
          protected: c.protected,
          radius: c.protected ? 4.5 : 3
        });
      }
    });
  }

  function animate() {
    ctx.clearRect(0, 0, width, height);

    // Draw graph connections
    ctx.lineWidth = 0.75;
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const dx = points[i].x - points[j].x;
        const dy = points[i].y - points[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 65) {
          ctx.strokeStyle = `rgba(142, 142, 156, ${0.15 * (1 - dist / 65)})`;
          ctx.beginPath();
          ctx.moveTo(points[i].x, points[i].y);
          ctx.lineTo(points[j].x, points[j].y);
          ctx.stroke();
        }
      }
    }

    // Draw points & physics
    points.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 10 || p.x > width - 10) p.vx *= -1;
      if (p.y < 10 || p.y > height - 10) p.vy *= -1;

      const dMouse = Math.hypot(mouse.x - p.x, mouse.y - p.y);
      const isHover = dMouse < 16;

      if (p.protected) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, isHover ? 10 : 7, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(192, 132, 252, 0.15)";
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(p.x, p.y, isHover ? p.radius + 2 : p.radius, 0, Math.PI * 2);
      ctx.fillStyle = isHover ? "#38bdf8" : p.color;
      ctx.fill();

      if (isHover) {
        const payloadBox = document.getElementById('hover-payload');
        if (payloadBox) {
          payloadBox.textContent = `${p.label} · ${p.protected ? 'PROTECTED INVARIANT' : 'ACTIVE MEMORY'}`;
        }
      }
    });

    requestAnimationFrame(animate);
  }

  window.addEventListener('resize', resize);
  canvas.addEventListener('mousemove', e => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
  });
  canvas.addEventListener('mouseleave', () => {
    mouse.x = -1000;
    mouse.y = -1000;
    const payloadBox = document.getElementById('hover-payload');
    if (payloadBox) payloadBox.textContent = 'Hover any node to inspect memory';
  });

  resize();
  animate();
}

// Copy Command Helper
function copyCmd(text, el) {
  navigator.clipboard.writeText(text);
  const pill = el.querySelector('.copy-pill');
  if (pill) {
    const original = pill.textContent;
    pill.textContent = 'copied!';
    setTimeout(() => pill.textContent = original, 1500);
  }
}
