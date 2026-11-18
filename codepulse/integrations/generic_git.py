"""Generic Git and human commit integration adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
from codepulse.integrations.base_adapter import BaseAgentAdapter


class GenericGitAdapter(BaseAgentAdapter):
    @property
    def name(self) -> str:
        return "generic-git"

    @property
    def display_name(self) -> str:
        return "Generic Git"

    def detect_installed(self) -> bool:
        return self.is_command_available("git")

    def _get_hook_path(self, repo_path: Path) -> Path:
        return repo_path / ".git" / "hooks" / "post-commit"

    def is_hooked(self, repo_path: Path) -> bool:
        hook_file = self._get_hook_path(repo_path)
        if hook_file.is_file():
            content = hook_file.read_text(encoding="utf-8", errors="replace")
            return "codepulse" in content
        return False

    def install_hook(self, repo_path: Path) -> bool:
        hook_file = self._get_hook_path(repo_path)
        hook_file.parent.mkdir(parents=True, exist_ok=True)

        existing = ""
        if hook_file.is_file():
            existing = hook_file.read_text(encoding="utf-8", errors="replace")
            if "codepulse" in existing:
                return True

        hook_script = "#!/bin/sh\n# CodePulse auto-hook\ncodepulse scan 2>/dev/null || true\n"
        full_content = (existing + "\n" + hook_script) if existing else hook_script

        hook_file.write_text(full_content, encoding="utf-8")
        try:
            # Set executable on Unix/Mac
            hook_file.chmod(0o755)
        except Exception:
            pass
        return True

    def uninstall_hook(self, repo_path: Path) -> bool:
        hook_file = self._get_hook_path(repo_path)
        if not hook_file.is_file():
            return False

        content = hook_file.read_text(encoding="utf-8", errors="replace")
        lines = [line for line in content.splitlines() if "codepulse" not in line]
        if not lines or (len(lines) == 1 and lines[0].startswith("#!")):
            hook_file.unlink()
        else:
            hook_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True

    def read_active_session(self, repo_path: Path) -> Optional[Dict[str, Any]]:
        return None
