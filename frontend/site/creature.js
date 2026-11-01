(() => {
  const orb = document.getElementById('eye-orb');
  const visual = document.querySelector('.hero-visual');
  if (!orb || !visual) return;
  let drag = null;
  let count = 0;
  let start = null;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  function gaze(event) {
    const rect = orb.getBoundingClientRect();
    const dx = (event.clientX - (rect.left + rect.width / 2)) / Math.max(1, rect.width);
    const dy = (event.clientY - (rect.top + rect.height / 2)) / Math.max(1, rect.height);
    orb.style.setProperty('--eye-x', `${Math.max(-7, Math.min(7, dx * 12))}px`);
    orb.style.setProperty('--eye-y', `${Math.max(-6, Math.min(6, dy * 11))}px`);
  }
  document.addEventListener('pointermove', gaze, { passive: true });
  orb.addEventListener('pointerdown', (event) => {
    start = { x: event.clientX, y: event.clientY };
    drag = { x: event.clientX, y: event.clientY };
    orb.setPointerCapture(event.pointerId);
    orb.classList.add('dragging');
  });
  orb.addEventListener('pointermove', (event) => {
    if (!drag) return;
    orb.style.setProperty('--drag-x', `${Math.max(-90, Math.min(90, event.clientX - drag.x))}px`);
    orb.style.setProperty('--drag-y', `${Math.max(-90, Math.min(90, event.clientY - drag.y))}px`);
    orb.style.setProperty('--orb-rotate', `${Math.max(-15, Math.min(15, (event.clientX - drag.x) * .2))}deg`);
  });
  function release() {
    if (!drag) return;
    drag = null;
    orb.classList.remove('dragging');
    orb.style.setProperty('--drag-x', '0px');
    orb.style.setProperty('--drag-y', '0px');
    orb.style.setProperty('--orb-rotate', '0deg');
  }
  orb.addEventListener('pointerup', release);
  orb.addEventListener('pointercancel', release);
  orb.addEventListener('click', (event) => {
    count++;
    document.getElementById('eye-orb-count').textContent = String(count).padStart(2, '0');
    orb.classList.remove('popped');
    void orb.offsetWidth;
    orb.classList.add('popped');
    if (reduced || document.documentElement.classList.contains('motion-paused')) return;
    for (let i = 0; i < 8; i++) {
      const particle = document.createElement('span');
      particle.className = 'eye-particle';
      particle.style.setProperty('--a', `${i * 45}deg`);
      orb.append(particle);
      particle.addEventListener('animationend', () => particle.remove(), { once: true });
    }
    if (start && Math.hypot(event.clientX - start.x, event.clientY - start.y) > 5) {
      visual.style.setProperty('--hero-x', `${Math.random() * 8 - 4}px`);
      visual.style.setProperty('--hero-y', `${Math.random() * 8 - 4}px`);
    }
  });
})();
