"""Session manager for tracking coding agent tasks, lifecycles, and change attribution."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.models import AgentSession, ChangeEvent


class SessionManager:
    def __init__(self, store: SQLiteStore, repo_id: str = "default") -> None:
        self.store = store
        self.repo_id = repo_id

    def start_session(
        self,
        agent_name: str,
        task_description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> AgentSession:
        sid = session_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        session = AgentSession(
            id=sid,
            repo_id=self.repo_id,
            agent_name=agent_name,
            task_description=task_description,
            started_at=now,
            ended_at=None,
            status="active",
            metadata=metadata or {},
        )
        self.store.create_session(session)
        return session

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        return self.store.get_session(self.repo_id, session_id)

    def get_active_session(self) -> Optional[AgentSession]:
        sessions = self.store.list_sessions(self.repo_id, limit=10)
        for s in sessions:
            if s.status == "active":
                return s
        return None

    def end_session(self, session_id: str, status: str = "completed") -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.store.update_session(
            self.repo_id,
            session_id,
            status=status,
            ended_at=now,
        )

    def update_task_description(self, session_id: str, description: str) -> None:
        self.store.update_session(
            self.repo_id,
            session_id,
            task_description=description,
        )

    def list_sessions(self, limit: int = 50) -> List[AgentSession]:
        return self.store.list_sessions(self.repo_id, limit=limit)

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Calculates file, symbol, and diff statistics for an agent session."""
        session = self.get_session(session_id)
        if not session:
            return {}

        events = self.store.get_session_events(self.repo_id, session_id)
        files_affected = sorted(list({e.file_path for e in events}))
        symbols_affected = sorted(list({e.symbol_id for e in events if e.symbol_id}))

        event_types: Dict[str, int] = {}
        for e in events:
            event_types[e.event_type] = event_types.get(e.event_type, 0) + 1

        return {
            "session_id": session.id,
            "agent_name": session.agent_name,
            "task_description": session.task_description,
            "status": session.status,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "files_affected_count": len(files_affected),
            "files_affected": files_affected,
            "symbols_affected_count": len(symbols_affected),
            "symbols_affected": symbols_affected,
            "events_count": len(events),
            "event_breakdown": event_types,
            "events": [e.model_dump() for e in events],
        }
