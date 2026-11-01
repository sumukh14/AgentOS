# AgentOS research site + existing backend

This package keeps the backend source from the supplied AgentOS archive and replaces its frontend with the AgentOS research site.

## Use with your running backend

Copy the packaged `AgentOS-main/frontend/dist` folder over the `frontend/dist` folder of your running AgentOS checkout, then open `http://127.0.0.1:8000/app/` (or the port you already use). The backend serves that directory at `/app/`. A browser refresh loads the new frontend; no backend source change is required.

The site retains its interactive architecture simulator. The new live section uses the existing backend endpoints for status, mission overview, agent activity, streaming chat, conversation sessions, engine selection, voice input, and background watchers. The simulator is educational and clearly marked as separate from live operations.

The frontend source is in `frontend/site`. Run `npm --prefix frontend run build` to copy it into `frontend/dist`; there are no frontend dependencies. The packaged `dist` is ready to use.

Local environments, secrets, caches, databases, and generated dependencies from the supplied archive were omitted from this source package. The backend code itself was not edited or run during this work.
