"""Groq LLM Engine for AgentOS.

Supports:
- High-speed inference via Groq cloud API
- Multi-agent roles (Supervisor, File Engineer, System Operator, Web Researcher, Verifier)
- Autonomous Tool-Calling / ReAct loop
"""

import os
import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from agentos.adapters.dynamic_tools import DynamicTools

load_dotenv()

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqAgentEngine:
    """Agent execution engine powered by Groq's high-speed API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        tools: Optional[DynamicTools] = None,
    ):
        self.api_key = (
            api_key
            or os.environ.get("GROQ_API_KEY")
            or os.environ.get("AGENTOS_MODEL_KEY")
            or ""
        ).strip()
        self.model = model or os.environ.get("AGENTOS_MODEL") or DEFAULT_GROQ_MODEL
        self.tools = tools or DynamicTools()

    def _salvage_failed_tool_call(self, raw: str) -> Optional[Dict[str, Any]]:
        """Attempt to salvage a truncated or unparsed tool call from Groq's failed_generation."""
        if not raw or not isinstance(raw, str):
            return None
        import re
        raw = raw.strip()
        name_match = re.search(r'"name"\s*:\s*"([^"]+)"', raw)
        fn_name = name_match.group(1) if name_match else ""
        if not fn_name:
            return None

        # 1. Try appending closing tokens directly
        candidates = ["", '"', '"}', '"]}', '"}]}', '"}]}}', '}}', ']}', ']}}']
        for suffix in candidates:
            try:
                candidate = raw + suffix
                parsed = json.loads(candidate)
                args = parsed.get("arguments", parsed)
                if isinstance(args, dict):
                    return self._wrap_tool_call_response(fn_name, args)
            except Exception:
                continue

        # 2. Try trimming back to the last complete dictionary item in a list (e.g. files: [...])
        last_comma = raw.rfind("},")
        if last_comma != -1:
            trimmed = raw[: last_comma + 1]
            for suffix in ["]}", "]}}", "}}"]:
                try:
                    candidate = trimmed + suffix
                    parsed = json.loads(candidate)
                    args = parsed.get("arguments", parsed)
                    if isinstance(args, dict):
                        return self._wrap_tool_call_response(fn_name, args)
                except Exception:
                    continue

        return None

    def _wrap_tool_call_response(self, fn_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Wrap salvaged function name and arguments into OpenAI/Groq response format."""
        return {
            "id": "salvaged_generation",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_salvaged",
                                "type": "function",
                                "function": {
                                    "name": fn_name,
                                    "arguments": json.dumps(args),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
        }

    def _call_groq_api(
        self,
        messages: List[Dict[str, Any]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """Send raw chat completion request to Groq."""
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured in .env or environment")

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools_schema:
            payload["tools"] = tools_schema
            payload["tool_choice"] = "auto"

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Content-Type": "application/json",
            },
            data=data_bytes,
        )

        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=45) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                err_msg = e.read().decode("utf-8", errors="ignore")
                break
            except Exception as conn_err:
                if attempt < 2:
                    import time
                    time.sleep(1.0)
                    continue
                raise conn_err
        else:
            raise RuntimeError("Request failed after retries")

            # If 400 tool_use_failed (truncated JSON generation in tool arguments), salvage or recover
            if e.code == 400 and ("tool_use_failed" in err_msg or "Failed to parse tool call arguments" in err_msg):
                try:
                    err_json = json.loads(err_msg)
                    failed_gen = err_json.get("error", {}).get("failed_generation", "")
                except Exception:
                    failed_gen = ""

                salvaged = self._salvage_failed_tool_call(failed_gen)
                if salvaged:
                    return salvaged

                # If cannot salvage, ask model to split actions into smaller tool calls
                retry_messages = list(messages)
                retry_messages.append({
                    "role": "user",
                    "content": (
                        "Your previous tool call arguments were cut off or too large. "
                        "Please perform the task using separate smaller tool calls: "
                        "create the folder first with create_directory, then create files individually with write_file."
                    ),
                })
                payload["messages"] = retry_messages
                payload["max_tokens"] = 3500
                retry_bytes = json.dumps(payload).encode("utf-8")
                retry_req = urllib.request.Request(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                        "Content-Type": "application/json",
                    },
                    data=retry_bytes,
                )
                try:
                    with urllib.request.urlopen(retry_req, timeout=45) as retry_res:
                        return json.loads(retry_res.read().decode("utf-8"))
                except urllib.error.HTTPError as re_400:
                    err_msg = re_400.read().decode("utf-8", errors="ignore")

            # If 413 or rate_limit_exceeded (TPM limit exceeded), reduce max_tokens and trim history
            if e.code == 413 or "rate_limit_exceeded" in err_msg or "TPM" in err_msg:
                reduced_tokens = 1000
                payload["max_tokens"] = reduced_tokens
                if len(messages) > 3:
                    payload["messages"] = [messages[0]] + messages[-3:]
                retry_bytes = json.dumps(payload).encode("utf-8")
                retry_req = urllib.request.Request(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                        "Content-Type": "application/json",
                    },
                    data=retry_bytes,
                )
                try:
                    with urllib.request.urlopen(retry_req, timeout=45) as retry_res:
                        return json.loads(retry_res.read().decode("utf-8"))
                except urllib.error.HTTPError as re:
                    err_msg = re.read().decode("utf-8", errors="ignore")

            # If 429 rate limit exceeded (TPM/RPM limit), wait for the window and retry
            if e.code == 429 or "rate_limit_exceeded" in err_msg:
                import time, re
                wait_time = 4.0
                match = re.search(r"try again in ([\d.]+)s", err_msg)
                if match:
                    wait_time = min(float(match.group(1)) + 1.0, 15.0)
                time.sleep(wait_time)
                payload["max_tokens"] = 1000
                if len(messages) > 3:
                    payload["messages"] = [messages[0]] + messages[-2:]
                retry_bytes = json.dumps(payload).encode("utf-8")
                retry_req = urllib.request.Request(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                        "Content-Type": "application/json",
                    },
                    data=retry_bytes,
                )
                try:
                    with urllib.request.urlopen(retry_req, timeout=45) as retry_res:
                        return json.loads(retry_res.read().decode("utf-8"))
                except urllib.error.HTTPError as re_err:
                    err_msg = re_err.read().decode("utf-8", errors="ignore")

            # If server overloaded (5xx), try fallback model
            if e.code in (500, 502, 503, 504) and self.model != "openai/gpt-oss-20b":
                self.model = "openai/gpt-oss-20b"
                payload["model"] = self.model
                payload["max_tokens"] = min(payload.get("max_tokens", 1500), 1000)
                data_bytes = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "User-Agent": "Mozilla/5.0",
                        "Content-Type": "application/json",
                    },
                    data=data_bytes,
                )
                try:
                    with urllib.request.urlopen(req, timeout=45) as fallback_res:
                        return json.loads(fallback_res.read().decode("utf-8"))
                except urllib.error.HTTPError as fe:
                    err_msg = fe.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Groq API Error {e.code}: {err_msg}") from e

    def _generate_smart_suggestions(
        self,
        user_prompt: str,
        reply: str,
        system_role: str,
        trace_logs: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate 3 contextual next-step prompts based on the current goal and result."""
        suggestions: List[str] = []
        lower_prompt = user_prompt.lower()

        # Check tools used in trace
        tools_used = [t.get("tool") for t in trace_logs if t.get("type") == "tool_call"]

        # 1. Project creation or file writing
        if any(t in ("create_project", "write_file", "patch_file") for t in tools_used) or any(w in lower_prompt for w in ["create", "build", "make", "write"]):
            suggestions.append("Check the status and structure of created files")
            suggestions.append("Run tests or syntax verification on the project")
            suggestions.append("Add more features or sample data to this project")
        # 2. Launching Desktop Applications
        elif "open_application" in tools_used or any(w in lower_prompt for w in ["open", "launch", "calc", "calculator", "notepad", "paint", "chrome"]):
            suggestions.append("Open Notepad on Windows")
            suggestions.append("Open Windows Terminal")
            suggestions.append("Open Windows Settings")
        # 3. Grocery & Blinkit Meal Planning
        elif "plan_and_order_blinkit_groceries" in tools_used or any(w in lower_prompt for w in ["grocery", "blinkit", "breakfast", "lunch", "dinner", "cart", "rashan"]):
            suggestions.append("Open Blinkit Cart in Google Chrome")
            suggestions.append("Add snacks, fruits & drinks to this list")
            suggestions.append("Plan healthy high-protein meals for tomorrow")
        # 4. Web search
        elif "web_search" in tools_used or any(w in lower_prompt for w in ["search", "google", "find online", "news", "price", "ipo"]):
            suggestions.append("Summarize key takeaways into bullet points")
            suggestions.append("Save these findings into a local markdown report")
            suggestions.append("Search for recent news or official documentation")
        # 3. Terminal or git commands
        elif "run_terminal_command" in tools_used or any(w in lower_prompt for w in ["terminal", "git", "test", "run", "status"]):
            suggestions.append("Show git diff of uncommitted changes")
            suggestions.append("Run the test suite with verbose output")
            suggestions.append("Explain any errors or warnings in the terminal output")
        # 4. Reading code or directory
        elif any(t in ("read_file", "list_directory", "search_code") for t in tools_used):
            suggestions.append("Explain the architecture of this component")
            suggestions.append("Identify areas for performance or security improvement")
            suggestions.append("Write unit tests for this module")
        # 5. General / Conversational fallback
        else:
            if any(w in lower_prompt for w in ["hello", "hi", "hey"]):
                suggestions.append("List project files in this workspace")
                suggestions.append("Create a Python SQLite application in D: drive")
                suggestions.append("Search DuckDuckGo for latest tech updates")
            elif any(w in lower_prompt for w in ["why", "how", "what", "explain"]):
                suggestions.append("Can you provide a working code example?")
                suggestions.append("How do I run and test this locally?")
                suggestions.append("What are alternative approaches to this?")
            else:
                suggestions.append("Inspect project directory and summarize structure")
                suggestions.append("Run project health check and diagnostics")
                suggestions.append("Create a new script or automated workflow")

        # Fallback if list is too small
        default_pool = [
            "Explain the next steps for this task",
            "Verify all files and run tests",
            "Show recent terminal and git status",
        ]
        for item in default_pool:
            if len(suggestions) < 3 and item not in suggestions:
                suggestions.append(item)

        return suggestions[:3]

    def run_agent(
        self,
        user_prompt: str,
        system_role: str = "supervisor",
        max_iterations: int = 5,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Run an autonomous agent loop with tool-calling capabilities and conversation memory."""

        system_prompts = {
            "supervisor": (
                "You are the AgentOS Chief Supervisor & Orchestrator. "
                "Break down goals into actionable steps, use your tools efficiently, "
                "and provide complete, accurate solutions in 1 to 3 steps."
            ),
            "file_engineer": (
                "You are the AgentOS File & Code Engineer. "
                "You specialize in reading, searching, writing, and refactoring project files. "
                "Inspect existing code before writing or editing files. Keep file operations concise."
            ),
            "system_operator": (
                "You are the AgentOS System & Terminal Operator. "
                "You run terminal commands, execute tests, check git status, and monitor environment processes safely."
            ),
            "web_researcher": (
                "You are the AgentOS Web Research Agent. "
                "CRITICAL INSTRUCTIONS:\n"
                "1. Always answer the user's SPECIFIC question directly. Never drift into giving generic textbook definitions.\n"
                "2. When asked about specific prices, company news, IPOs, or current market events:\n"
                "   - Run 1 targeted `web_search`.\n"
                "   - If the entity has NOT yet listed or is upcoming, state the exact factual status clearly.\n"
                "   - Report exact figures, dates, and citations directly to the user.\n"
                "3. Complete your answer in 1 or 2 tool calls maximum without looping."
            ),
            "project_architect": (
                "You are the AgentOS Project Architect & Full-Stack App Builder. "
                "You transform natural language specifications into complete, working, runnable software systems on the user's computer. "
                "When requested to create an app, project, or system (e.g. 'create a student management system in D drive'):\n"
                "1. Design a clean, modular structure (e.g., main app, database storage with SQLite, models, and a README).\n"
                "2. Call `create_project(project_dir=..., files=[...])` or use `create_directory` followed by `write_file` for each file.\n"
                "3. Optionally run syntax check using `run_terminal_command`.\n"
                "4. Provide the user with a summary of the created files and exact command to run the application."
            ),
            "verifier": (
                "You are the AgentOS Quality & Safety Verifier. "
                "Inspect files or run tests using 1 or 2 targeted tool calls (e.g., read_file or run_terminal_command), "
                "and then immediately output your verification summary, test results, and final pass/fail verdict."
            ),
            "grocery_chef": (
                "You are the AgentOS Grocery & Blinkit Meal Planning Agent. "
                "You plan meals for breakfast, lunch, and dinner, calculate all required grocery ingredients "
                "with sufficient quantities, and add them directly into the user's Blinkit shopping cart by calling "
                "`plan_and_order_blinkit_groceries(breakfast=..., lunch=..., dinner=..., servings=...)`. "
                "Always call `plan_and_order_blinkit_groceries` immediately when the user specifies dishes or requests grocery shopping."
            ),
        }

        base_instruction = (
            "You are an active, autonomous local AI agent operating inside AgentOS directly on the user's computer. "
            "You have REAL and DIRECT permissions to access the filesystem, search drives (like 'D:\\' or 'C:\\'), "
            "create projects, run PowerShell/shell commands, and read/write files via your available tools.\n\n"
            "CRITICAL OPERATING RULES:\n"
            "1. NEVER say 'I don't have access to your computer/laptop/file system'. You HAVE full access through your tools!\n"
            "2. NEVER reply with manual steps or tutorials when the user asked you to do a task. ACT immediately by calling your tools:\n"
            "   - To build a new app, project, or system: call `create_project(project_dir=..., files=[...])` or create directory and use `write_file` for each file.\n"
            "   - To create a directory: call `create_directory(dir_path=...)`.\n"
            "   - To find files across drives or folders (e.g. video files on 'D:\\'): call `find_files(pattern='*.mp4,*.mkv,*.avi', search_path='D:\\')`.\n"
            "   - When dishes for breakfast, lunch, or dinner are specified, or when grocery shopping is requested: call `plan_and_order_blinkit_groceries(breakfast=..., lunch=..., dinner=...)` to calculate ingredients and add them to the Blinkit cart.\n"
            "   - To launch or open any desktop application on Windows (like calculator, notepad, paint, chrome, vscode, explorer, terminal, settings): call `open_application(app_name=...)` immediately. For example, if asked 'open calculator', immediately call `open_application(app_name='calculator')`.\n"
            "   - To run system commands: call `run_terminal_command(command=...)`.\n"
            "   - To list folder contents: call `list_directory(dir_path=...)`.\n"
            "   - To search within code/text: call `search_code(query=...)`.\n"
            "   - To read/edit files: call `read_file`, `write_file`, or `patch_file`.\n"
            "   - To search the internet: call `web_search(query=...)`.\n"
            "3. Always report the actual created projects, files, and paths directly to the user."
        )

        sys_msg = f"{base_instruction}\n\nROLE FOCUS: {system_prompts.get(system_role, system_prompts['supervisor'])}"
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": sys_msg},
        ]

        # Inject previous conversation history for multi-turn context
        if history:
            for item in history[-6:]:
                h_role = item.get("role")
                h_content = item.get("content")
                if h_role in ("user", "assistant") and h_content and isinstance(h_content, str):
                    messages.append({"role": h_role, "content": h_content})

        messages.append({"role": "user", "content": user_prompt})

        tool_defs = self.tools.get_tool_definitions(role=system_role)
        trace_logs: List[Dict[str, Any]] = []

        def _safe_message_window(all_msgs: List[Dict[str, Any]], max_count: int = 10) -> List[Dict[str, Any]]:
            """Keep system + recent history and prevent orphaning 'tool' messages without their assistant call."""
            if len(all_msgs) <= max_count:
                return all_msgs
            head = [all_msgs[0]]
            tail = all_msgs[-(max_count - 1):]
            while tail and tail[0].get("role") == "tool":
                tail.pop(0)
            return head + tail

        for step in range(1, max_iterations + 1):
            current_messages = _safe_message_window(messages, max_count=9)

            res = self._call_groq_api(current_messages, tools_schema=tool_defs)
            choice = res["choices"][0]
            msg = choice["message"]
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning") or ""
            tool_calls = msg.get("tool_calls") or []

            messages.append(msg)

            if reasoning:
                trace_logs.append({"step": step, "type": "thought", "detail": reasoning})

            if not tool_calls:
                # Agent completed work without calling further tools
                trace_logs.append({"step": step, "type": "final_answer", "detail": content})
                suggestions = self._generate_smart_suggestions(
                    user_prompt=user_prompt,
                    reply=content,
                    system_role=system_role,
                    trace_logs=trace_logs,
                )
                return {
                    "status": "success",
                    "role": system_role,
                    "model": self.model,
                    "reply": content,
                    "reasoning": reasoning,
                    "trace": trace_logs,
                    "iterations": step,
                    "suggestions": suggestions,
                }

            # Handle Tool Calls
            for tool_call in tool_calls:
                fn_name = tool_call["function"]["name"]
                raw_args = tool_call["function"].get("arguments", "{}")
                try:
                    parsed_args = json.loads(raw_args)
                except Exception:
                    parsed_args = {}

                trace_logs.append({
                    "step": step,
                    "type": "tool_call",
                    "tool": fn_name,
                    "arguments": parsed_args,
                })

                # Execute Tool
                tool_output = self.tools.execute_tool(fn_name, parsed_args)
                output_str = json.dumps(tool_output, ensure_ascii=False)
                if len(output_str) > 3000:
                    output_str = output_str[:3000] + "\n... [Truncated: output trimmed to preserve TPM allowance]"

                trace_logs.append({
                    "step": step,
                    "type": "tool_result",
                    "tool": fn_name,
                    "result_snippet": output_str[:300],
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", f"call_{step}"),
                    "name": fn_name,
                    "content": output_str,
                })

        # If reached max iterations without final text, generate final synthesis without tool schema
        final_reply = content
        if not final_reply:
            try:
                tool_observations = []
                for t in trace_logs:
                    if t.get("type") == "tool_result":
                        tool_observations.append(f"- Tool '{t.get('tool')}': {t.get('result_snippet', '')}")
                obs_text = "\n".join(tool_observations[-6:]) if tool_observations else "No observations"

                final_messages = [
                    {"role": "system", "content": sys_msg},
                    {
                        "role": "user",
                        "content": (
                            f"Original User Request: {user_prompt}\n\n"
                            f"Live Research Gathered from Tools:\n{obs_text}\n\n"
                            "Based on the tool findings above, deliver the complete, factual final response now. "
                            "Directly answer the user's specific question. If an entity/stock is unlisted or upcoming, "
                            "state that clearly and report all known dates, price bands, and valuation figures."
                        ),
                    },
                ]
                final_res = self._call_groq_api(final_messages, max_tokens=1000)
                final_reply = final_res["choices"][0]["message"].get("content") or content
            except Exception:
                final_reply = content or f"Research completed. Findings: {obs_text[:500]}"

        suggestions = self._generate_smart_suggestions(
            user_prompt=user_prompt,
            reply=final_reply,
            system_role=system_role,
            trace_logs=trace_logs,
        )
        return {
            "status": "success" if final_reply else "partial",
            "role": system_role,
            "model": self.model,
            "reply": final_reply or "Completed requested actions.",
            "trace": trace_logs,
            "iterations": max_iterations,
            "suggestions": suggestions,
        }

    def run_agent_stream(
        self,
        user_prompt: str,
        system_role: str = "supervisor",
        max_iterations: int = 5,
        history: Optional[List[Dict[str, str]]] = None,
        engine: str = "groq",
        ollama_model: str = "llama3.2",
    ):
        """Run agent loop and yield real-time SSE events for thoughts, tool calls, and text tokens."""
        # 1. Check if offline Ollama is requested
        if engine == "ollama":
            import httpx
            ollama_url = "http://127.0.0.1:11434/api/chat"
            yield f"data: {json.dumps({'type': 'thought', 'text': f'Connecting to local offline Ollama ({ollama_model})...'})}\n\n"
            try:
                ollama_messages = [{"role": "system", "content": f"You are the AgentOS {system_role} agent running 100% offline."}]
                if history:
                    for h in history[-4:]:
                        ollama_messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
                ollama_messages.append({"role": "user", "content": user_prompt})

                with httpx.stream("POST", ollama_url, json={"model": ollama_model, "messages": ollama_messages}, timeout=60.0) as resp:
                    full_text = ""
                    for line in resp.iter_lines():
                        if line:
                            data = json.loads(line)
                            chunk = data.get("message", {}).get("content", "")
                            if chunk:
                                full_text += chunk
                                yield f"data: {json.dumps({'type': 'delta', 'text': chunk})}\n\n"

                    suggestions = self._generate_smart_suggestions(user_prompt, full_text, system_role, [])
                    yield f"data: {json.dumps({'type': 'done', 'reply': full_text, 'suggestions': suggestions, 'model': f'ollama/{ollama_model}', 'trace': []})}\n\n"
                    return
            except Exception as e:
                yield f"data: {json.dumps({'type': 'thought', 'text': f'Local Ollama is currently offline ({e}). Seamlessly switching to Groq Cloud...'})}\n\n"

        # 2. Groq Engine execution with streaming events
        system_prompts = {
            "supervisor": "You are the AgentOS Chief Supervisor & Orchestrator. Break down goals into actionable steps, use your tools efficiently, and provide complete, accurate solutions in 1 to 3 steps.",
            "file_engineer": "You are the AgentOS File & Code Engineer. You specialize in reading, searching, writing, and refactoring project files. Inspect existing code before writing or editing files. Keep file operations concise.",
            "system_operator": "You are the AgentOS System & Terminal Operator. You run terminal commands, execute tests, check git status, and monitor environment processes safely.",
            "web_researcher": "You are the AgentOS Web Research Agent. Answer the user's specific question directly. When asked about specific prices, company news, IPOs, or current market events, run 1 targeted web_search and report exact figures.",
            "project_architect": "You are the AgentOS Project Architect & Full-Stack App Builder. Transform natural language specifications into complete, working, runnable software systems on the user's computer.",
            "verifier": "You are the AgentOS Quality & Safety Verifier. Inspect files or run tests and immediately output verification summary.",
            "grocery_chef": "You are the AgentOS Grocery & Blinkit Meal Planning Agent. When breakfast, lunch, and dinner dishes are requested, calculate required ingredients and immediately call plan_and_order_blinkit_groceries to open Blinkit and add them to the cart.",
        }

        base_instruction = (
            "You are an active, autonomous local AI agent operating inside AgentOS directly on the user's computer. "
            "You have REAL and DIRECT permissions to access the filesystem, search drives (like 'D:\\' or 'C:\\'), "
            "create projects, run PowerShell/shell commands, launch Windows applications, and read/write files via your available tools.\n\n"
            "CRITICAL OPERATING RULES:\n"
            "1. NEVER say 'I don't have access to your computer/laptop/file system'. You HAVE full access through your tools!\n"
            "2. NEVER reply with manual steps or tutorials when the user asked you to do a task. ACT immediately by calling your tools.\n"
            "3. When dishes or groceries for breakfast, lunch, and dinner are requested: IMMEDIATELY call 'plan_and_order_blinkit_groceries(breakfast=..., lunch=..., dinner=...)' to calculate ingredients and add them to Blinkit.\n"
            "4. When the user asks to open, run, or launch an application on their Windows computer (such as 'open calculator', 'open notepad', 'launch chrome', 'open vscode', 'open explorer', 'open terminal', etc.), IMMEDIATELY call the 'open_application' tool with the app_name.\n"
            "4. Always report the actual created projects, files, launched applications, and paths directly to the user."
        )

        sys_msg = f"{base_instruction}\n\nROLE FOCUS: {system_prompts.get(system_role, system_prompts['supervisor'])}"
        messages: List[Dict[str, Any]] = [{"role": "system", "content": sys_msg}]

        if history:
            for item in history[-6:]:
                h_role = item.get("role")
                h_content = item.get("content")
                if h_role in ("user", "assistant") and h_content and isinstance(h_content, str):
                    messages.append({"role": h_role, "content": h_content})

        messages.append({"role": "user", "content": user_prompt})
        tool_defs = self.tools.get_tool_definitions(role=system_role)
        trace_logs: List[Dict[str, Any]] = []

        def _safe_message_window(all_msgs: List[Dict[str, Any]], max_count: int = 10) -> List[Dict[str, Any]]:
            if len(all_msgs) <= max_count:
                return all_msgs
            head = [all_msgs[0]]
            tail = all_msgs[-(max_count - 1):]
            while tail and tail[0].get("role") == "tool":
                tail.pop(0)
            return head + tail

        yield f"data: {json.dumps({'type': 'thought', 'step': 1, 'text': f'Active persona: {system_role}. Connected to Groq Cloud ({self.model}).'})}\n\n"

        for step in range(1, max_iterations + 1):
            current_messages = _safe_message_window(messages, max_count=9)
            res = self._call_groq_api(current_messages, tools_schema=tool_defs)
            choice = res["choices"][0]
            msg = choice["message"]
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning") or ""
            tool_calls = msg.get("tool_calls") or []

            messages.append(msg)

            if reasoning:
                trace_logs.append({"step": step, "type": "thought", "detail": reasoning})
                yield f"data: {json.dumps({'type': 'thought', 'step': step, 'text': reasoning})}\n\n"

            if not tool_calls:
                trace_logs.append({"step": step, "type": "final_answer", "detail": content})
                chunk_size = 32
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i + chunk_size]
                    yield f"data: {json.dumps({'type': 'delta', 'text': chunk})}\n\n"

                suggestions = self._generate_smart_suggestions(
                    user_prompt=user_prompt,
                    reply=content,
                    system_role=system_role,
                    trace_logs=trace_logs,
                )
                yield f"data: {json.dumps({'type': 'done', 'reply': content, 'suggestions': suggestions, 'trace': trace_logs, 'model': self.model})}\n\n"
                return

            # Tool Calls
            for tool_call in tool_calls:
                fn_name = tool_call["function"]["name"]
                raw_args = tool_call["function"].get("arguments", "{}")
                try:
                    parsed_args = json.loads(raw_args)
                except Exception:
                    parsed_args = {}

                # Check Safe Risk Assessment
                risk = self.tools.check_tool_risk(fn_name, parsed_args)
                if risk.get("requires_approval"):
                    yield f"data: {json.dumps({'type': 'approval_notice', 'tool': fn_name, 'risk': risk.get('risk_level', 'high'), 'reason': risk.get('reason')})}\n\n"

                yield f"data: {json.dumps({'type': 'tool_call', 'step': step, 'tool': fn_name, 'args': parsed_args})}\n\n"

                trace_logs.append({
                    "step": step,
                    "type": "tool_call",
                    "tool": fn_name,
                    "arguments": parsed_args,
                })

                # Execute Tool
                tool_output = self.tools.execute_tool(fn_name, parsed_args)
                output_str = json.dumps(tool_output, ensure_ascii=False)
                if len(output_str) > 3000:
                    output_str = output_str[:3000] + "\n... [Truncated: output trimmed to preserve TPM allowance]"

                yield f"data: {json.dumps({'type': 'tool_result', 'step': step, 'tool': fn_name, 'snippet': output_str[:300]})}\n\n"

                trace_logs.append({
                    "step": step,
                    "type": "tool_result",
                    "tool": fn_name,
                    "result_snippet": output_str[:300],
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", f"call_{step}"),
                    "name": fn_name,
                    "content": output_str,
                })

        # Final synthesis
        final_reply = content
        if not final_reply:
            try:
                tool_observations = []
                for t in trace_logs:
                    if t.get("type") == "tool_result":
                        tool_observations.append(f"- Tool '{t.get('tool')}': {t.get('result_snippet', '')}")
                obs_text = "\n".join(tool_observations[-6:]) if tool_observations else "No observations"

                final_messages = [
                    {"role": "system", "content": sys_msg},
                    {
                        "role": "user",
                        "content": (
                            f"Original User Request: {user_prompt}\n\n"
                            f"Live Research Gathered from Tools:\n{obs_text}\n\n"
                            "Based on the tool findings above, deliver the complete, factual final response now."
                        ),
                    },
                ]
                final_res = self._call_groq_api(final_messages, max_tokens=1000)
                final_reply = final_res["choices"][0]["message"].get("content") or content
            except Exception:
                final_reply = content or f"Research completed. Findings: {obs_text[:500]}"

        chunk_size = 32
        for i in range(0, len(final_reply), chunk_size):
            chunk = final_reply[i:i + chunk_size]
            yield f"data: {json.dumps({'type': 'delta', 'text': chunk})}\n\n"

        suggestions = self._generate_smart_suggestions(
            user_prompt=user_prompt,
            reply=final_reply,
            system_role=system_role,
            trace_logs=trace_logs,
        )
        yield f"data: {json.dumps({'type': 'done', 'reply': final_reply, 'suggestions': suggestions, 'trace': trace_logs, 'model': self.model})}\n\n"

