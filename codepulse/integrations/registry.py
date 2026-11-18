"""Agent adapter registry and discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from codepulse.integrations.antigravity import AntigravityAdapter
from codepulse.integrations.base_adapter import BaseAgentAdapter
from codepulse.integrations.claude_code import ClaudeCodeAdapter
from codepulse.integrations.codex import CodexAdapter
from codepulse.integrations.cursor import CursorAdapter
from codepulse.integrations.generic_git import GenericGitAdapter


class AgentRegistry:
    def __init__(self) -> None:
        self.adapters: Dict[str, BaseAgentAdapter] = {}
        self.register(ClaudeCodeAdapter())
        self.register(CursorAdapter())
        self.register(CodexAdapter())
        self.register(AntigravityAdapter())
        self.register(GenericGitAdapter())

    def register(self, adapter: BaseAgentAdapter) -> None:
        self.adapters[adapter.name] = adapter

    def get_adapter(self, name: str) -> Optional[BaseAgentAdapter]:
        return self.adapters.get(name)

    def list_adapters(self) -> List[BaseAgentAdapter]:
        return list(self.adapters.values())

    def get_status(self, repo_path: Path) -> List[Dict[str, Any]]:
        results = []
        for a in self.adapters.values():
            results.append({
                "name": a.name,
                "display_name": a.display_name,
                "installed": a.detect_installed(),
                "hooked": a.is_hooked(repo_path),
            })
        return results

    def detect_active_agent(self, repo_path: Path) -> str:
        """Detects if any agent has active session evidence in repo."""
        for a in self.adapters.values():
            if a.read_active_session(repo_path) is not None:
                return a.name
        return "unknown"


default_registry = AgentRegistry()
