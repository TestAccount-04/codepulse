"""Tests for AI agent integrations, hook installation, and registry."""

from pathlib import Path
from codepulse.integrations.antigravity import AntigravityAdapter
from codepulse.integrations.claude_code import ClaudeCodeAdapter
from codepulse.integrations.codex import CodexAdapter
from codepulse.integrations.cursor import CursorAdapter
from codepulse.integrations.generic_git import GenericGitAdapter
from codepulse.integrations.registry import AgentRegistry


def test_agent_adapters_hook_lifecycle(tmp_path: Path):
    adapters = [
        ClaudeCodeAdapter(),
        CursorAdapter(),
        CodexAdapter(),
        AntigravityAdapter(),
        GenericGitAdapter(),
    ]

    for adapter in adapters:
        # Initially not hooked
        assert adapter.is_hooked(tmp_path) is False

        # Install hook
        installed = adapter.install_hook(tmp_path)
        assert installed is True
        assert adapter.is_hooked(tmp_path) is True

        # Uninstall hook
        uninstalled = adapter.uninstall_hook(tmp_path)
        assert uninstalled is True
        assert adapter.is_hooked(tmp_path) is False


def test_agent_registry(tmp_path: Path):
    registry = AgentRegistry()
    adapters = registry.list_adapters()
    assert len(adapters) >= 5

    names = {a.name for a in adapters}
    assert "claude-code" in names
    assert "cursor" in names
    assert "codex" in names
    assert "antigravity" in names
    assert "generic-git" in names

    # Status check
    status = registry.get_status(tmp_path)
    assert len(status) >= 5
    assert all("hooked" in s for s in status)

    # Active agent detection fallback
    active_agent = registry.detect_active_agent(tmp_path)
    assert active_agent == "unknown"
