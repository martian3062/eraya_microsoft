// Lorenz attractor canvas animation
(function () {
  const canvas = document.getElementById('attractor-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  function resize() { canvas.width = innerWidth; canvas.height = innerHeight; }
  resize();
  window.addEventListener('resize', resize);

  // Lorenz params
  const s = 10, r = 28, b = 8 / 3, dt = 0.006;
  let x = 0.1, y = 0, z = 0;
  const trail = [], MAX = 1800;

  function step() {
    const dx = s * (y - x), dy = x * (r - z) - y, dz = x * y - b * z;
    x += dx * dt; y += dy * dt; z += dz * dt;
    return { x, y, z };
  }

  function project(p) {
    const sc = Math.min(canvas.width, canvas.height) / 55;
    return { sx: canvas.width / 2 + p.x * sc, sy: canvas.height / 2 - (p.z - 25) * sc * 0.7 };
  }

  function draw() {
    ctx.fillStyle = document.documentElement.classList.contains('dark')
      ? 'rgba(6,13,26,0.05)' : 'rgba(253,250,244,0.06)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (let i = 0; i < 4; i++) { trail.push(step()); if (trail.length > MAX) trail.shift(); }

    const len = trail.length;
    for (let i = 1; i < len; i++) {
      const a = i / len;
      const p0 = project(trail[i - 1]), p1 = project(trail[i]);
      ctx.beginPath();
      ctx.moveTo(p0.sx, p0.sy);
      ctx.lineTo(p1.sx, p1.sy);
      ctx.strokeStyle = `rgba(45,212,191,${a * 0.35})`;
      ctx.lineWidth = a * 1.4;
      ctx.stroke();
    }
    requestAnimationFrame(draw);
  }
  draw();
}());
