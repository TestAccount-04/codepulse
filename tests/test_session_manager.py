"""Tests for SessionManager task correlation and session summary."""

from pathlib import Path
from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.models import ChangeEvent
from codepulse.core.session_manager.manager import SessionManager


def test_session_lifecycle(tmp_path: Path):
    db_file = tmp_path / "test.db"
    store = SQLiteStore(db_file)
    session_mgr = SessionManager(store, repo_id="test_repo")

    # 1. Start session
    session = session_mgr.start_session(
        agent_name="claude-code",
        task_description="Implement user authentication flow",
    )
    assert session.id is not None
    assert session.agent_name == "claude-code"
    assert session.status == "active"

    # 2. Get active session
    active = session_mgr.get_active_session()
    assert active is not None
    assert active.id == session.id

    # 3. Update task description
    session_mgr.update_task_description(session.id, "Refactored user authentication")
    updated = session_mgr.get_session(session.id)
    assert updated is not None
    assert updated.task_description == "Refactored user authentication"

    # 4. Associate change events with session
    store.record_change_event(
        ChangeEvent(
            id="ev-1",
            repo_id="test_repo",
            timestamp="2026-11-18T10:00:00Z",
            event_type="added",
            file_path="src/auth.py",
            symbol_id="src/auth.py::function::login",
            session_id=session.id,
            agent_name="claude-code",
            summary="Added login()",
        )
    )

    # 5. Check session summary
    summary = session_mgr.get_session_summary(session.id)
    assert summary["files_affected_count"] == 1
    assert "src/auth.py" in summary["files_affected"]
    assert summary["symbols_affected_count"] == 1
    assert summary["event_breakdown"].get("added") == 1

    # 6. End session
    session_mgr.end_session(session.id, status="completed")
    ended = session_mgr.get_session(session.id)
    assert ended is not None
    assert ended.status == "completed"
    assert ended.ended_at is not None
    assert session_mgr.get_active_session() is None
