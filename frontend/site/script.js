const scenarios = {
  onboarding: {
    tag: 'HR / CROSS-TOOL',
    prompt: 'Prepare everything for a new teammate’s first day: account access, welcome message, calendar, and onboarding documents.',
    single: [
      ['action', 'AGENT', 'Read the request', 'Extract start date, manager, role, and required resources.', 'A single context holds the entire request and every subsequent tool result.'],
      ['action', 'AGENT', 'Create account access', 'Call the identity tool and assign the requested permissions.', 'This action changes a system before other dependencies are resolved.'],
      ['risk', 'AGENT', 'Draft the welcome message', 'Use the original role description while the access response adds new details.', 'Potential drift: the draft may refer to access that was not confirmed.'],
      ['action', 'AGENT', 'Schedule orientation', 'Find a slot and place the first-day meeting on the calendar.', 'The agent must reconcile time zones and the confirmed start date.'],
      ['check', 'AGENT', 'Review and send', 'Check the accumulated context and send a final summary.', 'Self-review is possible, but no independent verifier is assigned.']
    ],
    team: [
      ['action', 'PLANNER', 'Map the dependency chain', 'Separate access, documents, communication, and calendar work.', 'The planner defines completion criteria before delegation.'],
      ['action', 'ACCESS', 'Provision identity', 'Create access and return a structured confirmation to the planner.', 'The specialist reports exact granted permissions.'],
      ['action', 'CONTENT', 'Prepare the welcome pack', 'Assemble documents and draft a message using confirmed access.', 'The content step waits for the access result.'],
      ['action', 'CALENDAR', 'Schedule orientation', 'Choose a slot that matches the confirmed start date.', 'A specialist handles calendar constraints.'],
      ['check', 'VERIFIER', 'Cross-check outputs', 'Compare names, dates, permissions, links, and meeting details.', 'A separate role checks consistency across all tool results.'],
      ['check', 'PLANNER', 'Release the final summary', 'Resolve flagged discrepancies and present a traceable completion report.', 'The final response follows the verification gate.']
    ]
  },
  incident: {
    tag: 'OPS / TIME-SENSITIVE',
    prompt: 'A customer-facing service is degraded. Collect the signal, open an incident, alert the on-call team, and prepare a status update.',
    single: [
      ['action', 'AGENT', 'Inspect the alert', 'Read telemetry and infer the likely service impact.', 'The same agent must interpret and execute under time pressure.'],
      ['action', 'AGENT', 'Open an incident', 'Create an issue with the current severity assessment.', 'Severity may need revision as new evidence arrives.'],
      ['risk', 'AGENT', 'Notify the team', 'Send the initial escalation using the available context.', 'Potential drift: a notification can precede full impact confirmation.'],
      ['action', 'AGENT', 'Draft status', 'Write a customer update from the incident notes.', 'The update depends on the accuracy of earlier assessment.'],
      ['check', 'AGENT', 'Re-read the chain', 'Review the incident and messages for inconsistencies.', 'The agent checks its own interpretation.']
    ],
    team: [
      ['action', 'PLANNER', 'Set incident priorities', 'Define severity criteria, immediate actions, and communication order.', 'Governance establishes the escalation sequence.'],
      ['action', 'DIAGNOSE', 'Validate the signal', 'Cross-reference telemetry and identify affected services.', 'A specialist returns a bounded impact assessment.'],
      ['action', 'OPS', 'Open and route incident', 'Create the issue and page the appropriate on-call team.', 'Execution uses the validated severity.'],
      ['action', 'COMMS', 'Draft a status update', 'Write only confirmed impact and next-update timing.', 'The draft stays separate from operational changes.'],
      ['check', 'VERIFIER', 'Check claims against evidence', 'Compare the status draft, incident record, and telemetry.', 'Unsupported claims are flagged before release.'],
      ['check', 'PLANNER', 'Publish the handoff', 'Confirm owners, next steps, and a traceable communication summary.', 'The planner closes the loop after verification.']
    ]
  },
  review: {
    tag: 'FINANCE / DOCUMENT FLOW',
    prompt: 'Gather quarterly project updates, reconcile missing inputs, prepare a review brief, and schedule the stakeholder meeting.',
    single: [
      ['action', 'AGENT', 'Collect updates', 'Search issues, documents, and messages for project progress.', 'A long context accumulates many partially relevant records.'],
      ['risk', 'AGENT', 'Summarize the quarter', 'Combine updates into a first draft of the review brief.', 'Potential risk: an older update may be mistaken for the latest state.'],
      ['action', 'AGENT', 'Request missing inputs', 'Message owners about gaps in the evidence.', 'The agent tracks replies alongside the draft.'],
      ['action', 'AGENT', 'Schedule the review', 'Check availability and create the stakeholder meeting.', 'Scheduling depends on review readiness.'],
      ['check', 'AGENT', 'Finalize the brief', 'Re-read sources and submit the compiled summary.', 'Source verification remains a self-check.']
    ],
    team: [
      ['action', 'PLANNER', 'Define the evidence map', 'List required projects, owners, periods, and source documents.', 'The task begins with an explicit completeness checklist.'],
      ['action', 'RESEARCH', 'Gather current inputs', 'Collect and date-stamp the latest updates from each system.', 'The specialist records provenance for each claim.'],
      ['action', 'FOLLOW-UP', 'Resolve gaps', 'Request missing updates and track owner responses.', 'Open questions stay visible in shared state.'],
      ['action', 'WRITER', 'Compose the review brief', 'Draft findings linked to their source records.', 'Writing begins once the evidence map is ready.'],
      ['check', 'VERIFIER', 'Audit the brief', 'Inspect dates, citations, omissions, and unsupported conclusions.', 'Independent verification catches stale or missing evidence.'],
      ['check', 'PLANNER', 'Schedule and deliver', 'Set the meeting after review criteria pass and send the brief.', 'The final handoff follows a governance gate.']
    ]
  }
};

