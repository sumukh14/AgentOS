"""Dynamic Tools for AgentOS.

Inspired by:
- PersonalAgent (natural language file/workspace operations)
- OmniPilot (computer-use & system automation with permission safety)
- DuckDuckGo live search
"""

import os
import subprocess
import json
import urllib.request
import urllib.parse
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        HAS_DDGS = True
    except ImportError:
        HAS_DDGS = False

WORKSPACE_ROOT = Path(".").resolve()


class DynamicTools:
    """Unified tool executor for local file, system, and web research operations."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.root = (workspace_root or WORKSPACE_ROOT).resolve()

    def _resolve_safe_path(self, path_str: str) -> Path:
        """Resolve path safely, supporting relative paths and drive paths while blocking sensitive system folders."""
        p = Path(path_str)
        if p.is_absolute() or (len(path_str) > 1 and path_str[1] == ":"):
            target = p.resolve()
        else:
            target = (self.root / path_str).resolve()

        # Guard against sensitive operating system core folders
        low = str(target).lower()
        blocked = ["c:\\windows\\system32", "c:\\windows\\syswow64", "c:\\boot"]
        if any(low.startswith(b) for b in blocked):
            raise PermissionError(f"Access denied to system directory: '{path_str}'")
        return target

    # ==================== 1. FILE & WORKSPACE TOOLS (PersonalAgent) ====================

    def read_file(self, file_path: str, max_lines: int = 500) -> Dict[str, Any]:
        """Read text from a file up to max_lines."""
        try:
            target = self._resolve_safe_path(file_path)
            if not target.exists():
                return {"status": "error", "error": f"File '{file_path}' does not exist"}
            if not target.is_file():
                return {"status": "error", "error": f"Path '{file_path}' is not a file"}

            content = target.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            truncated = len(lines) > max_lines
            display_lines = lines[:max_lines]

            return {
                "status": "success",
                "file_path": file_path,
                "total_lines": len(lines),
                "truncated": truncated,
                "content": "\n".join(display_lines),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Create or overwrite a file in the workspace."""
        try:
            target = self._resolve_safe_path(file_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {
                "status": "success",
                "file_path": file_path,
                "bytes_written": len(content.encode("utf-8")),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def patch_file(self, file_path: str, target_snippet: str, replacement_snippet: str) -> Dict[str, Any]:
        """Replace a specific snippet of text in a file."""
        try:
            target = self._resolve_safe_path(file_path)
            if not target.exists():
                return {"status": "error", "error": f"File '{file_path}' does not exist"}
            content = target.read_text(encoding="utf-8")
            if target_snippet not in content:
                return {"status": "error", "error": "Target snippet not found in file"}
            
            new_content = content.replace(target_snippet, replacement_snippet, 1)
            target.write_text(new_content, encoding="utf-8")
            return {
                "status": "success",
                "file_path": file_path,
                "message": "Replacement applied successfully",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def create_directory(self, dir_path: str) -> Dict[str, Any]:
        """Create a new folder or directory path on the filesystem."""
        try:
            target = self._resolve_safe_path(dir_path)
            target.mkdir(parents=True, exist_ok=True)
            return {
                "status": "success",
                "directory": str(target),
                "message": f"Directory '{dir_path}' created successfully",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def create_project(
        self,
        project_dir: str,
        files: List[Dict[str, str]],
        description: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """Scaffold a complete multi-file application or system inside a directory in one atomic operation."""
        try:
            target_dir = self._resolve_safe_path(project_dir)
            target_dir.mkdir(parents=True, exist_ok=True)

            created_files = []
            for item in files:
                rel_path = item.get("path") or item.get("filename") or item.get("name") or ""
                content = item.get("content", "")
                if not rel_path:
                    continue
                file_target = (target_dir / rel_path).resolve()
                file_target.parent.mkdir(parents=True, exist_ok=True)
                file_target.write_text(content, encoding="utf-8")
                created_files.append({
                    "file": rel_path,
                    "full_path": str(file_target),
                    "bytes": len(content.encode("utf-8")),
                })

            return {
                "status": "success",
                "project_dir": str(target_dir),
                "description": description,
                "files_count": len(created_files),
                "files": [f["file"] for f in created_files],
                "message": f"Successfully created project with {len(created_files)} files in '{target_dir}'",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def list_directory(self, dir_path: str = ".") -> Dict[str, Any]:
        """List files and directories within a given directory."""
        try:
            target = self._resolve_safe_path(dir_path)
            if not target.exists() or not target.is_dir():
                return {"status": "error", "error": f"Directory '{dir_path}' does not exist"}

            items = []
            for item in sorted(target.iterdir()):
                try:
                    rel_str = str(item.relative_to(self.root)).replace("\\", "/")
                except ValueError:
                    rel_str = str(item)
                items.append({
                    "name": item.name,
                    "path": rel_str,
                    "is_dir": item.is_dir(),
                    "size_bytes": item.stat().st_size if item.is_file() else None,
                })
            return {"status": "success", "directory": dir_path, "items": items}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def find_files(
        self,
        pattern: str = "*",
        search_path: str = ".",
        max_results: int = 30,
        max_depth: int = 4,
        **kwargs,
    ) -> Dict[str, Any]:
        """Find files matching a pattern or extension (e.g. '*.mp4', '*.mkv', '*.py') on a drive or directory."""
        max_results = min(int(kwargs.get("max_results", max_results)), 30)
        try:
            target = self._resolve_safe_path(search_path)
            if not target.exists() or not target.is_dir():
                return {"status": "error", "error": f"Path '{search_path}' is not an accessible directory"}

            results = []
            import fnmatch

            target_depth = len(target.parts)
            for root, dirs, files in os.walk(target):
                # Check search depth
                curr_depth = len(Path(root).parts) - target_depth
                if curr_depth > max_depth:
                    dirs.clear()
                    continue

                # Skip hidden/heavy/system directories
                dirs[:] = [
                    d for d in dirs
                    if d not in {".git", ".venv", "node_modules", "$RECYCLE.BIN", "System Volume Information", "Windows"}
                ]

                # Match comma-separated patterns like "*.mp4, *.mkv, *.avi"
                sub_patterns = [p.strip().lower() for p in pattern.replace(";", ",").split(",") if p.strip()]
                if not sub_patterns:
                    sub_patterns = ["*"]

                for f in files:
                    fname = f.lower()
                    matched = any(
                        fnmatch.fnmatch(fname, sp) or (sp.startswith(".") and fname.endswith(sp)) or (sp in fname)
                        for sp in sub_patterns
                    )
                    if matched:
                        full_p = Path(root) / f
                        try:
                            size = full_p.stat().st_size
                        except Exception:
                            size = None
                        results.append({
                            "name": f,
                            "path": str(full_p),
                            "size_bytes": size,
                        })
                        if len(results) >= max_results:
                            break
                if len(results) >= max_results:
                    break

            return {
                "status": "success",
                "pattern": pattern,
                "search_path": str(target),
                "count": len(results),
                "files": results,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def search_code(self, query: str, sub_path: str = ".", max_matches: int = 25, **kwargs) -> Dict[str, Any]:
        """Search for a regex or substring across text files."""
        if "max_results" in kwargs:
            max_matches = int(kwargs["max_results"])
        try:
            target = self._resolve_safe_path(sub_path)
            matches = []
            pattern = re.compile(query, re.IGNORECASE)

            for root, dirs, files in os.walk(target):
                dirs[:] = [d for d in dirs if d not in {".git", ".venv", "node_modules", "__pycache__", "dist"}]
                for f in files:
                    file_p = Path(root) / f
                    try:
                        text = file_p.read_text(encoding="utf-8", errors="ignore")
                        for idx, line in enumerate(text.splitlines(), start=1):
                            if pattern.search(line):
                                rel = file_p.relative_to(self.root)
                                matches.append({
                                    "file": str(rel).replace("\\", "/"),
                                    "line_number": idx,
                                    "line": line.strip()[:200],
                                })
                                if len(matches) >= max_matches:
                                    break
                    except Exception:
                        continue
                    if len(matches) >= max_matches:
                        break
                if len(matches) >= max_matches:
                    break

            return {"status": "success", "query": query, "matches_count": len(matches), "matches": matches}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ==================== 2. SYSTEM & TERMINAL TOOLS (OmniPilot) ====================

    def run_terminal_command(self, command: str, timeout_seconds: int = 30) -> Dict[str, Any]:
        """Execute a safe shell command within the workspace."""
        try:
            # Enforce safety against destructive external commands
            forbidden = ["format ", "del /f /s /q c:", "rmdir /s /q c:", ":(){ :|:& };:"]
            if any(f in command.lower() for f in forbidden):
                return {"status": "error", "error": "Command blocked by security policy"}

            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            return {
                "status": "success",
                "command": command,
                "exit_code": proc.returncode,
                "stdout": proc.stdout[:10000],
                "stderr": proc.stderr[:5000],
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": f"Command timed out after {timeout_seconds}s"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def git_status(self) -> Dict[str, Any]:
        """Get git status of workspace."""
        return self.run_terminal_command("git status --short")

    # ==================== 3. WEB RESEARCH TOOLS ====================

    def web_search(self, query: str, max_results: int = 3, **kwargs) -> Dict[str, Any]:
        """Search DuckDuckGo in real-time without an API key."""
        try:
            if HAS_DDGS:
                results = []
                try:
                    results = list(DDGS().text(query, max_results=max_results))
                except Exception:
                    results = []
                if not results:
                    try:
                        news_results = list(DDGS().news(query, max_results=max_results))
                        if news_results:
                            return {
                                "status": "success",
                                "query": query,
                                "results": [
                                    {
                                        "title": r.get("title"),
                                        "snippet": (r.get("body") or "")[:400],
                                        "url": r.get("url"),
                                    }
                                    for r in news_results
                                ],
                            }
                    except Exception:
                        pass
                if results:
                    return {
                        "status": "success",
                        "query": query,
                        "results": [
                            {
                                "title": r.get("title"),
                                "snippet": (r.get("body") or "")[:400],
                                "url": r.get("href"),
                            }
                            for r in results
                        ],
                    }

            # Instant answer API fallback
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as res:
                data = json.loads(res.read().decode("utf-8"))
                topics = data.get("RelatedTopics", [])[:max_results]
                return {
                    "status": "success",
                    "query": query,
                    "results": [
                        {"title": t.get("Text", "")[:60], "snippet": (t.get("Text") or "")[:400], "url": t.get("FirstURL")}
                        for t in topics if isinstance(t, dict) and "Text" in t
                    ],
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def fetch_web_page(self, url: str, max_chars: int = 1500) -> Dict[str, Any]:
        """Fetch and extract visible text from a public web page."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=15) as res:
                html = res.read().decode("utf-8", errors="ignore")
                # Basic HTML tag stripping
                clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<[^>]+>", " ", clean)
                text = re.sub(r"\s+", " ", text).strip()
                return {
                    "status": "success",
                    "url": url,
                    "content": text[:max_chars],
                    "total_chars": len(text),
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def open_application(self, app_name: str, arguments: Optional[str] = None) -> Dict[str, Any]:
        """Launch or open a desktop application on the Windows computer (e.g. calculator, notepad, chrome, vscode, paint, explorer, terminal)."""
        raw_clean = app_name.strip().lower()
        # Clean common prefixes/suffixes
        for prefix in ("open ", "launch ", "start ", "run "):
            if raw_clean.startswith(prefix):
                raw_clean = raw_clean[len(prefix):].strip()
        for suffix in (" application", " app", " please", " tool"):
            if raw_clean.endswith(suffix):
                raw_clean = raw_clean[:-len(suffix)].strip()

        APP_MAP = {
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "cal": "calc.exe",
            "notepad": "notepad.exe",
            "notes": "notepad.exe",
            "paint": "mspaint.exe",
            "mspaint": "mspaint.exe",
            "chrome": "chrome",
            "google chrome": "chrome",
            "browser": "https://www.google.com",
            "edge": "msedge",
            "microsoft edge": "msedge",
            "vscode": "code",
            "code": "code",
            "vs code": "code",
            "visual studio code": "code",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "files": "explorer.exe",
            "terminal": "wt.exe",
            "windows terminal": "wt.exe",
            "powershell": "powershell.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "task manager": "taskmgr.exe",
            "taskmgr": "taskmgr.exe",
            "taskmanager": "taskmgr.exe",
            "settings": "ms-settings:",
            "windows settings": "ms-settings:",
            "control panel": "control.exe",
            "snipping tool": "snippingtool.exe",
            "wordpad": "write.exe",
        }

        target = APP_MAP.get(raw_clean)
        if not target:
            for k, v in APP_MAP.items():
                if k in raw_clean:
                    target = v
                    break
        if not target:
            target = app_name.strip()

        arg_str = f" {arguments.strip()}" if arguments else ""

        try:
            if hasattr(os, "startfile") and not arguments:
                try:
                    os.startfile(target)
                except Exception:
                    subprocess.Popen(f'start "" "{target}"', shell=True)
            else:
                subprocess.Popen(f'start "" "{target}"{arg_str}', shell=True)

            return {
                "status": "success",
                "app_name": app_name,
                "target": target,
                "output": f"Successfully launched '{app_name}' ({target}) on your Windows desktop."
            }
        except Exception as e:
            try:
                subprocess.Popen(["powershell", "-NoProfile", "-Command", f"Start-Process '{target}'{arg_str}"])
                return {
                    "status": "success",
                    "app_name": app_name,
                    "target": target,
                    "output": f"Launched '{app_name}' via PowerShell Start-Process."
                }
            except Exception as e2:
                return {
                    "status": "error",
                    "error": f"Failed to launch '{app_name}': {str(e2)}"
                }

    def plan_and_order_blinkit_groceries(
        self,
        breakfast: str,
        lunch: str,
        dinner: str,
        servings: int = 2,
        open_browser: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """Decompose breakfast, lunch, and dinner into required grocery ingredients and open Blinkit in Google Chrome to add them to cart."""
        from agentos.services.grocery_planner import GroceryPlannerService

        # Validate edible food dishes
        for meal_name, dish_str in [("Breakfast", breakfast), ("Lunch", lunch), ("Dinner", dinner)]:
            val = GroceryPlannerService.validate_edible_dish(dish_str)
            if not val.get("valid"):
                return {
                    "status": "error",
                    "error": f"The item '{val.get('invalid_item')}' in {meal_name} does not match any known edible food dish! Please specify real food dishes (e.g. Poha, Dal Tadka, Paneer, Salad).",
                    "invalid_item": val.get("invalid_item"),
                    "meal": meal_name
                }

        decomp = GroceryPlannerService.decompose_meals_to_grocery_list(
            breakfast=breakfast,
            lunch=lunch,
            dinner=dinner,
            servings=servings,
        )

        automation_result = None
        if open_browser:
            automation_result = GroceryPlannerService.launch_blinkit_and_add_cart(
                items=decomp["items"],
                max_items_to_auto_click=kwargs.get("max_items", None),
            )

        return {
            "status": "success",
            "meal_plan": {
                "breakfast": breakfast,
                "lunch": lunch,
                "dinner": dinner,
                "servings": servings,
            },
            "main_ingredients_set": decomp.get("main_ingredients_set", []),
            "total_groceries": decomp["total_items_count"],
            "categories": decomp["categories"],
            "items": decomp["items"],
            "blinkit_automation": automation_result or {"status": "skipped", "message": "Browser launch not requested."},
            "summary": f"Sent dishes to Groq to extract main ingredients set: {', '.join(decomp.get('main_ingredients_set', []))}. Opened Chromium with location permissions on Blinkit and added 1 item per ingredient to the cart."
        }

    # ==================== TOOL DEFINITIONS SCHEMA ====================

    def get_tool_definitions(self, role: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return OpenAI / Groq tool schemas for tool-calling, optionally filtered by agent role."""
        ROLE_ALLOWED_TOOLS = {
            "grocery_chef": {"plan_and_order_blinkit_groceries", "open_application", "web_search"},
            "web_researcher": {"web_search", "fetch_web_page", "open_application", "plan_and_order_blinkit_groceries"},
            "file_engineer": {"read_file", "write_file", "patch_file", "list_directory", "find_files", "search_code", "open_application"},
            "system_operator": {"run_terminal_command", "git_status", "list_directory", "find_files", "open_application", "plan_and_order_blinkit_groceries"},
            "project_architect": {"create_project", "create_directory", "write_file", "read_file", "list_directory", "run_terminal_command", "open_application", "plan_and_order_blinkit_groceries"},
            "verifier": {"read_file", "run_terminal_command", "git_status", "search_code", "open_application"},
        }
        all_tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read contents of a file in the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Relative path to the file"}
                        },
                        "required": ["file_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write or create a file in the workspace with given content.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Relative path to write to"},
                            "content": {"type": "string", "description": "Text content to write"},
                        },
                        "required": ["file_path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "patch_file",
                    "description": "Replace a specific snippet in a file with new content.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Relative path to file"},
                            "target_snippet": {"type": "string", "description": "Existing text to replace"},
                            "replacement_snippet": {"type": "string", "description": "New text"},
                        },
                        "required": ["file_path", "target_snippet", "replacement_snippet"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "List files and subdirectories in a directory path.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "dir_path": {"type": "string", "description": "Relative directory path (default '.')", "default": "."}
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_code",
                    "description": "Search code and text files for a regex pattern or keyword.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Text or regex to search for"},
                            "sub_path": {"type": "string", "description": "Subdirectory to search in", "default": "."},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_terminal_command",
                    "description": "Run a shell or PowerShell command safely in the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Shell command to run"}
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the live web using DuckDuckGo (free, no API key).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search terms"},
                            "max_results": {"type": "integer", "description": "Number of results", "default": 5},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "find_files",
                    "description": "Find files by extension, pattern (e.g. '*.mp4', '*.mkv', '*.py', '*.pdf') across a drive or folder (e.g. 'D:\\', 'C:\\Users', '.').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "Glob pattern or extension like '*.mp4', '*.mkv', '*.py'"},
                            "search_path": {"type": "string", "description": "Drive or folder path to search in (e.g. 'D:\\' or '.')", "default": "."},
                            "max_results": {"type": "integer", "description": "Max files to return", "default": 50},
                        },
                        "required": ["pattern"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_directory",
                    "description": "Create a new folder or directory path on a drive (e.g. 'D:\\my_project').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "dir_path": {"type": "string", "description": "Folder path to create"}
                        },
                        "required": ["dir_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_project",
                    "description": "Scaffold a complete multi-file project inside a directory in one atomic call.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_dir": {"type": "string", "description": "Target folder on drive (e.g. 'D:\\student_management_system')"},
                            "description": {"type": "string", "description": "Brief description of the application"},
                            "files": {
                                "type": "array",
                                "description": "List of files to create, each having 'path' and 'content'",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "path": {"type": "string", "description": "Relative file path (e.g. 'main.py', 'database.py', 'README.md')"},
                                        "content": {"type": "string", "description": "Complete source code content for the file"}
                                    },
                                    "required": ["path", "content"]
                                }
                            }
                        },
                        "required": ["project_dir", "files"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_web_page",
                    "description": "Fetch and extract text content from a public web page URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "Full URL to fetch"}
                        },
                        "required": ["url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "open_application",
                    "description": "Open or launch a desktop application or utility on the user's Windows computer (e.g. calculator, notepad, chrome, vscode, paint, explorer, terminal, settings). Use this whenever the user asks to open, run, or start an application.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_name": {
                                "type": "string",
                                "description": "Name of the application to open, such as 'calculator', 'notepad', 'chrome', 'vscode', 'paint', 'explorer', 'terminal', 'cmd', 'settings'."
                            },
                            "arguments": {
                                "type": "string",
                                "description": "Optional file path, URL, or argument to pass to the application."
                            }
                        },
                        "required": ["app_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "plan_and_order_blinkit_groceries",
                    "description": "Calculate all required grocery ingredients for Breakfast, Lunch, and Dinner dishes, launch Google Chrome, open Blinkit (https://blinkit.com), and automatically add the necessary items into the user's shopping cart. Use this whenever the user asks for groceries, Blinkit cart, or meal-based ingredient shopping for breakfast, lunch, and dinner.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "breakfast": {
                                "type": "string",
                                "description": "Dish or dishes for breakfast (e.g. 'Poha', 'Aloo Paratha', 'Bread Omelette', 'Idli Sambar')"
                            },
                            "lunch": {
                                "type": "string",
                                "description": "Dish or dishes for lunch (e.g. 'Dal Tadka, Paneer Butter Masala, Roti, Rice')"
                            },
                            "dinner": {
                                "type": "string",
                                "description": "Dish or dishes for dinner (e.g. 'Khichdi and Curd', 'Matar Paneer and Roti', 'Salad')"
                            },
                            "servings": {
                                "type": "integer",
                                "description": "Number of servings or people to prepare for (default is 2)"
                            },
                            "open_browser": {
                                "type": "boolean",
                                "description": "Whether to launch Google Chrome and open Blinkit (default is true)"
                            }
                        },
                        "required": ["breakfast", "lunch", "dinner"],
                    },
                },
            },
        ]
        if role and role in ROLE_ALLOWED_TOOLS:
            allowed = ROLE_ALLOWED_TOOLS[role]
            return [t for t in all_tools if t["function"]["name"] in allowed]
        return all_tools

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch tool call by name with parsed arguments."""
        tool_map = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "patch_file": self.patch_file,
            "create_directory": self.create_directory,
            "create_project": self.create_project,
            "list_directory": self.list_directory,
            "find_files": self.find_files,
            "search_code": self.search_code,
            "run_terminal_command": self.run_terminal_command,
            "web_search": self.web_search,
            "fetch_web_page": self.fetch_web_page,
            "git_status": self.git_status,
            "open_application": self.open_application,
            "plan_and_order_blinkit_groceries": self.plan_and_order_blinkit_groceries,
        }
        if name not in tool_map:
            return {"status": "error", "error": f"Tool '{name}' is not registered"}
        try:
            target_fn = tool_map[name]
            import inspect
            sig = inspect.signature(target_fn)
            filtered_args = {}
            for param_name, param in sig.parameters.items():
                if param.kind == inspect.Parameter.VAR_KEYWORD:
                    filtered_args.update(args)
                    break
                if param_name in args:
                    filtered_args[param_name] = args[param_name]
            return target_fn(**filtered_args)
        except Exception as e:
            return {"status": "error", "error": f"Tool execution failed: {str(e)}"}

    def check_tool_risk(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Assess whether a tool call poses a high risk to the system or filesystem."""
        if name == "run_terminal_command":
            cmd = str(args.get("command", "")).lower()
            dangerous_patterns = [
                "rm ", "rmdir", "del ", "erase", "format", "shutdown", "reboot",
                "kill", "taskkill", "drop database", "git reset --hard", "git clean",
                "drop table", "mkfs", "dd if="
            ]
            for pat in dangerous_patterns:
                if pat in cmd:
                    return {
                        "requires_approval": True,
                        "risk_level": "high",
                        "reason": f"Potentially destructive terminal command detected: '{pat.strip()}'",
                        "command": args.get("command"),
                    }
        elif name in ("write_file", "patch_file"):
            target_path = str(args.get("file_path", "")).lower()
            critical_files = [".env", "package.json", "pyproject.toml", "settings.json"]
            if any(target_path.endswith(f) for f in critical_files):
                return {
                    "requires_approval": True,
                    "risk_level": "medium",
                    "reason": f"Modifying critical project configuration file: '{target_path}'",
                    "file_path": args.get("file_path"),
                }
        return {"requires_approval": False, "risk_level": "low"}

