"""SQLite persistence store for AgentOS chat sessions and messages."""

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ChatStorage:
    """Manages chat session and message records inside the local SQLite database."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            self.db_path = Path(".agentos/agentos.sqlite3")
        else:
            self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    agent TEXT,
                    model TEXT,
                    trace_json TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session 
                ON chat_messages(session_id, created_at)
                """
            )

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all chat sessions with their message count and latest message timestamp."""
        with closing(self._connect()) as conn:
            query = """
                SELECT 
                    s.id, 
                    s.title, 
                    s.created_at, 
                    s.updated_at,
                    COUNT(m.id) as message_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON s.id = m.session_id
                GROUP BY s.id
                ORDER BY s.updated_at DESC
            """
            rows = conn.execute(query).fetchall()
            results = []
            for r in rows:
                results.append({
                    "id": r["id"],
                    "title": r["title"],
                    "createdAt": r["created_at"],
                    "updatedAt": r["updated_at"],
                    "messageCount": r["message_count"],
                })
            return results

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a full session with all ordered messages and parsed traces."""
        with closing(self._connect()) as conn:
            s_row = conn.execute(
                "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if not s_row:
                return None

            m_rows = conn.execute(
                """
                SELECT id, role, content, agent, model, trace_json, timestamp, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at ASC, rowid ASC
                """,
                (session_id,),
            ).fetchall()

            messages = []
            for m in m_rows:
                trace = []
                if m["trace_json"]:
                    try:
                        trace = json.loads(m["trace_json"])
                    except Exception:
                        trace = []
                messages.append({
                    "id": m["id"],
                    "role": m["role"],
                    "content": m["content"],
                    "agent": m["agent"],
                    "model": m["model"],
                    "trace": trace,
                    "timestamp": m["timestamp"],
                })

            return {
                "id": s_row["id"],
                "title": s_row["title"],
                "createdAt": s_row["created_at"],
                "updatedAt": s_row["updated_at"],
                "messages": messages,
            }

    def save_session_meta(self, session_id: str, title: str, created_at: Optional[str] = None, updated_at: Optional[str] = None) -> None:
        """Upsert session metadata."""
        now_iso = datetime.now(timezone.utc).isoformat()
        c_at = created_at or now_iso
        u_at = updated_at or now_iso
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    updated_at = excluded.updated_at
                """,
                (session_id, title, c_at, u_at),
            )

    def save_message(self, session_id: str, msg: Dict[str, Any]) -> None:
        """Insert or replace a message for a session, updating session updated_at."""
        msg_id = str(msg.get("id") or datetime.now(timezone.utc).timestamp())
        role = str(msg.get("role", "user"))
        content = str(msg.get("content", ""))
        agent = msg.get("agent")
        model = msg.get("model")
        timestamp = str(msg.get("timestamp") or "")
        trace = msg.get("trace")
        trace_json = json.dumps(trace) if trace else None
        now_iso = datetime.now(timezone.utc).isoformat()

        with closing(self._connect()) as conn, conn:
            # Ensure session exists
            conn.execute(
                """
                INSERT OR IGNORE INTO chat_sessions (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, "New Conversation", now_iso, now_iso),
            )

            conn.execute(
                """
                INSERT OR REPLACE INTO chat_messages (id, session_id, role, content, agent, model, trace_json, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (msg_id, session_id, role, content, agent, model, trace_json, timestamp, now_iso),
            )

            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now_iso, session_id),
            )

    def save_full_session(self, session: Dict[str, Any]) -> None:
        """Atomically upsert a session and all its messages."""
        session_id = str(session.get("id", ""))
        if not session_id:
            return

        title = str(session.get("title", "New Conversation"))
        created_at = str(session.get("createdAt") or datetime.now(timezone.utc).isoformat())
        updated_at = str(session.get("updatedAt") or datetime.now(timezone.utc).isoformat())
        messages = session.get("messages", [])

        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    updated_at = excluded.updated_at
                """,
                (session_id, title, created_at, updated_at),
            )

            for idx, msg in enumerate(messages):
                msg_id = str(msg.get("id") or f"{session_id}_{idx}")
                role = str(msg.get("role", "user"))
                content = str(msg.get("content", ""))
                agent = msg.get("agent")
                model = msg.get("model")
                timestamp = str(msg.get("timestamp") or "")
                trace = msg.get("trace")
                trace_json = json.dumps(trace) if trace else None
                # Create a sortable timestamp
                created_msg = f"{created_at}_{idx:04d}"

                conn.execute(
                    """
                    INSERT OR REPLACE INTO chat_messages (id, session_id, role, content, agent, model, trace_json, timestamp, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (msg_id, session_id, role, content, agent, model, trace_json, timestamp, created_msg),
                )

    def sync_all_sessions(self, sessions: List[Dict[str, Any]]) -> None:
        """Batch save multiple sessions from the client."""
        for s in sessions:
            if isinstance(s, dict) and s.get("id"):
                self.save_full_session(s)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all associated messages."""
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            return cursor.rowcount > 0

    def get_all_full_sessions(self) -> List[Dict[str, Any]]:
        """Return all sessions with full message lists (for frontend restoration)."""
        session_metas = self.list_sessions()
        full_sessions = []
        for s in session_metas:
            data = self.get_session(s["id"])
            if data:
                full_sessions.append(data)
        return full_sessions