const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const state = { scenario: 'onboarding', mode: 'single', current: 0, timer: null, started: false };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const els = {
  prompt: $('#scenario-prompt'), tag: $('#scenario-tag'), counter: $('#stage-counter'),
  stream: $('#stage-stream'), steps: $('#metric-steps'), roles: $('#metric-roles'),
  gates: $('#metric-gates'), note: $('#trace-note p'), run: $('#run-button'), step: $('#step-button')
};

function stopTimer() { if (state.timer) clearInterval(state.timer); state.timer = null; }
function currentSteps() { return scenarios[state.scenario][state.mode]; }
function renderMetrics() {
  const done = currentSteps().slice(0, state.current);
  const total = currentSteps().length;
  els.counter.textContent = `STEP ${String(state.current).padStart(2, '0')} / ${String(total).padStart(2, '0')}`;
  els.steps.innerHTML = `${String(state.current).padStart(2, '0')} <small>/ ${String(total).padStart(2, '0')}</small>`;
  els.roles.textContent = String(new Set(done.map(item => item[1])).size || 1).padStart(2, '0');
  els.gates.textContent = String(done.filter(item => item[0] === 'check').length).padStart(2, '0');
  dispatchEvent(new CustomEvent('agentos:trace', { detail: {
    scenario: state.scenario, mode: state.mode, current: state.current,
    steps: currentSteps().map(([type, role, title]) => ({ type, role, title }))
  } }));
}
function resetRun() {
  stopTimer(); state.current = 0; state.started = false;
  els.stream.innerHTML = '<div class="idle-state"><span class="idle-glyph">◎</span><strong>Ready to trace this workflow.</strong><span>Start the run to see how the selected architecture handles each dependency.</span></div>';
  els.note.textContent = 'Watch where responsibility moves, and where a missing check could let an error travel downstream.';
  els.run.innerHTML = 'Run simulation <span>↗</span>';
  els.step.disabled = false;
  renderMetrics();
}
function setScenario(key) {
  state.scenario = key;
  $$('.scenario-button').forEach(button => { const active = button.dataset.scenario === key; button.classList.toggle('active', active); button.setAttribute('aria-pressed', active); });
  els.prompt.textContent = scenarios[key].prompt; els.tag.textContent = scenarios[key].tag; compareRange.value = '1'; resetRun(); renderCompare();
}
function setMode(mode) {
  state.mode = mode;
  $$('.mode-button').forEach(button => { const active = button.dataset.mode === mode; button.classList.toggle('active', active); button.setAttribute('aria-pressed', active); });
  resetRun();
}
function advance() {
  const steps = currentSteps();
  if (state.current >= steps.length) { stopTimer(); return; }
  if (!state.started) { state.started = true; els.stream.innerHTML = ''; }
  const [type, role, title, detail, note] = steps[state.current];
  const row = document.createElement('div');
  row.className = `trace-row ${type}`;
  const index = document.createElement('span'); index.className = 'trace-index'; index.textContent = String(state.current + 1).padStart(2, '0');
  const agent = document.createElement('span'); agent.className = 'trace-role'; agent.textContent = role;
  const content = document.createElement('span'); content.className = 'trace-content';
  const heading = document.createElement('strong'); heading.textContent = title;
  const description = document.createElement('small'); description.textContent = detail;
  content.append(heading, description);
  const flag = document.createElement('span'); flag.className = 'trace-type'; flag.textContent = type.toUpperCase();
  row.append(index, agent, content, flag); els.stream.append(row);
  state.current++; els.note.textContent = note; renderMetrics();
  els.stream.scrollTo({ top: els.stream.scrollHeight, behavior: reduceMotion ? 'instant' : 'smooth' });
  els.step.disabled = state.current >= steps.length;
  if (state.current >= steps.length) { stopTimer(); els.run.innerHTML = 'Run again <span>↺</span>'; }
  else els.run.innerHTML = state.timer ? 'Pause run <span>Ⅱ</span>' : 'Play all <span>→</span>';
}
function startAuto() {
  if (state.current >= currentSteps().length) resetRun();
  if (state.timer) { stopTimer(); els.run.innerHTML = 'Resume run <span>→</span>'; return; }
  advance();
  if (state.current < currentSteps().length) {
    state.timer = setInterval(advance, reduceMotion ? 450 : 1050);
    els.run.innerHTML = 'Pause run <span>Ⅱ</span>';
  }
}
function seekTo(count) {
  const target = Math.max(0, Math.min(currentSteps().length, Math.floor(count)));
  resetRun();
  for (let index = 0; index < target; index++) advance();
}
window.AgentOS = { seekTo, getTrace: () => ({
  scenario: state.scenario, mode: state.mode, current: state.current,
  steps: currentSteps().map(([type, role, title]) => ({ type, role, title }))
}) };

