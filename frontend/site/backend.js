(() => {
  const $ = (id) => document.getElementById(id);
  const ui = {
    state: $('backend-state'), led: $('backend-led'), workspace: $('backend-workspace'),
    missions: $('live-missions'), active: $('live-active'), approvals: $('live-approvals'), artifacts: $('live-artifacts'),
    missionList: $('live-mission-list'), agents: $('live-agent-list'),
    engine: $('live-engine'), role: $('live-role'), model: $('live-model'), modelWrap: $('live-model-wrap'),
    session: $('live-session'), chat: $('live-chat-stream'), prompt: $('live-prompt'),
    send: $('live-send'), status: $('live-chat-status'), trace: $('live-trace'),
    traceEvents: $('live-trace-events'), traceCount: $('live-trace-count'),
    watcherList: $('live-watcher-list'), watcherCount: $('live-watcher-count'),
    // Left Live Feed elements
    tabTraceBtn: $('tab-trace-btn'), tabMissionsBtn: $('tab-missions-btn'),
    tracePanel: $('live-trace-panel'), missionsPanel: $('live-mission-panel'),
    traceFeedContainer: $('trace-feed-container'), traceTimeline: $('trace-timeline-list'),
    traceEmptyGuide: $('trace-empty-guide'), feedCount: $('live-feed-count'),
    feedStatusDot: $('feed-status-dot'), feedStatusLabel: $('feed-status-label'),
    feedMetaTools: $('feed-meta-tools'), feedMetaSteps: $('feed-meta-steps'), feedMetaRole: $('feed-meta-role'),
    // Smart suggestions elements
    suggChipsWrap: $('sugg-chips-wrap'), suggRolePill: $('sugg-role-pill'), suggRefreshBtn: $('sugg-refresh-btn'),
    // 3-Input Meal Planner elements
    groceryWrap: $('grocery-inputs-wrap'),
    groceryBreakfast: $('grocery-breakfast'),
    groceryLunch: $('grocery-lunch'),
    groceryDinner: $('grocery-dinner'),
    // Dish validation error modal
    dishErrorModal: $('dish-error-modal'),
    dishErrorItem: $('dish-error-item'),
    dishErrorDesc: $('dish-error-desc'),
    dishErrorClose: $('dish-error-close'),
    dishErrorBackdrop: $('dish-error-backdrop')
  };

  let connected = window.location.protocol.startsWith('http');
  let busy = false;
  let sessions = [];
  let activeSession = null;
  let currentTrace = [];
  let recognition = null;
  let toolsCount = 0;
  let stepsCount = 0;

  const ROLE_SUGGESTIONS = {
    project_architect: [
      { icon: "🚀", title: "Scaffold Student Management System", prompt: "Create a complete Student Management System in D:\\StudentManagementSystem using Python Flask, SQLite database, and clean HTML/CSS Bootstrap UI with CRUD routes." },
      { icon: "⚡", title: "FastAPI REST API with SQLite", prompt: "Scaffold a production-ready FastAPI REST API in D:\\FastAPIService with Pydantic v2 schemas, SQLite database, and auto-generated OpenAPI documentation." },
      { icon: "🎨", title: "Modern Analytics Dashboard", prompt: "Create a modern single-page web dashboard with responsive charts, dark mode, and sleek CSS glassmorphism in D:\\WebDashboard." },
      { icon: "📦", title: "Full-Stack Task Manager", prompt: "Build a complete Todo application in D:\\TaskManager with user auth models, SQLite persistence, and REST endpoints." }
    ],
    file_engineer: [
      { icon: "🔍", title: "Search Python Codebase", prompt: "Search all Python files in the current repository, summarize the module structure, and list all dependencies." },
      { icon: "📝", title: "Generate Comprehensive README", prompt: "Inspect the repository files and generate a comprehensive README.md with architecture and setup instructions." },
      { icon: "🔧", title: "Refactor Database Queries", prompt: "Inspect existing database queries in the project and optimize them with error handling and indexing." },
      { icon: "📁", title: "Audit Project Hierarchy", prompt: "List and audit all directories in this project and identify any redundant or misplaced files." }
    ],
    system_operator: [
      { icon: "🧮", title: "Open Calculator", prompt: "open calculator in my windows" },
      { icon: "📝", title: "Open Notepad", prompt: "open notepad in my windows" },
      { icon: "💻", title: "Check Python & Environment", prompt: "Run terminal commands to check installed Python version, pip packages, and available disk space." },
      { icon: "🧪", title: "Execute Unit Tests", prompt: "Run pytest or unittest on the repository and report all test results, failures, and warnings." },
      { icon: "📊", title: "Monitor System Processes", prompt: "Inspect active background tasks, system memory, and loopback network sockets." },
      { icon: "🌿", title: "Check Git Status & Log", prompt: "Check git status, unstaged diffs, and the latest commits in the workspace." }
    ],
    web_researcher: [
      { icon: "🌐", title: "Research Multi-Agent AI", prompt: "Perform web research on latest multi-agent LLM orchestration frameworks (like AutoGen, CrewAI, LangGraph) and compare their architectures." },
      { icon: "📈", title: "AI Model Benchmarks", prompt: "Search for current tech market updates and summarize top benchmarks for local AI models." },
      { icon: "📑", title: "Production FastAPI Docs", prompt: "Search and gather best practices for deploying FastAPI with SQLite and Uvicorn in production." }
    ],
    verifier: [
      { icon: "🛡️", title: "Verify Code Security", prompt: "Inspect the project files for security vulnerabilities, path traversal risks, and unhandled exceptions." },
      { icon: "🧪", title: "Syntax & Schema Validation", prompt: "Execute syntax verification and schema validation across all Python files in the workspace." },
      { icon: "📊", title: "Performance Audit", prompt: "Review API response handlers and suggest latency optimizations and caching strategies." }
    ],
    grocery_chef: [
      { icon: "🍳", title: "Daily Desi Meals", prompt: "Breakfast: Poha, Lunch: Dal Tadka with Steamed Rice, Dinner: Moong Dal Khichdi and Curd. Calculate all ingredients and add them to my Blinkit cart." },
      { icon: "🧀", title: "North Indian Feast", prompt: "Breakfast: Aloo Paratha with Curd, Lunch: Paneer Butter Masala with Roti, Dinner: Matar Paneer and Chapati. Calculate all ingredients and add them to my Blinkit cart." },
      { icon: "💪", title: "High-Protein Fitness Meals", prompt: "Breakfast: Bread Omelette, Lunch: Rajma Chawal with Salad, Dinner: Paneer Bhurji with Roti. Calculate all ingredients and add them to my Blinkit cart." },
      { icon: "🥥", title: "South Indian Special", prompt: "Breakfast: Idli Sambar, Lunch: Veg Pulao with Raita, Dinner: Dal Rice & Papad. Calculate all ingredients and add them to my Blinkit cart." },
      { icon: "🥣", title: "Light & Healthy Diet", prompt: "Breakfast: Oats with Milk & Banana, Lunch: Mix Veg with Roti, Dinner: Moong Dal Khichdi. Calculate all ingredients and add them to my Blinkit cart." },
      { icon: "🥘", title: "Weekend Family Feast", prompt: "Breakfast: Chole Bhature, Lunch: Shahi Paneer with Naan & Jeera Rice, Dinner: Palak Paneer with Roti. Calculate all ingredients and add them to my Blinkit cart." }
    ],
    auto: [
      { icon: "🛒", title: "Meals to Blinkit Cart", prompt: "Breakfast: Poha, Lunch: Paneer Butter Masala with Roti, Dinner: Dal Khichdi. Calculate ingredients and open Blinkit to add to cart." },
      { icon: "🧮", title: "Open Calculator", prompt: "open calculator in my windows" },
      { icon: "📝", title: "Open Notepad", prompt: "open notepad" },
      { icon: "🚀", title: "Build Student Management System", prompt: "Build a complete Student Management System in D:\\StudentManagementSystem using Flask, SQLite database, and clean HTML/CSS Bootstrap UI." },
      { icon: "🔍", title: "Inspect & Document Project", prompt: "Inspect the project files, check dependencies, and provide an architectural summary." },
      { icon: "🧪", title: "Run & Fix Tests", prompt: "Run the project test suite, diagnose any failures, and explain the fix." },
      { icon: "🌐", title: "Research Agent Architectures", prompt: "Research the differences between single-agent MCP and hierarchical multi-agent orchestration." }
    ]
  };

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = String(text);
    return element;
  }

  async function request(path, options = {}) {
    const response = await fetch(path, { ...options, headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers } });
    const type = response.headers.get('content-type') || '';
    if (!response.ok || !type.includes('application/json')) {
      let detail = `Request failed (${response.status})`;
      try { const body = await response.json(); detail = body.detail || body.error || detail; } catch {}
      throw new Error(detail);
    }
    return response.json();
  }
  const post = (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) });

  function setStatus(text, isError = false) {
    ui.status.textContent = text;
    ui.status.classList.toggle('error', isError);
  }

  function renderMissions(items = []) {
    ui.missionList.replaceChildren();
    if (!items.length) {
      ui.missionList.append(node('div', 'live-empty', 'No missions yet. Start one from the console.'));
      return;
    }
    items.slice(0, 5).forEach((mission, index) => {
      const row = node('div', 'live-mission-row');
      row.append(node('span', 'live-mission-no', String(index + 1).padStart(2, '0')));
      const info = node('div', 'live-mission-info');
      info.append(node('strong', '', mission.goal || 'Untitled mission'));
      info.append(node('small', '', `${mission.role_id || 'agent'} · ${new Date(mission.updated_at).toLocaleString()}`));
      row.append(info, node('span', `live-state state-${String(mission.status).toLowerCase()}`, String(mission.status || 'pending').replaceAll('_', ' ')));
      ui.missionList.append(row);
    });
  }

  function renderAgents(items = []) {
    ui.agents.replaceChildren();
    if (!items.length) { ui.agents.textContent = 'No agent activity yet'; return; }
    items.slice(0, 5).forEach((agent, index) => {
      const chip = node('span', 'agent-chip');
      chip.append(node('i', '', ['✳', '◈', '↗', '◇', '✦'][index]));
      chip.append(node('span', '', String(agent.agent_id).replaceAll('_', ' ')));
      ui.agents.append(chip);
    });
  }

  async function refreshStatus() {
    const results = await Promise.allSettled([request('/status'), request('/overview')]);
    if (results[0].status === 'fulfilled') {
      connected = true;
      const status = results[0].value;
      ui.state.textContent = `AGENTOS ONLINE / ${status.execution_mode === 'demo' ? 'DEMO' : 'LOCAL'}`;
      ui.led.classList.add('online');
      ui.workspace.textContent = `WORKSPACE / ${status.workspace_name || 'AGENTOS CORE'}`;
    } else {
      connected = false;
      ui.state.textContent = 'LOCAL BACKEND UNAVAILABLE';
      ui.led.classList.remove('online');
      setStatus('Open this site through your running backend at /app/ to use live features.', true);
    }
    if (ui.role.value === 'grocery_chef') {
      ui.send.disabled = busy;
    } else {
      ui.send.disabled = !connected || busy;
    }
    if (results[1].status === 'fulfilled') {
      const overview = results[1].value;
      ui.missions.textContent = overview.total_missions ?? '—';
      ui.active.textContent = overview.local_active_runs ?? '—';
      ui.approvals.textContent = overview.pending_approvals ?? '—';
      ui.artifacts.textContent = overview.total_artifacts ?? '—';
      renderMissions(overview.recent_reviews);
      renderAgents(overview.agent_activity);
    } else if (!connected) {
      ui.missionList.replaceChildren(node('div', 'live-empty', 'Live missions appear when the local backend is connected.'));
    }
  }

  async function loadEngines() {
    try {
      const engines = await request('/api/engines');
      ui.model.replaceChildren();
      (engines.ollama?.models || ['llama3.2']).forEach((name) => {
        const option = node('option', '', name);
        option.value = name;
        ui.model.append(option);
      });
    } catch {}
  }

  function renderMessages(messages) {
    ui.chat.replaceChildren();
    if (!messages?.length) {
      const welcome = node('div', 'chat-welcome');
      welcome.append(node('span', '', '✳'), node('strong', '', 'Give the system a direction.'), node('p', '', 'Ask a question, describe a task, or use your voice. Responses stream from the local backend.'));
      ui.chat.append(welcome);
      return;
    }
    messages.forEach((message) => {
      const contentEl = appendMessage(message.role, message.content, message.agent);
      if (message.role === 'assistant' && Array.isArray(message.suggestions) && message.suggestions.length) {
        appendMessageSuggestions(contentEl?.parentElement, message.suggestions);
      }
    });
  }

  function appendMessage(role, content = '', agent = '') {
    const article = node('article', `live-message ${role === 'user' ? 'from-user' : 'from-agent'}`);
    article.append(node('span', 'live-message-label', role === 'user' ? 'YOU / REQUEST' : `AGENTOS / ${(agent || 'SUPERVISOR').toUpperCase()}`));
    article.append(node('p', 'live-message-content', content));
    ui.chat.append(article);
    ui.chat.scrollTop = ui.chat.scrollHeight;
    return article.querySelector('.live-message-content');
  }

  function appendMessageSuggestions(container, suggestions = []) {
    if (!container || !suggestions.length) return;
    const box = node('div', 'msg-suggestions');
    box.append(node('span', 'msg-sugg-title', '💡 Recommended Next Actions:'));
    const pills = node('div', 'msg-sugg-pills');
    suggestions.forEach((text) => {
      const btn = node('button', 'msg-sugg-btn', `✨ ${text}`);
      btn.type = 'button';
      btn.addEventListener('click', () => {
        ui.prompt.value = text;
        ui.prompt.focus();
        ui.prompt.style.borderColor = 'var(--orange)';
        setTimeout(() => { ui.prompt.style.borderColor = ''; }, 600);
      });
      pills.append(btn);
    });
    box.append(pills);
    container.append(box);
  }

  function renderSessionOptions() {
    ui.session.replaceChildren();
    sessions.forEach((item) => {
      const option = node('option', '', item.title || 'New conversation');
      option.value = item.id;
      ui.session.append(option);
    });
    if (activeSession) ui.session.value = activeSession.id;
  }

  async function loadSessions() {
    try {
      const data = await request('/api/chat/sessions');
      sessions = Array.isArray(data.sessions) ? data.sessions : [];
      const id = activeSession?.id;
      activeSession = sessions.find((item) => item.id === id) || sessions[0] || null;
      renderSessionOptions();
      if (activeSession) {
        renderMessages(activeSession.messages);
        loadSessionTrace(activeSession);
      }
    } catch {}
  }

  function loadSessionTrace(session) {
    if (!session || !Array.isArray(session.messages)) return;
    const lastAsst = [...session.messages].reverse().find((m) => m.role === 'assistant' && Array.isArray(m.trace) && m.trace.length);
    if (lastAsst && lastAsst.trace.length) {
      ui.traceTimeline.replaceChildren();
      if (ui.traceEmptyGuide) ui.traceEmptyGuide.hidden = true;
      toolsCount = 0;
      stepsCount = 0;
      lastAsst.trace.forEach((ev) => renderTraceCard(ev, false));
      ui.feedMetaTools.textContent = String(toolsCount);
      ui.feedMetaSteps.textContent = String(stepsCount || 1);
      ui.feedCount.textContent = String(toolsCount).padStart(2, '0');
      ui.feedStatusDot.className = 'status-pulse-dot done';
      ui.feedStatusLabel.textContent = `✓ Recorded Run · ${toolsCount} tools used in ${stepsCount || 1} steps`;
    } else {
      ui.traceTimeline.replaceChildren();
      if (ui.traceEmptyGuide) ui.traceEmptyGuide.hidden = false;
      ui.feedMetaTools.textContent = '0';
      ui.feedMetaSteps.textContent = '0';
      ui.feedCount.textContent = '00';
      ui.feedStatusDot.className = 'status-pulse-dot idle';
      ui.feedStatusLabel.textContent = 'LLM Engine Ready · Waiting for task';
    }
  }

  async function createSession() {
    const id = `site_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    const now = new Date().toISOString();
    const session = { id, title: 'New conversation', createdAt: now, updatedAt: now, messages: [] };
    await post('/api/chat/sessions', session);
    sessions.unshift(session);
    activeSession = session;
    renderSessionOptions();
    renderMessages([]);
    loadSessionTrace(session);
    return session;
  }

  // Render a trace card in the left timeline
  function renderTraceCard(event, isLive = true) {
    if (!ui.traceTimeline) return;
    if (ui.traceEmptyGuide) ui.traceEmptyGuide.hidden = true;

    const step = event.step || stepsCount || 1;
    stepsCount = Math.max(stepsCount, step);

    if (event.type === 'thought') {
      const card = node('div', 'trace-card trace-card-thought');
      const head = node('div', 'trace-card-head');
      const tag = node('span', 'trace-card-tag');
      tag.innerHTML = `<i>🧠</i> STEP ${String(step).padStart(2, '0')} · MODEL REASONING`;
      const status = node('span', 'trace-card-status info', 'THINKING');
      head.append(tag, status);
      const body = node('div', 'trace-card-body', event.text || event.detail || '');
      card.append(head, body);
      ui.traceTimeline.append(card);

      if (isLive) {
        ui.feedStatusDot.className = 'status-pulse-dot thinking';
        ui.feedStatusLabel.textContent = `● LLM Thinking · Step ${step}`;
        ui.feedMetaSteps.textContent = String(stepsCount);
      }
    } else if (event.type === 'tool_call') {
      toolsCount++;
      const card = node('div', 'trace-card trace-card-tool');
      card.dataset.toolCall = `${event.tool}_${step}`;
      const head = node('div', 'trace-card-head');
      const tag = node('span', 'trace-card-tag');
      tag.innerHTML = `<i>⚙</i> STEP ${String(step).padStart(2, '0')} · TOOL CALL`;
      const status = node('span', 'trace-card-status running', 'EXECUTING ⏳');
      head.append(tag, status);
      const body = node('div', 'trace-card-body');
      const title = node('div', 'trace-tool-title');
      title.innerHTML = `Action: <code>${event.tool}</code>`;
      body.append(title);

      if (event.args && typeof event.args === 'object' && Object.keys(event.args).length) {
        const argsBox = node('pre', 'trace-args-box');
        let formattedArgs = '';
        if (event.args.breakfast) formattedArgs += `🍳 Breakfast: ${event.args.breakfast}\n`;
        if (event.args.lunch) formattedArgs += `🍲 Lunch: ${event.args.lunch}\n`;
        if (event.args.dinner) formattedArgs += `🍛 Dinner: ${event.args.dinner}\n`;
        if (event.args.servings) formattedArgs += `👥 Servings: ${event.args.servings}\n`;
        if (event.args.app_name) formattedArgs += `App: ${event.args.app_name}\n`;
        if (event.args.path) formattedArgs += `File: ${event.args.path}\n`;
        if (event.args.command) formattedArgs += `Command: ${event.args.command}\n`;
        if (event.args.query) formattedArgs += `Query: ${event.args.query}\n`;
        formattedArgs += JSON.stringify(event.args, null, 2);
        argsBox.textContent = formattedArgs.trim();
        body.append(argsBox);
      }
      card.append(head, body);
      ui.traceTimeline.append(card);

      if (isLive) {
        ui.feedStatusDot.className = 'status-pulse-dot running';
        ui.feedStatusLabel.textContent = `⚙ Tool Call: ${event.tool} (Step ${step})`;
        ui.feedMetaTools.textContent = String(toolsCount);
        ui.feedCount.textContent = String(toolsCount).padStart(2, '0');
        ui.feedMetaSteps.textContent = String(stepsCount);
      }
    } else if (event.type === 'tool_result') {
      // Find earlier tool card and mark completed
      const prev = ui.traceTimeline.querySelector(`[data-tool-call="${event.tool}_${step}"] .trace-card-status`);
      if (prev) {
        prev.className = 'trace-card-status done';
        prev.textContent = 'DONE ✓';
      }

      const card = node('div', 'trace-card trace-card-result');
      const head = node('div', 'trace-card-head');
      const tag = node('span', 'trace-card-tag');
      tag.innerHTML = `<i>✅</i> STEP ${String(step).padStart(2, '0')} · RESULT (${event.tool})`;
      const status = node('span', 'trace-card-status done', 'SUCCESS');
      head.append(tag, status);
      const body = node('div', 'trace-card-body');
      const resBox = node('pre', 'trace-result-box', event.snippet || event.result_snippet || 'Action completed successfully.');
      body.append(resBox);
      card.append(head, body);
      ui.traceTimeline.append(card);

      if (isLive) {
        ui.feedStatusDot.className = 'status-pulse-dot done';
        ui.feedStatusLabel.textContent = `✓ Tool Completed: ${event.tool} (Step ${step})`;
      }
    } else if (event.type === 'approval_notice') {
      const card = node('div', 'trace-card trace-card-approval');
      const head = node('div', 'trace-card-head');
      const tag = node('span', 'trace-card-tag');
      tag.innerHTML = `<i>⚠️</i> STEP ${String(step).padStart(2, '0')} · RISK ASSESSMENT`;
      const status = node('span', 'trace-card-status running', (event.risk || 'NOTICE').toUpperCase());
      head.append(tag, status);
      const body = node('div', 'trace-card-body', `Tool: ${event.tool} · Reason: ${event.reason || 'Requires operator awareness.'}`);
      card.append(head, body);
      ui.traceTimeline.append(card);
    }

    if (ui.traceFeedContainer) {
      ui.traceFeedContainer.scrollTop = ui.traceFeedContainer.scrollHeight;
    }
  }

  function addTrace(event) {
    const item = {
      type: event.type,
      step: event.step || stepsCount || 1,
      tool: event.tool || '',
      args: event.args || null,
      text: event.text || event.tool || event.reason || '',
      snippet: event.snippet || ''
    };
    currentTrace.push(item);

    // Update compact console trace
    ui.trace.hidden = false;
    ui.traceCount.textContent = String(currentTrace.length).padStart(2, '0');
    const row = node('div', 'trace-event');
    row.append(node('span', '', event.type.replaceAll('_', ' ').toUpperCase()), node('strong', '', item.text), node('small', '', item.snippet || ''));
    ui.traceEvents.append(row);

    // Render in main left timeline
    renderTraceCard(event, true);
  }

  function renderSmartSuggestions(customList = null) {
    if (!ui.suggChipsWrap) return;
    ui.suggChipsWrap.replaceChildren();
    const currentRole = ui.role.value || 'auto';
    if (ui.suggRolePill) {
      ui.suggRolePill.textContent = (customList ? 'RECOMMENDED NEXT ACTIONS' : (ui.role.options[ui.role.selectedIndex]?.text || currentRole)).toUpperCase();
    }
    const list = customList || ROLE_SUGGESTIONS[currentRole] || ROLE_SUGGESTIONS.auto;
    list.forEach((item) => {
      const chip = node('button', 'sugg-chip');
      chip.type = 'button';
      const promptText = typeof item === 'string' ? item : item.prompt;
      const labelText = typeof item === 'string' ? `✨ ${item}` : `${item.icon || '✳'} ${item.title || item.prompt}`;
      chip.textContent = labelText;
      chip.title = promptText;
      chip.addEventListener('click', () => {
        const isGroceryPrompt = /breakfast|lunch|dinner|blinkit|grocery|groceries|poha|paratha|khichdi|chawal|paneer|curry/i.test(promptText);
        if (isGroceryPrompt && ui.role.value !== 'grocery_chef') {
          ui.role.value = 'grocery_chef';
          updateRoleUI();
          if (ui.feedMetaRole) ui.feedMetaRole.textContent = 'GROCERY & BLINKIT CHEF';
        }

        if (ui.role.value === 'grocery_chef') {
          const bMatch = promptText.match(/Breakfast:\s*(.+?)(?=,\s*Lunch:|$|;)/i);
          const lMatch = promptText.match(/Lunch:\s*(.+?)(?=,\s*Dinner:|$|;)/i);
          const dMatch = promptText.match(/Dinner:\s*(.+?)(?=\.|\s*Calculate|$|;)/i);
          if (bMatch && ui.groceryBreakfast) ui.groceryBreakfast.value = bMatch[1].trim();
          if (lMatch && ui.groceryLunch) ui.groceryLunch.value = lMatch[1].trim();
          if (dMatch && ui.groceryDinner) ui.groceryDinner.value = dMatch[1].trim();
          if (!bMatch && !lMatch && !dMatch && ui.groceryBreakfast) {
            ui.groceryBreakfast.value = promptText;
          }
          [ui.groceryBreakfast, ui.groceryLunch, ui.groceryDinner].forEach(inp => {
            if (inp && inp.value) {
              inp.style.borderColor = '#28c946';
              inp.style.backgroundColor = 'rgba(12, 131, 31, 0.22)';
              setTimeout(() => { inp.style.borderColor = ''; inp.style.backgroundColor = ''; }, 650);
            }
          });
          if (ui.groceryBreakfast) ui.groceryBreakfast.focus();
        } else {
          ui.prompt.value = promptText;
          ui.prompt.focus();
          ui.prompt.style.borderColor = 'var(--orange)';
          setTimeout(() => { ui.prompt.style.borderColor = ''; }, 600);
        }
      });
      ui.suggChipsWrap.append(chip);
    });
  }

  // ==================== FOOD EDIBILITY VALIDATION ENGINE ====================
  const NON_FOOD_KEYWORDS = new Set([
    'car', 'cars', 'bike', 'motorcycle', 'scooter', 'cycle', 'bus', 'truck', 'plane', 'aeroplane', 'train',
    'mobile', 'phone', 'smartphone', 'laptop', 'computer', 'pc', 'monitor', 'keyboard', 'mouse', 'cpu', 'gpu',
    'tv', 'television', 'charger', 'cable', 'wire', 'battery', 'screen', 'camera', 'headphone', 'headphones',
    'table', 'chair', 'bed', 'sofa', 'almirah', 'cupboard', 'desk', 'fan', 'light', 'bulb', 'tube', 'door', 'window',
    'wall', 'floor', 'roof', 'mirror', 'curtain', 'carpet', 'lock', 'key',
    'pen', 'pencil', 'paper', 'book', 'notebook', 'eraser', 'sharpener', 'bag', 'backpack', 'wallet', 'purse',
    'knife', 'scissors', 'hammer', 'nail', 'screw', 'tape', 'glue',
    'iron', 'steel', 'plastic', 'wood', 'stone', 'rock', 'brick', 'cement', 'sand', 'mud', 'dirt', 'dust', 'glass',
    'cloth', 'clothes', 'clothing', 'shirt', 'tshirt', 'pant', 'pants', 'jeans', 'shoes', 'shoe', 'socks', 'jacket',
    'hat', 'cap', 'leather', 'rubber',
    'soap', 'detergent', 'shampoo', 'conditioner', 'perfume', 'deodorant', 'petrol', 'diesel', 'kerosene', 'paint',
    'poison', 'acid', 'chemical', 'medicine', 'medicines', 'tablet', 'tablets', 'pill', 'pills', 'injection',
    'house', 'building', 'room', 'road', 'street', 'bridge',
    'code', 'coding', 'program', 'software', 'hardware', 'bug', 'error', 'script', 'server', 'database', 'terminal',
    'python', 'javascript', 'html', 'css', 'git', 'github', 'file', 'files', 'folder', 'virus', 'trojan'
  ]);

  const FOOD_TERMS_REGEX = new RegExp(
    '\\b(' + [
      'poha', 'upma', 'idli', 'dosa', 'vada', 'paratha', 'parantha', 'roti', 'chapati', 'phulka', 'naan', 'kulcha',
      'puri', 'poori', 'bhature', 'bhatura', 'rice', 'chawal', 'biryani', 'pulao', 'khichdi', 'atta', 'sooji', 'besan',
      'maida', 'oats', 'oatmeal', 'bread', 'toast', 'sandwich', 'pancake', 'waffle', 'cereal', 'cornflakes', 'muesli',
      'noodles', 'pasta', 'macaroni', 'spaghetti', 'maggi', 'chowmein', 'burger', 'pizza', 'roll', 'wrap', 'frankie',
      'dal', 'daal', 'tadka', 'makhani', 'fry', 'rajma', 'chole', 'chhole', 'chana', 'kadhi', 'sambar', 'rasam',
      'curry', 'gravy', 'sabzi', 'sabji', 'saag', 'paneer', 'kofta', 'bhurji', 'bharta', 'korma', 'jalfrezi',
      'aloo', 'alu', 'potato', 'gobi', 'gobhi', 'cauliflower', 'cabbage', 'matar', 'mutter', 'peas', 'palak', 'spinach',
      'methi', 'bhindi', 'okra', 'ladyfinger', 'baingan', 'brinjal', 'eggplant', 'karela', 'lauki', 'ghiya', 'tinda',
      'tori', 'capsicum', 'shimla', 'mirch', 'chilli', 'pepper', 'corn', 'mushroom', 'soya', 'chaap', 'beans',
      'carrot', 'gajar', 'radish', 'mooli', 'beetroot', 'cucumber', 'kheera', 'tomato', 'tamatar', 'onion', 'pyaz',
      'ginger', 'adrak', 'garlic', 'lahsun', 'lemon', 'nimbu', 'coriander', 'dhaniya', 'mint', 'pudina',
      'chicken', 'mutton', 'egg', 'eggs', 'anda', 'fish', 'prawn', 'prawns', 'keema', 'tikka', 'kabab', 'kebab', 'meat',
      'milk', 'dahi', 'curd', 'yogurt', 'butter', 'makhan', 'ghee', 'cheese', 'cream', 'malai', 'lassi', 'chaas', 'buttermilk',
      'chilla', 'cheela', 'dhokla', 'thepla', 'khandvi', 'samosa', 'kachori', 'pakoda', 'pakora', 'cutlet', 'omelette', 'omelet',
      'tea', 'chai', 'coffee', 'juice', 'shake', 'smoothie', 'soup', 'halwa', 'kheer', 'gulab jamun', 'rasgulla', 'jalebi',
      'ice cream', 'custard', 'pudding', 'cake', 'pastry', 'brownie', 'biscuit', 'cookie',
      'apple', 'banana', 'mango', 'orange', 'grapes', 'papaya', 'watermelon', 'pineapple', 'guava', 'strawberry', 'fruit', 'fruits',
      'salad', 'raita', 'chutney', 'pickle', 'achar', 'sauce', 'snack', 'snacks', 'food', 'meal', 'khana', 'dish', 'dishes', 'thali'
    ].join('|') + ')\\b',
    'i'
  );

  function validateEdibleDish(mealCategory, text) {
    const raw = (text || '').trim();
    if (!raw) return { valid: true };

    const lower = raw.toLowerCase();
    const words = lower.split(/[\s,+/&;]+/).filter(Boolean);

    // 1. Check for forbidden non-food keywords
    for (const w of words) {
      const cleanW = w.replace(/[^a-z0-9]/g, '');
      if (NON_FOOD_KEYWORDS.has(cleanW)) {
        return {
          valid: false,
          invalidItem: cleanW,
          meal: mealCategory,
          reason: `"${cleanW}" is not an edible food item.`
        };
      }
    }

    // 2. Check for gibberish (word >= 4 letters without vowel, or repeated letters)
    for (const w of words) {
      const cleanW = w.replace(/[^a-z]/g, '');
      if (cleanW.length >= 4 && !/[aeiouy]/.test(cleanW)) {
        return {
          valid: false,
          invalidItem: cleanW,
          meal: mealCategory,
          reason: `"${cleanW}" appears to be random letters, not a food dish.`
        };
      }
      if (/([a-z])\1{3,}/.test(cleanW)) {
        return {
          valid: false,
          invalidItem: cleanW,
          meal: mealCategory,
          reason: `"${cleanW}" contains invalid repeated characters.`
        };
      }
    }

    // 3. Ensure input has at least one recognized food term or dish concept
    if (!FOOD_TERMS_REGEX.test(lower)) {
      return {
        valid: false,
        invalidItem: raw,
        meal: mealCategory,
        reason: `"${raw}" does not match any recognized food or edible dish.`
      };
    }

    return { valid: true };
  }

  function showDishError(invalidItem, customDesc) {
    if (!ui.dishErrorModal) {
      alert(`Invalid Dish: ${invalidItem}`);
      return;
    }
    if (ui.dishErrorItem) ui.dishErrorItem.textContent = invalidItem ? `"${invalidItem}"` : 'Input';
    if (ui.dishErrorDesc) {
      ui.dishErrorDesc.innerHTML = customDesc || `The entered item <strong class="dish-error-highlight">"${invalidItem}"</strong> does not match any known edible food dish! Please check your spelling or enter a real dish.`;
    }
    ui.dishErrorModal.hidden = false;
    ui.dishErrorModal.style.display = 'flex';
  }

  function hideDishError() {
    if (ui.dishErrorModal) {
      ui.dishErrorModal.hidden = true;
      ui.dishErrorModal.style.display = 'none';
    }
  }

  function updateRoleUI() {
    const isGrocery = ui.role.value === 'grocery_chef';
    const form = $('live-chat-form');
    if (form) {
      form.classList.toggle('grocery-mode', isGrocery);
      form.style.flexDirection = isGrocery ? 'column' : '';
    }
    if (ui.groceryWrap) {
      ui.groceryWrap.hidden = !isGrocery;
      ui.groceryWrap.style.display = isGrocery ? 'flex' : 'none';
      ui.groceryWrap.style.flexDirection = isGrocery ? 'column' : '';
    }
    ui.prompt.hidden = isGrocery;
    ui.prompt.style.display = isGrocery ? 'none' : '';
    const mic = $('live-mic');
    if (mic) {
      mic.hidden = isGrocery;
      mic.style.display = isGrocery ? 'none' : '';
    }
    if (isGrocery) {
      ui.send.disabled = false;
      ui.send.innerHTML = '⚡ ORDER ON BLINKIT 🛒 ➔';
      if (ui.groceryBreakfast) {
        setTimeout(() => ui.groceryBreakfast.focus(), 80);
      }
    } else {
      ui.send.disabled = !connected || busy;
      ui.send.innerHTML = 'SEND ↗';
    }
  }

  async function sendMessage(message) {
    if (!connected || busy || !message.trim()) return;
    busy = true;
    ui.send.disabled = true;
    setStatus('Connecting to agent stream…');

    // Automatically switch left panel to Live Tools tab
    if (ui.tabTraceBtn) ui.tabTraceBtn.click();

    // Reset execution counters and timeline
    toolsCount = 0;
    stepsCount = 0;
    currentTrace = [];
    ui.traceTimeline.replaceChildren();
    if (ui.traceEmptyGuide) ui.traceEmptyGuide.hidden = true;
    ui.feedMetaTools.textContent = '0';
    ui.feedMetaSteps.textContent = '0';
    ui.feedCount.textContent = '00';
    ui.feedMetaRole.textContent = (ui.role.value === 'auto' ? 'SUPERVISOR' : ui.role.value).toUpperCase();
    ui.feedStatusDot.className = 'status-pulse-dot thinking';
    ui.feedStatusLabel.textContent = '● LLM Initializing · Planning agent actions...';

    try {
      const session = activeSession || await createSession();
      const history = (session.messages || []).slice(-12).map(({ role, content }) => ({ role, content }));
      session.messages = [...(session.messages || []), { id: String(Date.now()), role: 'user', content: message, timestamp: new Date().toLocaleTimeString() }];
      if (session.title === 'New conversation') { session.title = message.slice(0, 38); renderSessionOptions(); }
      appendMessage('user', message);
      const output = appendMessage('assistant', '', ui.role.value === 'auto' ? 'supervisor' : ui.role.value);
      ui.prompt.value = '';
      ui.trace.hidden = true;
      ui.traceEvents.replaceChildren();

      const response = await fetch('/api/chat/stream', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.id, message, role: ui.role.value === 'auto' ? null : ui.role.value, engine: ui.engine.value, ollama_model: ui.model.value || 'llama3.2', history })
      });
      if (!response.ok || !response.body) throw new Error(`Stream failed (${response.status})`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let reply = '';
      let doneEvent = false;
      let returnedSuggestions = [];

      function process(block) {
        for (const line of block.split(/\r?\n/)) {
          if (!line.startsWith('data:')) continue;
          let event;
          try { event = JSON.parse(line.slice(5).trim()); } catch { continue; }
          if (event.type === 'delta') {
            reply += event.text || '';
            output.textContent = reply;
          } else if (event.type === 'done') {
            doneEvent = true;
            reply = event.reply || reply;
            output.textContent = reply;
            if (Array.isArray(event.suggestions) && event.suggestions.length) {
              returnedSuggestions = event.suggestions;
            }
          } else if (event.type === 'error') {
            throw new Error(event.error || 'Agent stream error');
          } else if (['thought', 'tool_call', 'tool_result', 'approval_notice'].includes(event.type)) {
            addTrace(event);
          }
          ui.chat.scrollTop = ui.chat.scrollHeight;
        }
      }

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() || '';
        blocks.forEach(process);
      }
      if (buffer.trim()) process(buffer);
      if (!doneEvent && !reply) throw new Error('The stream ended without a response.');

      // Final completion summary card in timeline
      const summaryCard = node('div', 'trace-card-summary');
      const sumIcon = node('span', 'sum-icon', '🎉');
      const sumInfo = node('div');
      sumInfo.append(
        node('strong', '', 'Task Execution Complete'),
        node('p', '', `All actions finished. ${toolsCount} tool calls executed across ${stepsCount || 1} steps.`)
      );
      summaryCard.append(sumIcon, sumInfo);
      ui.traceTimeline.append(summaryCard);
      if (ui.traceFeedContainer) ui.traceFeedContainer.scrollTop = ui.traceFeedContainer.scrollHeight;

      ui.feedStatusDot.className = 'status-pulse-dot done';
      ui.feedStatusLabel.textContent = `✓ Execution Finished · ${toolsCount} tools used in ${stepsCount || 1} steps`;

      // Save message with trace and suggestions
      session.messages.push({
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: reply,
        agent: 'supervisor',
        timestamp: new Date().toLocaleTimeString(),
        trace: currentTrace,
        suggestions: returnedSuggestions
      });

      // If grocery request, render prominent 3D Blinkit Cart link card
      if (ui.role.value === 'grocery_chef' || reply.toLowerCase().includes('blinkit') || message.toLowerCase().includes('blinkit')) {
        const cartCard = node('div', 'blinkit-chat-action-card');
        cartCard.innerHTML = `
          <div class="cart-card-header">
            <span class="cart-card-icon">🛒</span>
            <div class="cart-card-meta">
              <strong>Blinkit Cart Drawer Ready</strong>
              <small>Google Chrome has launched with your cart drawer open and visible without login.</small>
            </div>
          </div>
          <a href="https://blinkit.com/cart" target="_blank" rel="noopener noreferrer" class="blinkit-direct-link-btn">
            ⚡ OPEN BLINKIT IN NEW TAB ↗
          </a>
        `;
        if (output && output.parentElement) {
          output.parentElement.append(cartCard);
        }
      }

      // Update smart prompt suggestions with contextual recommendations
      if (returnedSuggestions.length) {
        renderSmartSuggestions(returnedSuggestions);
        appendMessageSuggestions(output.parentElement, returnedSuggestions);
      }

      setStatus('Response complete.');
      void refreshStatus();
      void loadSessions();
    } catch (error) {
      setStatus(error.message || 'Could not stream a response.', true);
      ui.feedStatusDot.className = 'status-pulse-dot running';
      ui.feedStatusLabel.textContent = `⚠️ Error: ${error.message}`;
      const last = ui.chat.lastElementChild?.querySelector('.live-message-content');
      if (last && !last.textContent) last.textContent = 'The response could not be completed. Please try again.';
    } finally {
      busy = false;
      if (ui.role.value === 'grocery_chef') {
        ui.send.disabled = false;
        ui.send.innerHTML = '⚡ ORDER ON BLINKIT 🛒 ➔';
      } else {
        ui.send.disabled = !connected;
        ui.send.innerHTML = 'SEND ↗';
      }
    }
  }

  async function loadWatchers() {
    try {
      const data = await request('/api/watchers');
      const watchers = data.watchers || [];
      ui.watcherCount.textContent = String(watchers.filter((item) => item.enabled).length).padStart(2, '0');
      ui.watcherList.replaceChildren();
      if (!watchers.length) ui.watcherList.append(node('p', 'live-empty', 'No watchers yet.'));
      watchers.forEach((watcher) => {
        const row = node('div', 'watcher-row');
        const info = node('div');
        info.append(node('strong', '', watcher.name), node('small', '', `${watcher.command} · every ${watcher.interval_seconds}s`));
        const buttons = node('div', 'watcher-actions');
        for (const [text, action] of [['RUN', 'run'], [watcher.enabled ? 'PAUSE' : 'RESUME', 'toggle'], ['DELETE', 'delete']]) {
          const button = node('button', '', text);
          button.type = 'button';
          button.addEventListener('click', async () => {
            try {
              if (action === 'delete') await request(`/api/watchers/${encodeURIComponent(watcher.id)}`, { method: 'DELETE' });
              else await request(`/api/watchers/${encodeURIComponent(watcher.id)}/${action}`, { method: 'POST' });
              setStatus(`Watcher ${action} complete.`);
              await loadWatchers();
            } catch (error) { setStatus(error.message, true); }
          });
          buttons.append(button);
        }
        row.append(info, buttons);
        ui.watcherList.append(row);
      });
    } catch {}
  }

  // Left Feed Tab Handlers
  if (ui.tabTraceBtn && ui.tabMissionsBtn) {
    ui.tabTraceBtn.addEventListener('click', () => {
      ui.tabTraceBtn.classList.add('active');
      ui.tabMissionsBtn.classList.remove('active');
      ui.tracePanel.hidden = false;
      ui.missionsPanel.hidden = true;
    });
    ui.tabMissionsBtn.addEventListener('click', () => {
      ui.tabMissionsBtn.classList.add('active');
      ui.tabTraceBtn.classList.remove('active');
      ui.missionsPanel.hidden = false;
      ui.tracePanel.hidden = true;
    });
  }

  // Smart suggestions refresh button
  if (ui.suggRefreshBtn) {
    ui.suggRefreshBtn.addEventListener('click', () => {
      renderSmartSuggestions();
    });
  }

  // Role change updates smart suggestions & status bar role badge
  ui.role.addEventListener('change', () => {
    const roleText = ui.role.options[ui.role.selectedIndex]?.text || ui.role.value;
    if (ui.feedMetaRole) ui.feedMetaRole.textContent = roleText.toUpperCase();
    renderSmartSuggestions();
    updateRoleUI();
  });

  function handleFormSubmit() {
    if (ui.role.value === 'grocery_chef') {
      const b = (ui.groceryBreakfast?.value || '').trim();
      const l = (ui.groceryLunch?.value || '').trim();
      const d = (ui.groceryDinner?.value || '').trim();

      // Rule 1: At least one box must be filled!
      if (!b && !l && !d) {
        showDishError(
          'All 3 Meal Boxes Empty',
          'Please enter at least one dish for <strong>Breakfast</strong>, <strong>Lunch</strong>, or <strong>Dinner</strong> before ordering on Blinkit!'
        );
        return;
      }

      // Rule 2: Food / Edibility validation on each filled box
      if (b) {
        const valB = validateEdibleDish('Breakfast', b);
        if (!valB.valid) {
          showDishError(valB.invalidItem, `In <strong>Breakfast</strong>, "${valB.invalidItem}" does not match any known edible food dish! Please enter a real edible dish.`);
          return;
        }
      }
      if (l) {
        const valL = validateEdibleDish('Lunch', l);
        if (!valL.valid) {
          showDishError(valL.invalidItem, `In <strong>Lunch</strong>, "${valL.invalidItem}" does not match any known edible food dish! Please enter a real edible dish.`);
          return;
        }
      }
      if (d) {
        const valD = validateEdibleDish('Dinner', d);
        if (!valD.valid) {
          showDishError(valD.invalidItem, `In <strong>Dinner</strong>, "${valD.invalidItem}" does not match any known edible food dish! Please enter a real edible dish.`);
          return;
        }
      }

      // Construct synthesized prompt
      const parts = [];
      if (b) parts.push(`Breakfast: ${b}`);
      if (l) parts.push(`Lunch: ${l}`);
      if (d) parts.push(`Dinner: ${d}`);
      const prompt = `${parts.join(', ')}. Send all dishes to Groq to find all the main ingredients necessary to make their recipes (e.g. Aloo Paratha -> Aloo and Atta; Palak Paneer -> Palak and Paneer), create a deduplicated set of main ingredients, open Chromium with location permissions for Blinkit, search each ingredient one by one and add only 1 item to the cart, and open the cart drawer without login.`;
      console.log('[AgentOS] Sending grocery prompt to AI agent:', prompt);
      setStatus('Sending dishes to Groq & opening Chromium Blinkit cart...');
      ui.send.disabled = true;
      ui.send.innerHTML = '⚡ PREPARING BLINKIT CART... ⏳';
      void sendMessage(prompt);
    } else {
      const val = (ui.prompt?.value || '').trim();
      if (!val) return;
      void sendMessage(val);
    }
  }

  $('backend-refresh').addEventListener('click', () => { void refreshStatus(); void loadEngines(); void loadWatchers(); });

  let submitBusy = false;
  function triggerSubmit() {
    if (submitBusy) return;
    submitBusy = true;
    setTimeout(() => { submitBusy = false; }, 350);
    handleFormSubmit();
  }

  $('live-chat-form').addEventListener('submit', (event) => { event.preventDefault(); triggerSubmit(); });
  ui.send.addEventListener('click', (event) => { event.preventDefault(); triggerSubmit(); });
  ui.send.addEventListener('pointerup', () => { triggerSubmit(); });
  ui.prompt.addEventListener('keydown', (event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); triggerSubmit(); } });

  // Keydown Enter on grocery meal inputs
  [ui.groceryBreakfast, ui.groceryLunch, ui.groceryDinner].forEach((input) => {
    if (input) {
      input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
          event.preventDefault();
          triggerSubmit();
        }
      });
    }
  });

  // Connect .meal-pill click handlers
  document.querySelectorAll('.meal-pill').forEach((pill) => {
    pill.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const food = pill.getAttribute('data-food') || pill.textContent.replace(/[^\w\s&]/gi, '').trim();
      const parentChips = pill.closest('.meal-quick-chips');
      const targetId = parentChips ? parentChips.getAttribute('data-target') : null;
      const targetInput = targetId ? $(targetId) : null;
      if (targetInput) {
        if (!targetInput.value.trim()) {
          targetInput.value = food;
        } else {
          if (!targetInput.value.includes(food)) {
            targetInput.value += `, ${food}`;
          }
        }
        targetInput.focus();
        pill.classList.add('selected');
        setTimeout(() => pill.classList.remove('selected'), 350);
      }
    });
  });

  // Connect clear all button
  const clearBtn = $('grocery-clear-btn');
  if (clearBtn) {
    clearBtn.addEventListener('click', (e) => {
      e.preventDefault();
      if (ui.groceryBreakfast) ui.groceryBreakfast.value = '';
      if (ui.groceryLunch) ui.groceryLunch.value = '';
      if (ui.groceryDinner) ui.groceryDinner.value = '';
      if (ui.groceryBreakfast) ui.groceryBreakfast.focus();
    });
  }

  // Dish Error Modal close handlers
  if (ui.dishErrorClose) ui.dishErrorClose.addEventListener('click', hideDishError);
  if (ui.dishErrorBackdrop) ui.dishErrorBackdrop.addEventListener('click', hideDishError);
  ui.engine.addEventListener('change', () => { ui.modelWrap.hidden = ui.engine.value !== 'ollama'; });
  ui.session.addEventListener('change', () => {
    activeSession = sessions.find((item) => item.id === ui.session.value) || null;
    renderMessages(activeSession?.messages);
    loadSessionTrace(activeSession);
  });
  $('live-new-session').addEventListener('click', () => { void createSession().catch((error) => setStatus(error.message, true)); });
  $('live-trace-toggle').addEventListener('click', () => { ui.traceEvents.hidden = !ui.traceEvents.hidden; $('live-trace-toggle').setAttribute('aria-expanded', String(!ui.traceEvents.hidden)); });
  $('live-watchers-toggle').addEventListener('click', () => { const panel = $('live-watchers'); panel.hidden = !panel.hidden; $('live-watchers-toggle').setAttribute('aria-expanded', String(!panel.hidden)); if (!panel.hidden) void loadWatchers(); });
  $('live-watcher-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      await post('/api/watchers', { name: $('live-watcher-name').value.trim(), command: $('live-watcher-command').value.trim(), interval_seconds: Number($('live-watcher-interval').value) });
      $('live-watcher-form').reset();
      setStatus('Watcher created.');
      await loadWatchers();
    } catch (error) { setStatus(error.message, true); }
  });
  $('live-mic').addEventListener('click', () => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) { setStatus('Voice input is unavailable in this browser.', true); return; }
    if (recognition) { recognition.stop(); recognition = null; return; }
    recognition = new Recognition();
    recognition.lang = navigator.language || 'en-US';
    recognition.interimResults = false;
    recognition.onresult = (event) => { ui.prompt.value = [ui.prompt.value, event.results[0][0].transcript].filter(Boolean).join(' '); ui.prompt.focus(); };
    recognition.onend = () => { recognition = null; $('live-mic').classList.remove('listening'); setStatus('Voice captured. Review and send your message.'); };
    recognition.onerror = (event) => setStatus(`Voice input: ${event.error}`, true);
    $('live-mic').classList.add('listening');
    recognition.start();
  });

  if (ui.dishErrorModal) {
    ui.dishErrorModal.hidden = true;
    ui.dishErrorModal.style.display = 'none';
  }

  updateRoleUI();
  renderSmartSuggestions();
  void refreshStatus().then(() => { if (connected) { void loadEngines(); void loadSessions(); void loadWatchers(); } });
  window.setInterval(refreshStatus, 10000);
})();

