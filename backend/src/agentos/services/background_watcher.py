"""Automated background task watcher for AgentOS.

Supports scheduled recurring checks (e.g. git status, test runs, health audits)
running in background worker threads without blocking the main event loop.
"""

import threading
import time
import uuid
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class BackgroundWatcherService:
    """Manages scheduled background automation tasks and records execution history."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.root = (workspace_root or Path.cwd()).resolve()
        self._watchers: Dict[str, Dict[str, Any]] = {}
        self._history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Add default recommended watchers
        self.add_watcher(
            name="Workspace Git Status Monitor",
            command="git status -s",
            interval_seconds=300,
            enabled=True,
            description="Checks for uncommitted modifications in the workspace every 5 minutes",
        )

        self._start_loop()

    def _start_loop(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(1)
            now = time.time()
            with self._lock:
                for wid, w in list(self._watchers.items()):
                    if not w.get("enabled", True):
                        continue
                    last_run = w.get("last_run_timestamp", 0)
                    interval = w.get("interval_seconds", 60)
                    if now - last_run >= interval:
                        w["last_run_timestamp"] = now
                        threading.Thread(target=self._execute_watcher, args=(wid,), daemon=True).start()

    def _execute_watcher(self, watcher_id: str) -> None:
        with self._lock:
            w = self._watchers.get(watcher_id)
            if not w:
                return
            command = w["command"]
            name = w["name"]

        start_time = datetime.now().isoformat()
        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=str(self.root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
            )
            output = res.stdout.strip() or res.stderr.strip() or "(no output)"
            status = "success" if res.returncode == 0 else "failed"
        except Exception as e:
            output = f"Execution error: {e}"
            status = "error"

        record = {
            "id": str(uuid.uuid4())[:8],
            "watcher_id": watcher_id,
            "watcher_name": name,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "status": status,
            "output_preview": output[:300],
        }

        with self._lock:
            if watcher_id in self._watchers:
                self._watchers[watcher_id]["last_status"] = status
                self._watchers[watcher_id]["last_run_display"] = record["timestamp"]
                self._watchers[watcher_id]["last_output"] = record["output_preview"]
            self._history.append(record)
            if len(self._history) > 50:
                self._history.pop(0)

    def add_watcher(
        self,
        name: str,
        command: str,
        interval_seconds: int = 180,
        enabled: bool = True,
        description: str = "",
    ) -> str:
        wid = str(uuid.uuid4())[:8]
        with self._lock:
            self._watchers[wid] = {
                "id": wid,
                "name": name,
                "command": command,
                "interval_seconds": max(interval_seconds, 10),
                "enabled": enabled,
                "description": description or f"Runs: {command}",
                "last_run_timestamp": 0,
                "last_run_display": "Never",
                "last_status": "idle",
                "last_output": None,
            }
        return wid

    def toggle_watcher(self, watcher_id: str) -> Optional[bool]:
        with self._lock:
            if watcher_id in self._watchers:
                self._watchers[watcher_id]["enabled"] = not self._watchers[watcher_id]["enabled"]
                return self._watchers[watcher_id]["enabled"]
        return None

    def delete_watcher(self, watcher_id: str) -> bool:
        with self._lock:
            if watcher_id in self._watchers:
                del self._watchers[watcher_id]
                return True
        return False

    def trigger_now(self, watcher_id: str) -> None:
        threading.Thread(target=self._execute_watcher, args=(watcher_id,), daemon=True).start()

    def list_watchers(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._watchers.values())

    def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(reversed(self._history))
