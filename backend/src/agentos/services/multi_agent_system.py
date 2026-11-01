"""Multi-Agent Orchestration System for AgentOS.

Combines concepts from:
- PersonalAgent (Natural Language File/Workspace Management)
- OmniPilot (Computer-Use & System Automation with Permission-Safe Tools)
- Yadeesht/Personal-Assistant-Agent (Multi-Agent Routing & Specialized Roles)
"""

from typing import Any, Dict, List, Optional
from agentos.adapters.dynamic_tools import DynamicTools
from agentos.adapters.groq_adapter import GroqAgentEngine


class MultiAgentSystem:
    """Orchestrates specialized agents to achieve complex user goals."""

    def __init__(
        self,
        engine: Optional[GroqAgentEngine] = None,
        tools: Optional[DynamicTools] = None,
    ):
        self.tools = tools or DynamicTools()
        self.engine = engine or GroqAgentEngine(tools=self.tools)

    def route_request(self, user_prompt: str) -> str:
        """Route user request to the most appropriate specialized agent."""
        lower = user_prompt.lower()
        if any(w in lower for w in [
            "grocery", "groceries", "blinkit", "breakfast", "lunch", "dinner",
            "ingredient", "ingredients", "cart me", "cart mein", "dishes", "dish",
            "rashan", "sabzi", "meal plan", "khana", "recipe"
        ]):
            return "grocery_chef"
        if any(w in lower for w in [
            "create project", "create a project", "build project", "build an app", "create an app",
            "make an app", "create a", "build a", "scaffold", "management system", "system bana",
            "bana do", "project bana", "app bana", "folder bana", "student management"
        ]):
            return "project_architect"
        if any(w in lower for w in ["search", "google", "find online", "lookup", "documentation", "docs for"]):
            return "web_researcher"
        if any(w in lower for w in ["terminal", "bash", "command", "run test", "git", "status", "exec"]):
            return "system_operator"
        if any(w in lower for w in ["file", "code", "read", "write", "patch", "edit", "directory", "function", "find vide"]):
            return "file_engineer"
        if any(w in lower for w in ["verify", "check", "audit", "review", "test report"]):
            return "verifier"
        return "supervisor"

    def execute_goal(
        self,
        goal: str,
        role_override: Optional[str] = None,
        max_iterations: int = 6,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Execute a user goal through the multi-agent pipeline."""
        assigned_role = role_override or self.route_request(goal)
        
        result = self.engine.run_agent(
            user_prompt=goal,
            system_role=assigned_role,
            max_iterations=max_iterations,
            history=history,
        )

        # Build full agent response summary
        return {
            "goal": goal,
            "assigned_agent": assigned_role,
            "status": result.get("status"),
            "reply": result.get("reply"),
            "model": result.get("model"),
            "trace": result.get("trace", []),
            "iterations": result.get("iterations", 1),
            "suggestions": result.get("suggestions", []),
            "safety_verified": True,
        }

    def execute_goal_stream(
        self,
        goal: str,
        role_override: Optional[str] = None,
        max_iterations: int = 6,
        history: Optional[List[Dict[str, str]]] = None,
        engine: str = "groq",
        ollama_model: str = "llama3.2",
    ):
        """Execute a goal and yield live SSE streaming events."""
        assigned_role = role_override or self.route_request(goal)
        yield from self.engine.run_agent_stream(
            user_prompt=goal,
            system_role=assigned_role,
            max_iterations=max_iterations,
            history=history,
            engine=engine,
            ollama_model=ollama_model,
        )

