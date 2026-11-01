(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const motionAllowed = () => !reduced && !document.documentElement.classList.contains('motion-paused');
  const orb = document.querySelector('#cursor-orb');
  const orbLabel = orb.querySelector('span');
  const finePointer = matchMedia('(pointer:fine)').matches;
  let pointerX = -100, pointerY = -100, orbX = -100, orbY = -100, orbFrame = 0;

  function cursorFrame() {
    orbFrame = 0;
    if (!motionAllowed() || !finePointer || document.hidden) return;
    orbX += (pointerX - orbX) * .23;
    orbY += (pointerY - orbY) * .23;
    orb.style.transform = `translate3d(${orbX - orb.offsetWidth / 2}px,${orbY - orb.offsetHeight / 2}px,0)`;
    if (Math.abs(pointerX - orbX) > .3 || Math.abs(pointerY - orbY) > .3) orbFrame = requestAnimationFrame(cursorFrame);
  }
  if (finePointer && !reduced) {
    document.addEventListener('pointermove', event => {
      if (event.pointerType !== 'mouse' && event.pointerType !== 'pen') return;
      pointerX = event.clientX; pointerY = event.clientY;
      const target = event.target;
      const label = target.closest('.compare-columns,.compare-range') ? 'DRAG' :
        target.closest('.hero-visual') ? 'ORBIT' :
        target.closest('.flow-step,.scenario-button,.mode-button,.ablation-button') ? 'SELECT' :
        target.closest('a,.chapter-rail') ? 'GO' : '';
      orbLabel.textContent = label;
      orb.classList.toggle('has-label', Boolean(label));
      orb.classList.toggle('is-visible', motionAllowed());
      if (!orbFrame) orbFrame = requestAnimationFrame(cursorFrame);
    }, { passive: true });
    addEventListener('pointerout', event => {
      if (!event.relatedTarget) orb.classList.remove('is-visible');
    });
    document.addEventListener('pointerdown', () => orb.classList.add('is-down'));
    document.addEventListener('pointerup', () => orb.classList.remove('is-down'));
  }

  const chapters = [...document.querySelectorAll('.chapter-rail a')];
  const sections = ['top', 'question', 'lab', 'method', 'live'].map(id => document.getElementById(id));
  const heroVisual = document.querySelector('.hero-visual');
  let scrollFrame = 0;
  function updateScroll() {
    scrollFrame = 0;
    const probe = scrollY + innerHeight * .42;
    let current = 0;
    for (let index = 1; index < sections.length; index++) {
      if (sections[index].offsetTop <= probe) current = index;
    }
    chapters.forEach((link, index) => {
      if (index === current) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    });
    if (motionAllowed()) heroVisual.style.setProperty('--scroll-y', `${Math.max(-30, -scrollY * .045)}px`);
  }
  addEventListener('scroll', () => { if (!scrollFrame) scrollFrame = requestAnimationFrame(updateScroll); }, { passive: true });
  addEventListener('resize', updateScroll);
  updateScroll();

  document.addEventListener('pointerdown', event => {
    if (!motionAllowed()) return;
    const target = event.target.closest('.pill-button,.scenario-button,.mode-button,.flow-step,.ablation-button,.run-button,.step-button,.architecture-card');
    if (!target) return;
    const rect = target.getBoundingClientRect();
    const ripple = document.createElement('span');
    ripple.className = 'tap-ripple';
    ripple.style.left = `${event.clientX - rect.left}px`;
    ripple.style.top = `${event.clientY - rect.top}px`;
    target.append(ripple);
    ripple.addEventListener('animationend', () => ripple.remove(), { once: true });
  });

  const range = document.querySelector('#compare-step');
  const compareSurface = document.querySelector('.compare-columns');
  let compareStart = null;
  let mouseCompareStart = null;
  function changeMoment(direction) {
    range.value = String(Math.max(1, Math.min(6, Number(range.value) + direction)));
    range.dispatchEvent(new Event('input', { bubbles: true }));
  }
  compareSurface.addEventListener('touchstart', event => {
    const touch = event.touches[0]; compareStart = { x: touch.clientX, y: touch.clientY };
  }, { passive: true });
  compareSurface.addEventListener('touchend', event => {
    if (!compareStart) return;
    const touch = event.changedTouches[0];
    const dx = touch.clientX - compareStart.x, dy = touch.clientY - compareStart.y;
    if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy) * 1.25) changeMoment(dx < 0 ? 1 : -1);
    compareStart = null;
  }, { passive: true });
  compareSurface.addEventListener('pointerdown', event => {
    if (event.pointerType === 'touch') return;
    mouseCompareStart = { x: event.clientX, y: event.clientY };
    compareSurface.setPointerCapture(event.pointerId);
  });
  compareSurface.addEventListener('pointermove', event => {
    if (!mouseCompareStart || event.pointerType === 'touch') return;
    const dx = event.clientX - mouseCompareStart.x, dy = event.clientY - mouseCompareStart.y;
    if (Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(dy) * 1.25) {
      changeMoment(dx < 0 ? 1 : -1);
      mouseCompareStart = { x: event.clientX, y: event.clientY };
    }
  });
  compareSurface.addEventListener('pointerup', event => {
    if (!mouseCompareStart || event.pointerType === 'touch') return;
    const dx = event.clientX - mouseCompareStart.x, dy = event.clientY - mouseCompareStart.y;
    if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy) * 1.25) changeMoment(dx < 0 ? 1 : -1);
    mouseCompareStart = null;
  });
  compareSurface.addEventListener('pointercancel', () => { mouseCompareStart = null; });
  let wheelAt = 0;
  compareSurface.addEventListener('wheel', event => {
    if (!(event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY) * 1.4)) return;
    event.preventDefault();
    if (performance.now() - wheelAt < 200) return;
    wheelAt = performance.now();
    changeMoment((event.deltaX || event.deltaY) > 0 ? 1 : -1);
  }, { passive: false });

  const flowTrack = document.querySelector('#flow-track');
  let flowStart = null;
  flowTrack.addEventListener('touchstart', event => {
    const touch = event.touches[0]; flowStart = { x: touch.clientX, y: touch.clientY };
  }, { passive: true });
  flowTrack.addEventListener('touchend', event => {
    if (!flowStart) return;
    const touch = event.changedTouches[0];
    const dx = touch.clientX - flowStart.x, dy = touch.clientY - flowStart.y;
    if (Math.abs(dx) > 38 && Math.abs(dx) > Math.abs(dy) * 1.3) {
      const trace = window.AgentOS.getTrace();
      window.AgentOS.seekTo(trace.current + (dx < 0 ? 1 : -1));
    }
    flowStart = null;
  }, { passive: true });

  heroVisual.addEventListener('touchmove', event => {
    if (!motionAllowed()) return;
    const touch = event.touches[0], rect = heroVisual.getBoundingClientRect();
    heroVisual.style.setProperty('--hero-x', `${((touch.clientX - rect.left) / rect.width - .5) * 16}px`);
    heroVisual.style.setProperty('--hero-y', `${((touch.clientY - rect.top) / rect.height - .5) * 16}px`);
  }, { passive: true });
  heroVisual.addEventListener('touchend', () => {
    heroVisual.style.setProperty('--hero-x', '0px'); heroVisual.style.setProperty('--hero-y', '0px');
  }, { passive: true });
})();
