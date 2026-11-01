# AgentOS

**A local-first AI workspace where specialised agents do real work, and a human stays in control.**

AI agents can write code, run commands and change files, but they are hard to trust.
AgentOS puts **approval, audit and safety** around them: nothing becomes final until a
human reviews the exact result. Everything runs on your own machine.


## Table of contents
1. [Features](#features)
2. [How it works](#how-it-works)
3. [Tech stack](#tech-stack)
4. [Backend layers](#backend-layers)
5. [API overview](#api-overview)
6. [Techniques used](#techniques-used)
7. [Real-world use cases](#real-world-use-cases)
8. [Getting started](#getting-started)
9. [Configuration](#configuration)
10. [Project structure](#project-structure)
11. [Testing](#testing)
12. [Current limitations](#current-limitations)
13. [Roadmap](#roadmap)
14. [Team and roles](#team-and-roles)


## Features

- **Multi-agent live chat:** a router picks a specialist (file engineer, web researcher,
  system operator, project architect, grocery chef, verifier). Each agent has its own
  instructions and its own allowed tools, and runs a think → act → observe loop.
- **Mission engine:** a goal becomes a dependency-ordered task graph for three roles:
  **Developer**, **Creator** and **Student**.
- **Human-in-the-loop approval:** approvals are bound to a SHA-256 digest of the exact
  evidence, so a result that changed after review cannot be approved by mistake.
- **Safe by design:** scoped agent permissions, risk checks on dangerous commands, and
  Developer patches applied to **scratch copies**, never the original code.
- **Live streaming UI:** watch the agent's thinking and tool calls in real time
  (Server-Sent Events), with browser voice input.
- **Local-first:** data lives in SQLite on your machine. Use Groq for speed or Ollama
  for fully offline use.
- **Background watchers:** scheduled checks (for example `git status` every 5 minutes).
- **Persistent memory:** notes and mission history survive restarts, with keyword search
  and optional local semantic search.
- **Offline demo mode:** scripted responses so a demo never depends on the network.
- **Workflow simulator:** an interactive landing-page illustration comparing a single
  agent with a hierarchical (Planner / Ops / Verifier) architecture.

## How it works

```
UI (browser / Electron)  ->  FastAPI backend  ->  Agent engine (LLM + tools)
                                   |                        |
                           SQLite + artifacts       files, terminal, web
                                   |
                    Human approval before final results
```

**Live chat:** your prompt is routed to a specialist agent. The agent sends the prompt
and its allowed tools to the model, runs any tool the model requests, feeds the result
back, and repeats (up to 6 rounds) until it has a final answer. Every step streams to
the UI.

**Missions:** a goal is planned into tasks, tasks run in dependency order, and the
result stops at `WAITING_APPROVAL`. A human approves or rejects it with a matching
digest.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, vanilla JavaScript, Web Speech API |
| Desktop | Electron shell (loopback-only navigation) |
| Backend | Python 3.11+, FastAPI, Uvicorn, Pydantic |
| AI engines | Groq API (`openai/gpt-oss-120b`), Ollama (local, optional) |
| Storage | SQLite, optional local embeddings for semantic memory |
| Agent tools | File operations, terminal, git, DuckDuckGo search, web fetch, Playwright (Blinkit cart) |
| Imaging | Pillow (Creator thumbnails) |

## Backend layers

| Layer | Folder | Responsibility |
|---|---|---|
| **API** | `backend/src/agentos/api/` | About 50 REST endpoints, security middleware (same-origin checks, JSON-only writes, CSP headers) |
| **Domain** | `.../domain/` | Pydantic models and rules: missions, tasks, agents, permissions, governance, artifacts |
| **Services** | `.../services/` | Planning, orchestration, approvals, Developer/Creator/Student workflows, memory, watchers, multi-agent system |
| **Adapters** | `.../adapters/` | Groq, Ollama, SQLite, tool execution, embeddings, thumbnails, demo mode |

Keeping the layers separate means the AI engine or database can be swapped without
rewriting business logic.

## API overview

| Group | Examples |
|---|---|
| Health | `/health`, `/status`, `/overview` |
| Live chat | `/api/chat`, `/api/chat/stream`, `/api/chat/sessions` |
| Engines & watchers | `/api/engines`, `/api/watchers` |
| Memory | `/memory`, `/memory/semantic/search` |
| Workflows | `/workflows/developer`, `/workflows/creator`, `/workflows/student` |
| Missions | `/missions`, `/missions/{id}/run`, `/missions/{id}/cancel` |
| Approvals | `/approvals/{id}/decision` |
| Artifacts | `/artifacts/{id}/content` |

## Techniques used

- Tool calling / ReAct agent loop
- Multi-agent orchestration with specialist agents and dependency-ordered tasks
- Server-Sent Events streaming
- Human-in-the-loop governance with digest-bound approvals and role checks (Viewer / Operator / Admin)
- Risk assessment of dangerous commands (`rm`, `git reset --hard`, `drop table`, and similar)
- Scratch-copy sandboxing for code patches
- Resilience: salvaging truncated tool calls, context trimming, retries, output truncation
- Persistent memory with keyword and optional semantic retrieval
- Background scheduled watchers
- Offline demo mode

## Real-world use cases

- **Developers:** find a bug, patch a copy, prove the fix with before/after tests, and wait for approval.
- **Creators:** produce a source-linked outline, script and thumbnail.
- **Students:** turn their own material into sourced notes, a quiz and a focus plan.
- **Everyday users:** control the computer in plain language (create projects, search the web, plan groceries).
- **Organisations:** local data, auditability and approval gates, the things that block agents from real workplaces.

## Getting started

**Requirements:** Python 3.11+, Node.js, Git. Windows PowerShell is the primary launcher.

```powershell
# 1. Clone and install
git clone <your-repo-url>
cd AgentOS
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "./backend[dev]"
npm --prefix frontend ci --no-fund --no-audit
npm --prefix frontend run build

# 2. Start the offline demo (no API key needed)
.\Start-AgentOS.ps1 -Demo
```

On another OS, from an installed environment: `python -m agentos serve --demo`.

Then open **http://127.0.0.1:8768/app/**.

**Live AI mode:** copy `.env.example` to `.env`, add your own key (see
[Configuration](#configuration)), then run `.\Start-AgentOS.ps1`.

**Desktop app:** `.\Start-AgentOSDesktop.ps1`

**Optional, for the Blinkit grocery agent:**
```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m playwright install chromium
```

## Configuration

Copy `.env.example` to `.env`. **Never commit `.env` or share your API key.**

| Variable | Purpose |
|---|---|
| `AGENTOS_MODEL` | Model name, for example `openai/gpt-oss-120b` |
| `AGENTOS_MODEL_KEY` | Your provider API key |
| `AGENTOS_MODEL_URL` | Provider endpoint URL (OpenAI-compatible) |
| `AGENTOS_USER_ROLE` | `viewer`, `operator` or `admin` |
| `AGENTOS_ALLOW_LIVE_MODELS` | Enable cloud models such as Groq |
| `AGENTOS_ALLOW_LOCAL_MODELS` | Enable local models such as Ollama |

## Project structure

```
AgentOS/
├── backend/            # FastAPI app: api/, domain/, services/, adapters/
├── frontend/site/      # Dashboard UI (HTML, CSS, vanilla JS)
├── desktop/            # Electron shell
├── packages/           # Developer / Creator / Student agent manifests (JSON)
├── samples/            # Demo inputs
├── docs/               # Setup and provider guides
├── Start-AgentOS.ps1
├── Start-AgentOSDesktop.ps1
├── ARCHITECTURE.md
└── README.md
```

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest backend
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix desktop test
```

The project includes an automated backend test suite (779 tests at the time of writing)
and CI workflows.

## Current limitations

We list these openly:

- In live chat, risky tool calls show a warning but still run; **mission approvals fully block**.
- Agent routing is keyword-based (LLM-based routing is planned).
- The terminal tool uses a deny-list guardrail, not a full sandbox.
- The Blinkit agent **adds items to the cart only**. The user logs in, confirms the address and pays.
- The landing-page workflow simulator is a teaching illustration, not a benchmark.
- Memory retrieval is keyword-based by default; semantic search is optional.

## Roadmap

- Enforce hard approval gates in live chat, not only in missions
- LLM-based or hybrid agent routing
- Container-based sandboxing for the terminal tool
- Evaluation suite for real model behaviour
- Postgres option for multi-user deployments

## Team and roles

| Member | Role | Owns |
|---|---|---|
| **[Gaurav]** | Frontend and Desktop | `frontend/site/`: dashboard UI, live streaming view, voice input, workflow simulator, motion and visuals; `desktop/`: Electron shell |
| **[Sumukh Dixit]** | Backend API and Data | `api/app.py` and middleware, SQLite and chat storage, domain models, memory and embeddings, background watchers |
| **[Sarthak]** | AI Agents and Tools | Groq/Ollama adapters, multi-agent router and agent loop, tool system (files, terminal, web, apps), grocery/Blinkit agent |
| **[Ashish]** | Mission Engine, Safety and Testing | Planning and orchestration, approvals and governance, Developer/Creator/Student workflows, test suite, CI and documentation |