const comparisonNotes = {
  onboarding: [
    'Both begin with the request. AgentOS makes the dependency plan explicit before changing a tool.',
    'The baseline keeps access work in one context; AgentOS assigns it to a dedicated role with a structured return.',
    'The baseline reaches a possible context drift point while AgentOS prepares content from confirmed inputs.',
    'Both touch the calendar, but AgentOS keeps scheduling inside a bounded specialist task.',
    'The baseline self-checks; AgentOS introduces an independent verification gate.',
    'The baseline trace has ended. AgentOS still has a planner handoff after verification.'
  ],
  incident: [
    'The baseline inspects the alert directly; AgentOS first defines severity criteria and action order.',
    'The baseline opens an incident while AgentOS separately validates the signal and impact.',
    'The baseline can notify before confirmation; AgentOS routes the incident using validated severity.',
    'Both prepare communication, but AgentOS separates writing from incident operations.',
    'The baseline reviews its own chain; AgentOS checks public claims against the evidence.',
    'AgentOS has one final planner handoff to confirm owners and next actions.'
  ],
  review: [
    'The baseline searches across systems; AgentOS begins with an explicit evidence map.',
    'The baseline can summarize stale material; AgentOS dates and tracks source inputs.',
    'Both resolve gaps, but AgentOS keeps missing items visible in shared state.',
    'The baseline schedules while AgentOS drafts from the completed evidence map.',
    'The baseline self-checks; AgentOS audits the draft with a separate verifier.',
    'AgentOS schedules delivery only after the verification gate.'
  ]
};
const compareRange = $('#compare-step');
function renderCompare() {
  const index = Number(compareRange.value) - 1;
  const scenario = scenarios[state.scenario];
  $('#compare-scenario').textContent = {
    onboarding: 'NEW HIRE ONBOARDING', incident: 'INCIDENT RESPONSE', review: 'QUARTERLY REVIEW'
  }[state.scenario];
  $('#compare-count').textContent = `${String(index + 1).padStart(2, '0')} / 06`;
  compareRange.style.setProperty('--range-progress', `${index * 20}%`);
  for (const [mode, prefix] of [['single', 'compare-single'], ['team', 'compare-team']]) {
    const step = scenario[mode][index];
    const complete = !step;
    $(`#${prefix}-role`).textContent = complete ? 'TRACE COMPLETE' : step[1];
    $(`#${prefix}-title`).textContent = complete ? 'Work handed off.' : step[2];
    $(`#${prefix}-detail`).textContent = complete ? 'The single-agent trace has ended at this moment.' : step[3];
    $(`#${prefix}-type`).textContent = complete ? 'END OF TRACE' : step[0].toUpperCase();
    $(`#${prefix}-type`).dataset.type = complete ? 'complete' : step[0];
  }
  $('#compare-insight-text').textContent = comparisonNotes[state.scenario][index];
}
compareRange.addEventListener('input', renderCompare);

