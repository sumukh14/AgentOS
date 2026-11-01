# AgentOS research frontend

This is the interactive AgentOS research site, not the frontend from the supplied archive. The supplied backend source is preserved in the project package. The backend serves `frontend/dist` at `/app/`.

The live section reads `/status`, `/overview`, `/api/engines`, `/api/chat/sessions`, `/api/chat/stream`, and `/api/watchers` from that same origin. The teaching simulator is explicitly illustrative and does not call the backend.

Edit files in `frontend/site`, then run `npm --prefix frontend run build` to copy them to `frontend/dist`. The package includes a ready `dist`, so the existing start script can serve it without rebuilding. No frontend dependencies are required.

When this site is opened outside the local backend, the research interactions remain available and the live panel reports that the backend is unavailable.
