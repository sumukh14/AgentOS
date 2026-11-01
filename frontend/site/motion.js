(() => {
  const root = document.documentElement;
  const prefersReducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const toggle = document.querySelector('#motion-toggle');
  const toggleText = document.querySelector('#motion-toggle-text');
  const visual = document.querySelector('.hero-visual');
  const canvas = document.querySelector('#agent-field');
  const context = canvas.getContext('2d', { alpha: true });
  let motionOn = !prefersReducedMotion;
  let heroVisible = false;
  let animationFrame = 0;
  let lastFrame = 0;
  let fieldWidth = 0;
  let fieldHeight = 0;
  let particles = [];
  const pointer = { x: -1000, y: -1000 };

  function setMotion(value) {
    motionOn = value;
    root.classList.toggle('motion-paused', !value);
    toggle.setAttribute('aria-pressed', String(value));
    toggle.setAttribute('aria-label', value ? 'Pause decorative motion' : 'Resume decorative motion');
    toggleText.textContent = value ? 'MOTION ON' : 'MOTION OFF';
    if (value) startField();
    else {
      cancelAnimationFrame(animationFrame);
      animationFrame = 0;
      context.clearRect(0, 0, fieldWidth, fieldHeight);
      visual.style.setProperty('--hero-x', '0px');
      visual.style.setProperty('--hero-y', '0px');
    }
  }
  if (prefersReducedMotion) toggle.hidden = true;
  toggle.addEventListener('click', () => setMotion(!motionOn));
  setMotion(motionOn);

  function resizeField() {
    const bounds = visual.getBoundingClientRect();
    fieldWidth = Math.max(1, Math.round(bounds.width));
    fieldHeight = Math.max(1, Math.round(bounds.height));
    const ratio = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.round(fieldWidth * ratio);
    canvas.height = Math.round(fieldHeight * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    const count = innerWidth < 620 ? 22 : 42;
    particles = Array.from({ length: count }, (_, index) => ({
      x: Math.random() * fieldWidth,
      y: Math.random() * fieldHeight,
      vx: (Math.random() - .5) * .22,
      vy: (Math.random() - .5) * .22,
      radius: index % 9 === 0 ? 2 : 1
    }));
  }
  new ResizeObserver(resizeField).observe(visual);

  function drawField(time) {
    animationFrame = 0;
    if (!motionOn || !heroVisible || document.hidden) return;
    if (time - lastFrame < 30) { animationFrame = requestAnimationFrame(drawField); return; }
    const dt = Math.min((time - lastFrame) / 30 || 1, 2);
    lastFrame = time;
    context.clearRect(0, 0, fieldWidth, fieldHeight);
    for (const point of particles) {
      point.x += point.vx * dt;
      point.y += point.vy * dt;
      if (point.x < 0 || point.x > fieldWidth) point.vx *= -1;
      if (point.y < 0 || point.y > fieldHeight) point.vy *= -1;
      const dx = point.x - pointer.x;
      const dy = point.y - pointer.y;
      const distance = Math.hypot(dx, dy);
      if (distance < 90 && distance > 1) {
        point.x += dx / distance * (90 - distance) * .012;
        point.y += dy / distance * (90 - distance) * .012;
      }
    }
    for (let a = 0; a < particles.length; a++) {
      for (let b = a + 1; b < particles.length; b++) {
        const one = particles[a], two = particles[b];
        const distance = Math.hypot(one.x - two.x, one.y - two.y);
        if (distance > 92) continue;
        context.strokeStyle = `rgba(172, 154, 242, ${(.18 * (1 - distance / 92)).toFixed(3)})`;
        context.lineWidth = .7;
        context.beginPath(); context.moveTo(one.x, one.y); context.lineTo(two.x, two.y); context.stroke();
      }
    }
    for (const point of particles) {
      context.fillStyle = point.radius > 1 ? 'rgba(223,255,112,.8)' : 'rgba(205,202,255,.5)';
      context.beginPath(); context.arc(point.x, point.y, point.radius, 0, Math.PI * 2); context.fill();
    }
    animationFrame = requestAnimationFrame(drawField);
  }
  function startField() {
    if (motionOn && heroVisible && !document.hidden && !animationFrame) {
      lastFrame = 0;
      animationFrame = requestAnimationFrame(drawField);
    }
  }
  new IntersectionObserver(entries => {
    heroVisible = entries[0].isIntersecting;
    if (heroVisible) startField();
    else { cancelAnimationFrame(animationFrame); animationFrame = 0; }
  }, { threshold: .05 }).observe(visual);
  document.addEventListener('visibilitychange', startField);
  visual.addEventListener('pointermove', event => {
    if (!motionOn || event.pointerType === 'touch') return;
    const rect = visual.getBoundingClientRect();
    pointer.x = event.clientX - rect.left;
    pointer.y = event.clientY - rect.top;
    visual.style.setProperty('--hero-x', `${((pointer.x / rect.width) - .5) * 14}px`);
    visual.style.setProperty('--hero-y', `${((pointer.y / rect.height) - .5) * 14}px`);
  }, { passive: true });
  visual.addEventListener('pointerleave', () => {
    pointer.x = -1000; pointer.y = -1000;
    visual.style.setProperty('--hero-x', '0px'); visual.style.setProperty('--hero-y', '0px');
  });

  document.querySelectorAll('.architecture-card').forEach(card => {
    card.addEventListener('pointermove', event => {
      const rect = card.getBoundingClientRect();
      card.style.setProperty('--spot-x', `${event.clientX - rect.left}px`);
      card.style.setProperty('--spot-y', `${event.clientY - rect.top}px`);
    }, { passive: true });
  });

  const track = document.querySelector('#flow-track');
  const flowStatus = document.querySelector('#flow-status');
  const signalArt = document.querySelector('.signal-art');
  let flowKey = '';
  function renderFlow(trace) {
    const key = `${trace.scenario}:${trace.mode}`;
    if (key !== flowKey) {
      flowKey = key;
      track.replaceChildren();
      trace.steps.forEach((step, index) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `flow-step ${step.type}`;
        button.setAttribute('aria-label', `Go to step ${index + 1}: ${step.title}`);
        button.title = `${step.role} — ${step.title}`;
        const node = document.createElement('span'); node.className = 'flow-node'; node.textContent = String(index + 1).padStart(2, '0');
        const name = document.createElement('span'); name.className = 'flow-name'; name.textContent = trace.mode === 'single' ? step.title.split(' ')[0].toUpperCase() : step.role;
        button.append(node, name);
        button.addEventListener('click', () => window.AgentOS.seekTo(index + 1));
        track.append(button);
      });
      const packet = document.createElement('span'); packet.className = 'flow-packet'; packet.setAttribute('aria-hidden', 'true'); track.append(packet);
    }
    const buttons = [...track.querySelectorAll('.flow-step')];
    buttons.forEach((button, index) => {
      button.classList.toggle('complete', index < trace.current - 1);
      button.classList.toggle('active', index === trace.current - 1);
      if (index === trace.current - 1) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
    const percent = trace.current <= 0 ? 0 : (trace.current - 1) / Math.max(1, trace.steps.length - 1) * 100;
    track.style.setProperty('--flow-progress', `${percent}%`);
    track.style.setProperty('--packet-position', `${5 + percent * .9}%`);
    track.classList.toggle('has-progress', trace.current > 0);
    flowStatus.textContent = trace.current === 0 ? 'STANDBY' : trace.current === trace.steps.length ? 'TRACE COMPLETE' : `STEP ${String(trace.current).padStart(2, '0')} / ${String(trace.steps.length).padStart(2, '0')}`;
    const type = trace.current ? trace.steps[trace.current - 1].type : '';
    signalArt.classList.toggle('is-active', trace.current > 0);
    signalArt.classList.toggle('is-risk', type === 'risk');
    signalArt.classList.toggle('is-check', type === 'check');
  }
  addEventListener('agentos:trace', event => renderFlow(event.detail));
  renderFlow(window.AgentOS.getTrace());

  const compare = document.querySelector('.compare-shell');
  const compareRange = document.querySelector('#compare-step');
  let compareTimeout;
  compareRange.addEventListener('input', () => {
    compare.classList.remove('is-shifting');
    void compare.offsetWidth;
    compare.classList.add('is-shifting');
    clearTimeout(compareTimeout);
    compareTimeout = setTimeout(() => compare.classList.remove('is-shifting'), 380);
  });
  const ablationResult = document.querySelector('.ablation-result');
  let ablationTimeout;
  document.querySelectorAll('.ablation-button').forEach(button => button.addEventListener('click', () => {
    ablationResult.classList.remove('is-changing');
    void ablationResult.offsetWidth;
    ablationResult.classList.add('is-changing');
    clearTimeout(ablationTimeout);
    ablationTimeout = setTimeout(() => ablationResult.classList.remove('is-changing'), 420);
  }));
})();
