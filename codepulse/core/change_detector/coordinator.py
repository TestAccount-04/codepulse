"""Change coordinator connecting Git baseline, filesystem monitoring, AST diffing, and graph updates."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.change_detector.diff_engine import DiffEngine
from codepulse.core.change_detector.git_tracker import GitTracker
from codepulse.core.change_detector.watcher import RepositoryWatcher
from codepulse.core.models import (
    ChangeEvent,
    ChangeStatus,
    FileInfo,
    ParseResult,
    RelationshipType,
    Symbol,
    SymbolDiff,
    SymbolType,
)
from codepulse.core.repository_scanner.scanner import RepositoryScanner
from codepulse.core.symbol_graph.graph import SymbolGraphManager


class ChangeCoordinator:
    def __init__(
        self,
        repo_path: Path,
        store: SQLiteStore,
        repo_id: str = "default",
    ) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.store = store
        self.repo_id = repo_id
        self.git_tracker = GitTracker(self.repo_path)
        self.scanner = RepositoryScanner(self.store, repo_id=self.repo_id)
        self.graph_mgr = SymbolGraphManager(self.store, repo_id=self.repo_id)
        self.watcher: Optional[RepositoryWatcher] = None
        self._monitoring_started_at: Optional[str] = None

    def capture_baseline(self) -> Dict[str, Any]:
        """Captures Git state and identifies pre-existing uncommitted modifications."""
        now = datetime.now(timezone.utc).isoformat()
        self._monitoring_started_at = now

        git_state = {
            "is_git": self.git_tracker.is_git_repo,
            "head_commit": self.git_tracker.get_head_commit(),
            "branch": self.git_tracker.get_current_branch(),
            "uncommitted": self.git_tracker.get_uncommitted_changes(),
            "monitoring_started_at": now,
        }

        # Run an initial scan to populate symbols if empty
        metrics = self.store.get_metrics(self.repo_id)
        if metrics.file_count == 0:
            self.scanner.scan_repository(self.repo_path)

        # Mark pre-existing changes
        uncommitted_files = set(
            git_state["uncommitted"]["modified"] + git_state["uncommitted"]["untracked"]
        )
        for rel_path in uncommitted_files:
            file_symbols = self.store.get_symbols_by_file(self.repo_id, rel_path)
            for sym in file_symbols:
                self.store.update_symbol_status(self.repo_id, sym.id, ChangeStatus.MODIFIED)

        return git_state

    def handle_file_change(
        self,
        event_type: str,
        rel_path: str,
        session_id: Optional[str] = None,
        agent_name: str = "unknown",
    ) -> List[SymbolDiff]:
        """Processes a single file change event, performs AST diffing, and updates graph."""
        clean_path = rel_path.replace("\\", "/")
        full_path = self.repo_path / clean_path
        ext = full_path.suffix.lower()

        if ext not in self.scanner.extension_map:
            return []

        parser = self.scanner.extension_map[ext]
        old_symbols = self.store.get_symbols_by_file(self.repo_id, clean_path)

        timestamp = datetime.now(timezone.utc).isoformat()

        if event_type == "deleted" or not full_path.exists():
            # File was deleted
            diffs = DiffEngine.compare_symbols(
                old_symbols=old_symbols,
                new_symbols=[],
                file_path=clean_path,
            )
            self.store.delete_file_data(self.repo_id, clean_path)
            existing_file = self.store.get_file(self.repo_id, clean_path)
            if existing_file:
                existing_file.is_deleted = True
                self.store.upsert_file(self.repo_id, existing_file)

            # Record event
            self.store.record_change_event(
                ChangeEvent(
                    id=str(uuid.uuid4()),
                    repo_id=self.repo_id,
                    timestamp=timestamp,
                    event_type="deleted",
                    file_path=clean_path,
                    session_id=session_id,
                    agent_name=agent_name,
                    summary=f"Deleted file {clean_path}",
                )
            )
            return diffs

        # File was created or modified
        try:
            new_code_bytes = full_path.read_bytes()
        except Exception:
            return []

        # Get old code bytes from git or current stored sha if available
        old_code_bytes = self.git_tracker.get_file_content_at_head(clean_path)

        new_parse_result = parser.parse_code(clean_path, new_code_bytes, self.repo_id)
        stat = full_path.stat()
        new_parse_result.file_info.mtime = stat.st_mtime
        new_parse_result.file_info.size_bytes = stat.st_size

        # Compute symbol diffs
        symbol_diffs = DiffEngine.compare_symbols(
            old_symbols=old_symbols,
            new_symbols=new_parse_result.symbols,
            file_path=clean_path,
            old_code_bytes=old_code_bytes,
            new_code_bytes=new_code_bytes,
        )

        # Update symbol statuses in parse result before saving
        diff_status_map = {d.symbol_id: d.status for d in symbol_diffs}
        for sym in new_parse_result.symbols:
            if sym.id in diff_status_map:
                sym.change_status = diff_status_map[sym.id]

        # Save to database
        self.store.save_parse_result(self.repo_id, new_parse_result)

        # Propagate impact to callers of modified symbols
        for d in symbol_diffs:
            if d.status in (ChangeStatus.MODIFIED, ChangeStatus.DELETED):
                blast = self.graph_mgr.get_blast_radius(d.symbol_id, max_depth=1)
                for caller_id in blast["upstream_callers"]:
                    self.store.update_symbol_status(
                        self.repo_id, caller_id, ChangeStatus.IMPACTED
                    )

            # Record change event for significant modifications
            if d.status != ChangeStatus.UNCHANGED:
                summary = f"{d.status.value.capitalize()} {d.symbol_type.value} {d.symbol_name} in {clean_path}"
                self.store.record_change_event(
                    ChangeEvent(
                        id=str(uuid.uuid4()),
                        repo_id=self.repo_id,
                        timestamp=timestamp,
                        event_type=d.status.value,
                        file_path=clean_path,
                        symbol_id=d.symbol_id,
                        session_id=session_id,
                        agent_name=agent_name,
                        diff_content=d.diff_text,
                        summary=summary,
                    )
                )

        return symbol_diffs

    def start_watching(
        self,
        on_change_callback: Optional[Callable[[List[SymbolDiff]], None]] = None,
    ) -> None:
        """Starts real-time filesystem monitoring."""
        def _on_event(event_type: str, rel_path: str) -> None:
            diffs = self.handle_file_change(event_type, rel_path)
            if on_change_callback and diffs:
                on_change_callback(diffs)

        self.watcher = RepositoryWatcher(
            root_dir=self.repo_path,
            callback=_on_event,
        )
        self.watcher.start()

    def stop_watching(self) -> None:
        if self.watcher:
            self.watcher.stop()
            self.watcher = None