const ablationContent = {
  full: ['Does the complete hierarchy help?', 'Compare the full AgentOS system with the single-agent baseline on the same tasks, then remove one component at a time to isolate its contribution.'],
  planning: ['What happens without a plan?', 'Keep the specialists and tools, but remove the explicit task decomposition. Test whether missed dependencies or rework change.'],
  memory: ['What happens without shared state?', 'Keep the planner and specialists, but remove persistent handoff context. Test whether repeated work and inconsistent facts change.'],
  verification: ['What happens without an independent check?', 'Keep execution intact, but remove the verifier. Test whether errors reach the final handoff more often.'],
  governance: ['What happens without a release gate?', 'Keep the roles, but remove explicit approval and completion criteria. Test whether the system acts too early or leaves ownership unclear.']
};
$$('.ablation-button').forEach(button => button.addEventListener('click', () => {
  const selected = button.dataset.ablation;
  $$('.ablation-button').forEach(option => {
    const active = option === button;
    option.classList.toggle('active', active);
    option.setAttribute('aria-pressed', String(active));
  });
  $$('.ablation-nodes span').forEach(node => node.classList.toggle('removed', node.dataset.component === selected));
  $('#ablation-title').textContent = ablationContent[selected][0];
  $('#ablation-description').textContent = ablationContent[selected][1];
}));

$$('.scenario-button').forEach(button => button.addEventListener('click', () => setScenario(button.dataset.scenario)));
$$('.mode-button').forEach(button => button.addEventListener('click', () => setMode(button.dataset.mode)));
$('#reset-run').addEventListener('click', resetRun);
els.run.addEventListener('click', startAuto);
els.step.addEventListener('click', () => { stopTimer(); advance(); });
document.addEventListener('keydown', event => {
  if (event.code !== 'Space' || event.repeat || /button|a|input|textarea|select/i.test(document.activeElement?.tagName || '')) return;
  const lab = $('#lab').getBoundingClientRect();
  if (lab.top < innerHeight * .7 && lab.bottom > innerHeight * .3) { event.preventDefault(); stopTimer(); advance(); }
});

const menu = $('.menu-button');
menu.addEventListener('click', () => { const open = $('.nav').classList.toggle('menu-open'); menu.setAttribute('aria-expanded', String(open)); });
$$('.nav nav a').forEach(link => link.addEventListener('click', () => { $('.nav').classList.remove('menu-open'); menu.setAttribute('aria-expanded', 'false'); }));
const progress = $('.page-progress span');
function updateProgress() { const max = document.documentElement.scrollHeight - innerHeight; progress.style.width = `${max > 0 ? scrollY / max * 100 : 0}%`; }
addEventListener('scroll', updateProgress, { passive: true }); updateProgress();
if (reduceMotion) $$('.reveal').forEach(element => element.classList.add('visible'));
else {
  const observer = new IntersectionObserver((entries, observed) => entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('visible'); observed.unobserve(entry.target); } }), { threshold: .08 });
  $$('.reveal').forEach(element => observer.observe(element));
}
renderMetrics();
renderCompare();
