"""Review Engine for CodePulse — review lifecycle, annotations, and safe Git rollback."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.change_detector.git_tracker import GitTracker
from codepulse.core.explanation_engine.engine import ExplanationEngine
from codepulse.core.impact_analyzer.analyzer import ImpactAnalyzer
from codepulse.core.models import (
    AgentSession,
    ChangeStatus,
    ReviewAnnotation,
    ReviewDetail,
    ReviewItem,
    ReviewStatus,
    Symbol,
    SymbolDiff,
    SymbolType,
)
from codepulse.core.repository_scanner.scanner import RepositoryScanner
from codepulse.core.session_manager.manager import SessionManager

logger = logging.getLogger(__name__)


class ReviewEngine:
    def __init__(
        self,
        root_path: Path,
        store: SQLiteStore,
        repo_id: str = "default",
        git_tracker: Optional[GitTracker] = None,
        impact_analyzer: Optional[ImpactAnalyzer] = None,
        explanation_engine: Optional[ExplanationEngine] = None,
        session_mgr: Optional[SessionManager] = None,
    ) -> None:
        self.root_path = Path(root_path).resolve()
        self.store = store
        self.repo_id = repo_id
        self.git_tracker = git_tracker or GitTracker(self.root_path)
        self.impact_analyzer = impact_analyzer or ImpactAnalyzer(store, repo_id=repo_id)
        self.explanation_engine = explanation_engine or ExplanationEngine()
        self.session_mgr = session_mgr or SessionManager(store, repo_id=repo_id)
        self.scanner = RepositoryScanner(self.store, repo_id=self.repo_id)

    def get_reviews(self, status: Optional[ReviewStatus] = None) -> List[ReviewItem]:
        """Lists reviews for all changed symbols in the repository."""
        changed_symbols = self.store.list_changed_symbols(self.repo_id)
        existing_reviews = {r.symbol_id: r for r in self.store.list_reviews(self.repo_id)}

        items: List[ReviewItem] = []
        for sym in changed_symbols:
            if sym.id in existing_reviews:
                rev = existing_reviews[sym.id]
            else:
                rev = self.store.get_or_create_review(self.repo_id, sym.id, sym.file_path)
            
            if status is None or rev.status == status:
                items.append(rev)

        return items

    def get_review_detail(self, symbol_id: str) -> Optional[ReviewDetail]:
        """Constructs a comprehensive review bundle for a single changed symbol."""
        sym = self.store.get_symbol_by_id(self.repo_id, symbol_id)
        if not sym:
            return None

        review_item = self.store.get_or_create_review(self.repo_id, sym.id, sym.file_path)
        annotations = self.store.get_review_annotations(self.repo_id, sym.id)

        # 1. Fetch updated code from disk
        file_disk_path = self.root_path / sym.file_path
        updated_code: Optional[str] = None
        if file_disk_path.is_file():
            try:
                with open(file_disk_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                start = max(0, sym.start_line - 1)
                end = min(len(lines), sym.end_line)
                updated_code = "".join(lines[start:end])
            except Exception as e:
                logger.warning(f"Failed to read updated code from {file_disk_path}: {e}")

        # 2. Fetch original code from Git HEAD
        original_code: Optional[str] = None
        head_bytes = self.git_tracker.get_file_content_at_head(sym.file_path)
        if head_bytes:
            head_text = head_bytes.decode("utf-8", errors="replace")
            original_code = self._extract_symbol_from_source(sym.name, sym.symbol_type, head_text, sym.file_path)

        # 3. Diff text
        diff_text = self.git_tracker.get_file_diff(sym.file_path)

        # 4. Task context and Agent session
        active_session = self.session_mgr.get_active_session()
        task_context: Optional[str] = None
        agent_session: Optional[AgentSession] = active_session

        if active_session:
            task_context = active_session.task_description
        else:
            # Check recent change events for symbol
            events = self.store.list_change_events(self.repo_id, limit=20)
            for ev in events:
                if ev.symbol_id == sym.id or ev.file_path == sym.file_path:
                    if ev.session_id:
                        sess = self.session_mgr.get_session(ev.session_id)
                        if sess:
                            agent_session = sess
                            task_context = sess.task_description
                            break

        # 5. Impact analysis
        impact_report = self.impact_analyzer.analyze_symbol_impact(symbol_id)

        # 6. Change explanation
        diff = SymbolDiff(
            symbol_id=sym.id,
            symbol_name=sym.name,
            symbol_type=sym.symbol_type,
            file_path=sym.file_path,
            status=sym.change_status,
            diff_text=diff_text,
            new_signature=sym.signature,
            new_start_line=sym.start_line,
        )
        explanation = self.explanation_engine.explain_change(
            diff, task_description=task_context, impact_report=impact_report
        )

        structural_summary = (
            f"{sym.symbol_type.value.capitalize()} '{sym.name}' {sym.change_status.value} "
            f"in {sym.file_path} (lines {sym.start_line}-{sym.end_line})"
        )

        return ReviewDetail(
            symbol_id=sym.id,
            symbol_name=sym.name,
            file_path=sym.file_path,
            status=review_item.status,
            change_status=sym.change_status,
            decision_reason=review_item.decision_reason,
            original_code=original_code,
            updated_code=updated_code,
            diff_text=diff_text,
            structural_summary=structural_summary,
            task_context=task_context,
            impact_report=impact_report,
            explanation=explanation,
            agent_session=agent_session,
            annotations=annotations,
        )

    def mark_reviewed(
        self, symbol_id: str, note: Optional[str] = None, author: str = "reviewer"
    ) -> ReviewItem:
        """Marks a symbol change as reviewed."""
        sym = self.store.get_symbol_by_id(self.repo_id, symbol_id)
        file_path = sym.file_path if sym else ""
        item = self.store.set_review_status(
            self.repo_id, symbol_id, ReviewStatus.REVIEWED, file_path=file_path
        )
        if note:
            self.add_annotation(symbol_id, note, author=author)
            item.annotations = self.store.get_review_annotations(self.repo_id, symbol_id)
        return item

    def accept_change(
        self, symbol_id: str, note: Optional[str] = None, author: str = "reviewer"
    ) -> ReviewItem:
        """
        Accepts a symbol change.
        IMPORTANT (spec section 12): Review acceptance must not automatically modify the repository.
        """
        sym = self.store.get_symbol_by_id(self.repo_id, symbol_id)
        file_path = sym.file_path if sym else ""
        item = self.store.set_review_status(
            self.repo_id, symbol_id, ReviewStatus.ACCEPTED, file_path=file_path
        )
        if note:
            self.add_annotation(symbol_id, note, author=author)
            item.annotations = self.store.get_review_annotations(self.repo_id, symbol_id)
        return item

    def add_annotation(
        self, symbol_id: str, note: str, author: str = "reviewer"
    ) -> ReviewAnnotation:
        """Adds a review note or comment to a symbol change."""
        return self.store.add_review_annotation(self.repo_id, symbol_id, note, author=author)

    def reject_change(
        self,
        symbol_id: str,
        reason: Optional[str] = None,
        safe_rollback: bool = True,
        author: str = "reviewer",
    ) -> Dict[str, Any]:
        """
        Rejects a symbol change with safe, Git-aware rollback.
        IMPORTANT (spec section 12): Never overwrite unrelated user changes.
        """
        sym = self.store.get_symbol_by_id(self.repo_id, symbol_id)
        if not sym:
            return {"success": False, "error": f"Symbol {symbol_id} not found."}

        # Record rejection in storage
        item = self.store.set_review_status(
            self.repo_id,
            symbol_id,
            ReviewStatus.REJECTED,
            decision_reason=reason,
            file_path=sym.file_path,
        )
        if reason:
            self.add_annotation(symbol_id, f"Rejected: {reason}", author=author)

        if not safe_rollback:
            return {
                "success": True,
                "symbol_id": symbol_id,
                "status": "rejected",
                "rolled_back": False,
                "message": "Change rejected without filesystem rollback.",
            }

        # Perform safe rollback
        rollback_result = self._execute_safe_rollback(sym)
        if not rollback_result["success"]:
            return {
                "success": False,
                "symbol_id": symbol_id,
                "status": "rejected",
                "rolled_back": False,
                "error": rollback_result["error"],
            }

        # Rescan the file to update repository symbol graph & change statuses
        scanner = RepositoryScanner(self.store, repo_id=self.repo_id)
        scanner.scan_file(self.root_path / sym.file_path, self.root_path)

        return {
            "success": True,
            "symbol_id": symbol_id,
            "file_path": sym.file_path,
            "status": "rejected",
            "rolled_back": True,
            "message": rollback_result.get("message", "Symbol change rolled back successfully."),
        }

    def _execute_safe_rollback(self, sym: Symbol) -> Dict[str, Any]:
        """
        Executes a safe Git-aware rollback for the given symbol.
        Guarantees:
        1. Never touches files other than sym.file_path.
        2. If other symbols in sym.file_path were modified, attempts surgical symbol extraction/replacement.
           If surgical isolation cannot be safely guaranteed, refuses rollback to avoid clobbering user edits.
        """
        if not self.git_tracker.is_git_repo:
            return {
                "success": False,
                "error": "Safe rollback requires an initialized Git repository.",
            }

        file_disk_path = (self.root_path / sym.file_path).resolve()
        if not file_disk_path.is_relative_to(self.root_path):
            return {
                "success": False,
                "error": "Path traversal detected: Target file outside repository root.",
            }

        all_symbols_in_file = self.store.get_symbols_by_file(self.repo_id, sym.file_path)
        other_modified_symbols = [
            s for s in all_symbols_in_file
            if s.id != sym.id and s.change_status != ChangeStatus.UNCHANGED
        ]

        head_bytes = self.git_tracker.get_file_content_at_head(sym.file_path)

        # Case 1: No other symbols in the file were modified
        if not other_modified_symbols:
            if head_bytes is not None:
                # File exists in HEAD — safe to restore file to HEAD
                success = self.git_tracker.restore_file_to_head(sym.file_path)
                if success:
                    return {
                        "success": True,
                        "message": f"Restored {sym.file_path} to Git HEAD (no other symbols modified).",
                    }
                return {
                    "success": False,
                    "error": f"Git restore command failed for {sym.file_path}.",
                }
            else:
                # Untracked newly added file with single symbol
                if file_disk_path.is_file():
                    file_disk_path.unlink()
                    return {
                        "success": True,
                        "message": f"Removed newly added file {sym.file_path}.",
                    }

        # Case 2: Other symbols in the file WERE modified or user edits exist
        # We must isolate this symbol and NEVER overwrite unrelated user edits.
        if not file_disk_path.is_file():
            return {
                "success": False,
                "error": f"File {sym.file_path} does not exist on disk.",
            }

        try:
            with open(file_disk_path, "r", encoding="utf-8", errors="replace") as f:
                current_lines = f.readlines()
        except Exception as e:
            return {"success": False, "error": f"Failed reading {sym.file_path}: {e}"}

        # Verification of symbol lines bounds
        if sym.start_line < 1 or sym.end_line > len(current_lines) or sym.start_line > sym.end_line:
            return {
                "success": False,
                "error": f"Symbol line bounds ({sym.start_line}-{sym.end_line}) do not match file length ({len(current_lines)}).",
            }

        current_symbol_block = "".join(current_lines[sym.start_line - 1 : sym.end_line])
        if sym.name not in current_symbol_block:
            return {
                "success": False,
                "error": f"Symbol content does not match name '{sym.name}'. Aborting rollback to prevent corruption.",
            }

        if sym.change_status == ChangeStatus.ADDED:
            # Surgically remove only the added symbol's lines
            new_lines = current_lines[: sym.start_line - 1] + current_lines[sym.end_line :]
            with open(file_disk_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            return {
                "success": True,
                "message": f"Surgically removed added symbol '{sym.name}' from {sym.file_path}, preserving other changes.",
            }

        elif sym.change_status in (ChangeStatus.MODIFIED, ChangeStatus.UNCHANGED):
            # Extract original symbol code from HEAD
            if not head_bytes:
                return {
                    "success": False,
                    "error": f"Original content for {sym.file_path} not found in Git HEAD.",
                }

            head_text = head_bytes.decode("utf-8", errors="replace")
            original_code = self._extract_symbol_from_source(sym.name, sym.symbol_type, head_text, sym.file_path)
            if not original_code:
                return {
                    "success": False,
                    "error": f"Could not isolate original symbol '{sym.name}' from Git HEAD to perform safe replacement.",
                }

            # Replace lines with original code
            orig_lines = [l if l.endswith("\n") else l + "\n" for l in original_code.splitlines()]
            new_lines = current_lines[: sym.start_line - 1] + orig_lines + current_lines[sym.end_line :]
            with open(file_disk_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            return {
                "success": True,
                "message": f"Surgically restored '{sym.name}' to original HEAD code, preserving other changes in {sym.file_path}.",
            }

        return {
            "success": False,
            "error": f"Rollback for change status '{sym.change_status.value}' is not supported automatically.",
        }

    def _extract_symbol_from_source(
        self, symbol_name: str, symbol_type: SymbolType, source_text: str, file_path: str
    ) -> Optional[str]:
        """Extracts the exact code block for a symbol from a source text string."""
        ext = Path(file_path).suffix.lower()
        parser = self.scanner.extension_map.get(ext)
        if parser:
            try:
                res = parser.parse_content(Path(file_path), source_text.encode("utf-8"))
                for s in res.symbols:
                    if s.name == symbol_name and s.symbol_type == symbol_type:
                        lines = source_text.splitlines(keepends=True)
                        start = max(0, s.start_line - 1)
                        end = min(len(lines), s.end_line)
                        return "".join(lines[start:end])
            except Exception:
                pass

        # Fallback heuristic: search lines for definition
        lines = source_text.splitlines(keepends=True)
        found_idx = -1
        for idx, line in enumerate(lines):
            if f"def {symbol_name}" in line or f"class {symbol_name}" in line or f"function {symbol_name}" in line:
                found_idx = idx
                break

        if found_idx >= 0:
            # Capture block until next unindented definition or blank line
            collected = [lines[found_idx]]
            base_indent = len(lines[found_idx]) - len(lines[found_idx].lstrip())
            for line in lines[found_idx + 1 :]:
                if not line.strip():
                    collected.append(line)
                    continue
                line_indent = len(line) - len(line.lstrip())
                if line_indent <= base_indent and (
                    line.startswith("def ") or line.startswith("class ") or line.startswith("function ")
                ):
                    break
                collected.append(line)
            return "".join(collected)

        return None
