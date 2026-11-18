"""Base adapter interface for AI coding agent integrations."""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional


class BaseAgentAdapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Machine identifier (e.g. 'claude-code', 'cursor', etc.)."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name."""
        pass

    @abstractmethod
    def detect_installed(self) -> bool:
        """Checks if the agent CLI or environment is present on system."""
        pass

    @abstractmethod
    def is_hooked(self, repo_path: Path) -> bool:
        """Checks if CodePulse hooks/instrumentation are installed in repo."""
        pass

    @abstractmethod
    def install_hook(self, repo_path: Path) -> bool:
        """Installs non-destructive hooks or configuration in repo."""
        pass

    @abstractmethod
    def uninstall_hook(self, repo_path: Path) -> bool:
        """Cleans up hooks or configuration from repo."""
        pass

    @abstractmethod
    def read_active_session(self, repo_path: Path) -> Optional[Dict[str, Any]]:
        """Reads session or prompt metadata if currently active."""
        pass

    @staticmethod
    def is_command_available(cmd: str) -> bool:
        return shutil.which(cmd) is not None
