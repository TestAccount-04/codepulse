"""Tests for ChangeCoordinator end-to-end change workflow and impact propagation."""

from pathlib import Path
from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.change_detector.coordinator import ChangeCoordinator
from codepulse.core.models import ChangeStatus, SymbolType


def test_coordinator_handles_modification_and_impact(tmp_path: Path):
    db_file = tmp_path / ".codepulse" / "codepulse.db"
    store = SQLiteStore(db_file)
    coordinator = ChangeCoordinator(tmp_path, store, repo_id="test")

    # Create initial files: caller.py and callee.py
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)

    callee_file = src_dir / "callee.py"
    callee_file.write_text(
        "def fetch_data():\n    return [1, 2, 3]\n",
        encoding="utf-8",
    )

    caller_file = src_dir / "caller.py"
    caller_file.write_text(
        "def process():\n    return fetch_data()\n",
        encoding="utf-8",
    )

    # Initial baseline
    baseline = coordinator.capture_baseline()
    assert baseline is not None

    # Verify initial symbols exist and are unchanged
    callee_syms = store.get_symbols_by_file("test", "src/callee.py")
    assert any(s.name == "fetch_data" for s in callee_syms)

    # Modify callee.py
    callee_file.write_text(
        "def fetch_data():\n    # updated implementation\n    return [1, 2, 3, 4]\n",
        encoding="utf-8",
    )

    diffs = coordinator.handle_file_change(
        event_type="modified",
        rel_path="src/callee.py",
        session_id="session-123",
        agent_name="test-agent",
    )

    assert len(diffs) > 0
    fetch_diff = next(d for d in diffs if d.symbol_name == "fetch_data")
    assert fetch_diff.status == ChangeStatus.MODIFIED

    # Check change events recorded in SQLite
    events = store.list_change_events("test")
    assert len(events) >= 1
    assert any(e.symbol_id == fetch_diff.symbol_id for e in events)
    assert any(e.agent_name == "test-agent" for e in events)


def test_coordinator_handles_file_deletion(tmp_path: Path):
    db_file = tmp_path / ".codepulse" / "codepulse.db"
    store = SQLiteStore(db_file)
    coordinator = ChangeCoordinator(tmp_path, store, repo_id="test")

    temp_file = tmp_path / "temp.py"
    temp_file.write_text("def temporary_function(): pass\n", encoding="utf-8")

    coordinator.capture_baseline()
    assert len(store.get_symbols_by_file("test", "temp.py")) >= 1

    # Delete file
    temp_file.unlink()
    diffs = coordinator.handle_file_change("deleted", "temp.py")

    assert any(d.status == ChangeStatus.DELETED for d in diffs)
    # File symbols should be cleaned from store
    assert len(store.get_symbols_by_file("test", "temp.py")) == 0
