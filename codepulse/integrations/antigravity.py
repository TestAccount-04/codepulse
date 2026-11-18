"""Antigravity coding agent integration adapter."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from codepulse.integrations.base_adapter import BaseAgentAdapter


class AntigravityAdapter(BaseAgentAdapter):
    @property
    def name(self) -> str:
        return "antigravity"

    @property
    def display_name(self) -> str:
        return "Antigravity"

    def detect_installed(self) -> bool:
        # Check standard user gemini/antigravity directory
        user_home = Path.home()
        antigravity_dir = user_home / ".gemini" / "antigravity"
        return antigravity_dir.is_dir() or "ANTIGRAVITY_APP_DATA" in os.environ

    def _get_hook_path(self, repo_path: Path) -> Path:
        return repo_path / ".codepulse" / "antigravity.json"

    def is_hooked(self, repo_path: Path) -> bool:
        return self._get_hook_path(repo_path).is_file()

    def install_hook(self, repo_path: Path) -> bool:
        hook_file = self._get_hook_path(repo_path)
        hook_file.parent.mkdir(parents=True, exist_ok=True)
        config = {
            "integration": "antigravity",
            "active": True,
            "session_source": "auto",
        }
        hook_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return True

    def uninstall_hook(self, repo_path: Path) -> bool:
        hook_file = self._get_hook_path(repo_path)
        if hook_file.is_file():
            hook_file.unlink()
            return True
        return False

    def read_active_session(self, repo_path: Path) -> Optional[Dict[str, Any]]:
        # Read from .codepulse/active_session.json if populated
        session_file = repo_path / ".codepulse" / "active_session.json"
        if session_file.is_file():
            try:
                return json.loads(session_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None
