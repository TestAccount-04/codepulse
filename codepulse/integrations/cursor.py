"""Cursor AI editor integration adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
from codepulse.integrations.base_adapter import BaseAgentAdapter


class CursorAdapter(BaseAgentAdapter):
    @property
    def name(self) -> str:
        return "cursor"

    @property
    def display_name(self) -> str:
        return "Cursor"

    def detect_installed(self) -> bool:
        return self.is_command_available("cursor")

    def _get_hook_path(self, repo_path: Path) -> Path:
        return repo_path / ".cursor" / "codepulse.json"

    def is_hooked(self, repo_path: Path) -> bool:
        return self._get_hook_path(repo_path).is_file()

    def install_hook(self, repo_path: Path) -> bool:
        hook_file = self._get_hook_path(repo_path)
        hook_file.parent.mkdir(parents=True, exist_ok=True)
        config = {
            "integration": "codepulse",
            "version": "0.1.0",
            "observer": "active",
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
        session_file = repo_path / ".cursor" / "session.json"
        if session_file.is_file():
            try:
                return json.loads(session_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None
