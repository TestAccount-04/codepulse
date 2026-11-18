"""Local SQLite storage manager for CodePulse symbol graphs and repository metadata."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from codepulse.backend.storage.schema import SCHEMA_SQL
from codepulse.core.models import (
    AgentSession,
    ChangeEvent,
    ChangeStatus,
    FileInfo,
    ParseResult,
    Relationship,
    RelationshipType,
    RepositoryMetrics,
    Symbol,
    SymbolType,
)


class SQLiteStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize(self) -> None:
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)

    def register_repository(self, repo_id: str, root_path: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO repositories (id, root_path, created_at, last_scanned_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET root_path = excluded.root_path
                """,
                (repo_id, str(root_path), now, None),
            )

    def update_last_scanned(self, repo_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE repositories SET last_scanned_at = ? WHERE id = ?",
                (now, repo_id),
            )

    def upsert_file(self, repo_id: str, file_info: FileInfo) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO files (repo_id, path, sha256, mtime, size_bytes, language, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(repo_id, path) DO UPDATE SET
                    sha256 = excluded.sha256,
                    mtime = excluded.mtime,
                    size_bytes = excluded.size_bytes,
                    language = excluded.language,
                    is_deleted = excluded.is_deleted
                """,
                (
                    repo_id,
                    file_info.path,
                    file_info.sha256,
                    file_info.mtime,
                    file_info.size_bytes,
                    file_info.language,
                    1 if file_info.is_deleted else 0,
                ),
            )

    def get_file(self, repo_id: str, path: str) -> Optional[FileInfo]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM files WHERE repo_id = ? AND path = ?",
                (repo_id, path),
            ).fetchone()
            if not row:
                return None
            return FileInfo(
                path=row["path"],
                sha256=row["sha256"],
                mtime=row["mtime"],
                size_bytes=row["size_bytes"],
                language=row["language"],
                is_deleted=bool(row["is_deleted"]),
            )

    def list_files(self, repo_id: str, include_deleted: bool = False) -> List[FileInfo]:
        with self.get_connection() as conn:
            query = "SELECT * FROM files WHERE repo_id = ?"
            if not include_deleted:
                query += " AND is_deleted = 0"
            rows = conn.execute(query, (repo_id,)).fetchall()
            return [
                FileInfo(
                    path=row["path"],
                    sha256=row["sha256"],
                    mtime=row["mtime"],
                    size_bytes=row["size_bytes"],
                    language=row["language"],
                    is_deleted=bool(row["is_deleted"]),
                )
                for row in rows
            ]

    def delete_file_data(self, repo_id: str, file_path: str) -> None:
        """Removes symbols and relations originating from a specific file."""
        with self.get_connection() as conn:
            # Delete relationships where source symbol belongs to this file
            conn.execute(
                """
                DELETE FROM relationships
                WHERE repo_id = ? AND source_id IN (
                    SELECT id FROM symbols WHERE repo_id = ? AND file_path = ?
                )
                """,
                (repo_id, repo_id, file_path),
            )
            # Delete symbols for this file
            conn.execute(
                "DELETE FROM symbols WHERE repo_id = ? AND file_path = ?",
                (repo_id, file_path),
            )

    def save_parse_result(self, repo_id: str, parse_result: ParseResult) -> None:
        """Atomically saves file record, symbols, and relationships."""
        with self.get_connection() as conn:
            file_info = parse_result.file_info
            conn.execute(
                """
                INSERT INTO files (repo_id, path, sha256, mtime, size_bytes, language, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(repo_id, path) DO UPDATE SET
                    sha256 = excluded.sha256,
                    mtime = excluded.mtime,
                    size_bytes = excluded.size_bytes,
                    language = excluded.language,
                    is_deleted = excluded.is_deleted
                """,
                (
                    repo_id,
                    file_info.path,
                    file_info.sha256,
                    file_info.mtime,
                    file_info.size_bytes,
                    file_info.language,
                    1 if file_info.is_deleted else 0,
                ),
            )

            # Purge existing symbols/edges for this file to ensure clean incremental update
            conn.execute(
                """
                DELETE FROM relationships
                WHERE repo_id = ? AND source_id IN (
                    SELECT id FROM symbols WHERE repo_id = ? AND file_path = ?
                )
                """,
                (repo_id, repo_id, file_info.path),
            )
            conn.execute(
                "DELETE FROM symbols WHERE repo_id = ? AND file_path = ?",
                (repo_id, file_info.path),
            )

            # Insert symbols
            for sym in parse_result.symbols:
                conn.execute(
                    """
                    INSERT INTO symbols (
                        id, repo_id, file_path, name, symbol_type, parent_symbol_id,
                        start_line, end_line, start_byte, end_byte, signature,
                        docstring, content_hash, change_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sym.id,
                        repo_id,
                        sym.file_path,
                        sym.name,
                        sym.symbol_type.value,
                        sym.parent_symbol_id,
                        sym.start_line,
                        sym.end_line,
                        sym.start_byte,
                        sym.end_byte,
                        sym.signature,
                        sym.docstring,
                        sym.content_hash,
                        sym.change_status.value,
                    ),
                )

            # Insert relationships
            for rel in parse_result.relationships:
                conn.execute(
                    """
                    INSERT INTO relationships (repo_id, source_id, target_id, relationship_type, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        repo_id,
                        rel.source_id,
                        rel.target_id,
                        rel.relationship_type.value,
                        json.dumps(rel.metadata),
                    ),
                )

    def get_symbol_by_id(self, repo_id: str, symbol_id: str) -> Optional[Symbol]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM symbols WHERE repo_id = ? AND id = ?",
                (repo_id, symbol_id),
            ).fetchone()
            if not row:
                return None
            return self._row_to_symbol(row)

    def get_symbols_by_file(self, repo_id: str, file_path: str) -> List[Symbol]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM symbols WHERE repo_id = ? AND file_path = ? ORDER BY start_line ASC",
                (repo_id, file_path),
            ).fetchall()
            return [self._row_to_symbol(r) for r in rows]

    def list_symbols(
        self,
        repo_id: str,
        symbol_type: Optional[SymbolType] = None,
        file_path: Optional[str] = None,
    ) -> List[Symbol]:
        with self.get_connection() as conn:
            query = "SELECT * FROM symbols WHERE repo_id = ?"
            params: List[Any] = [repo_id]
            if symbol_type:
                query += " AND symbol_type = ?"
                params.append(symbol_type.value)
            if file_path:
                query += " AND file_path = ?"
                params.append(file_path)
            query += " ORDER BY file_path ASC, start_line ASC"
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_symbol(r) for r in rows]

    def get_relationships(
        self,
        repo_id: str,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        rel_type: Optional[RelationshipType] = None,
    ) -> List[Relationship]:
        with self.get_connection() as conn:
            query = "SELECT * FROM relationships WHERE repo_id = ?"
            params: List[Any] = [repo_id]
            if source_id:
                query += " AND source_id = ?"
                params.append(source_id)
            if target_id:
                query += " AND target_id = ?"
                params.append(target_id)
            if rel_type:
                query += " AND relationship_type = ?"
                params.append(rel_type.value)
            rows = conn.execute(query, params).fetchall()
            return [
                Relationship(
                    id=row["id"],
                    source_id=row["source_id"],
                    target_id=row["target_id"],
                    relationship_type=RelationshipType(row["relationship_type"]),
                    metadata=json.loads(row["metadata"] or "{}"),
                )
                for row in rows
            ]

    def record_change_event(self, event: ChangeEvent) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO repositories (id, root_path, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (event.repo_id, "", event.timestamp),
            )
            if event.session_id:
                conn.execute(
                    """
                    INSERT INTO sessions (id, repo_id, agent_name, started_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO NOTHING
                    """,
                    (event.session_id, event.repo_id, event.agent_name, event.timestamp),
                )
            conn.execute(
                """
                INSERT INTO change_events (
                    id, repo_id, timestamp, event_type, file_path,
                    symbol_id, session_id, agent_name, diff_content, summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.repo_id,
                    event.timestamp,
                    event.event_type,
                    event.file_path,
                    event.symbol_id,
                    event.session_id,
                    event.agent_name,
                    event.diff_content,
                    event.summary,
                ),
            )

    def list_change_events(
        self,
        repo_id: str,
        limit: int = 50,
        file_path: Optional[str] = None,
    ) -> List[ChangeEvent]:
        with self.get_connection() as conn:
            query = "SELECT * FROM change_events WHERE repo_id = ?"
            params: List[Any] = [repo_id]
            if file_path:
                query += " AND file_path = ?"
                params.append(file_path)
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [
                ChangeEvent(
                    id=r["id"],
                    repo_id=r["repo_id"],
                    timestamp=r["timestamp"],
                    event_type=r["event_type"],
                    file_path=r["file_path"],
                    symbol_id=r["symbol_id"],
                    session_id=r["session_id"],
                    agent_name=r["agent_name"],
                    diff_content=r["diff_content"],
                    summary=r["summary"],
                )
                for r in rows
            ]

    def create_session(self, session: AgentSession) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO repositories (id, root_path, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (session.repo_id, "", session.started_at),
            )
            conn.execute(
                """
                INSERT INTO sessions (
                    id, repo_id, agent_name, task_description,
                    started_at, ended_at, status, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    task_description = excluded.task_description,
                    ended_at = excluded.ended_at,
                    status = excluded.status,
                    metadata = excluded.metadata
                """,
                (
                    session.id,
                    session.repo_id,
                    session.agent_name,
                    session.task_description,
                    session.started_at,
                    session.ended_at,
                    session.status,
                    json.dumps(session.metadata),
                ),
            )

    def get_session(self, repo_id: str, session_id: str) -> Optional[AgentSession]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE repo_id = ? AND id = ?",
                (repo_id, session_id),
            ).fetchone()
            if not row:
                return None
            return AgentSession(
                id=row["id"],
                repo_id=row["repo_id"],
                agent_name=row["agent_name"],
                task_description=row["task_description"],
                started_at=row["started_at"],
                ended_at=row["ended_at"],
                status=row["status"],
                metadata=json.loads(row["metadata"] or "{}"),
            )

    def list_sessions(self, repo_id: str, limit: int = 50) -> List[AgentSession]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE repo_id = ? ORDER BY started_at DESC LIMIT ?",
                (repo_id, limit),
            ).fetchall()
            return [
                AgentSession(
                    id=r["id"],
                    repo_id=r["repo_id"],
                    agent_name=r["agent_name"],
                    task_description=r["task_description"],
                    started_at=r["started_at"],
                    ended_at=r["ended_at"],
                    status=r["status"],
                    metadata=json.loads(r["metadata"] or "{}"),
                )
                for r in rows
            ]

    def update_session(
        self,
        repo_id: str,
        session_id: str,
        status: Optional[str] = None,
        task_description: Optional[str] = None,
        ended_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self.get_connection() as conn:
            updates = []
            params: List[Any] = []
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if task_description is not None:
                updates.append("task_description = ?")
                params.append(task_description)
            if ended_at is not None:
                updates.append("ended_at = ?")
                params.append(ended_at)
            if metadata is not None:
                updates.append("metadata = ?")
                params.append(json.dumps(metadata))

            if updates:
                query = f"UPDATE sessions SET {', '.join(updates)} WHERE repo_id = ? AND id = ?"
                params.extend([repo_id, session_id])
                conn.execute(query, params)

    def get_session_events(self, repo_id: str, session_id: str) -> List[ChangeEvent]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM change_events WHERE repo_id = ? AND session_id = ? ORDER BY timestamp ASC",
                (repo_id, session_id),
            ).fetchall()
            return [
                ChangeEvent(
                    id=r["id"],
                    repo_id=r["repo_id"],
                    timestamp=r["timestamp"],
                    event_type=r["event_type"],
                    file_path=r["file_path"],
                    symbol_id=r["symbol_id"],
                    session_id=r["session_id"],
                    agent_name=r["agent_name"],
                    diff_content=r["diff_content"],
                    summary=r["summary"],
                )
                for r in rows
            ]

    def update_symbol_status(self, repo_id: str, symbol_id: str, status: ChangeStatus) -> None:
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE symbols SET change_status = ? WHERE repo_id = ? AND id = ?",
                (status.value, repo_id, symbol_id),
            )

    def list_changed_symbols(self, repo_id: str) -> List[Symbol]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM symbols WHERE repo_id = ? AND change_status != 'unchanged' ORDER BY file_path ASC, start_line ASC",
                (repo_id,),
            ).fetchall()
            return [self._row_to_symbol(r) for r in rows]

    def reset_all_symbol_statuses(self, repo_id: str) -> None:
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE symbols SET change_status = 'unchanged' WHERE repo_id = ?",
                (repo_id,),
            )

    def get_metrics(self, repo_id: str) -> RepositoryMetrics:
        with self.get_connection() as conn:
            repo_row = conn.execute(
                "SELECT last_scanned_at FROM repositories WHERE id = ?",
                (repo_id,),
            ).fetchone()
            last_scanned = repo_row["last_scanned_at"] if repo_row else None

            file_count = conn.execute(
                "SELECT COUNT(*) as count FROM files WHERE repo_id = ? AND is_deleted = 0",
                (repo_id,),
            ).fetchone()["count"]

            symbol_count = conn.execute(
                "SELECT COUNT(*) as count FROM symbols WHERE repo_id = ?",
                (repo_id,),
            ).fetchone()["count"]

            rel_count = conn.execute(
                "SELECT COUNT(*) as count FROM relationships WHERE repo_id = ?",
                (repo_id,),
            ).fetchone()["count"]

            lang_rows = conn.execute(
                "SELECT language, COUNT(*) as count FROM files WHERE repo_id = ? AND is_deleted = 0 GROUP BY language",
                (repo_id,),
            ).fetchall()
            languages = {r["language"]: r["count"] for r in lang_rows}

            return RepositoryMetrics(
                file_count=file_count,
                symbol_count=symbol_count,
                relationship_count=rel_count,
                languages=languages,
                last_scanned_at=last_scanned,
            )

    @staticmethod
    def _row_to_symbol(row: sqlite3.Row) -> Symbol:
        return Symbol(
            id=row["id"],
            repo_id=row["repo_id"],
            file_path=row["file_path"],
            name=row["name"],
            symbol_type=SymbolType(row["symbol_type"]),
            parent_symbol_id=row["parent_symbol_id"],
            start_line=row["start_line"],
            end_line=row["end_line"],
            start_byte=row["start_byte"],
            end_byte=row["end_byte"],
            signature=row["signature"],
            docstring=row["docstring"],
            content_hash=row["content_hash"],
            change_status=ChangeStatus(row["change_status"]),
        )
