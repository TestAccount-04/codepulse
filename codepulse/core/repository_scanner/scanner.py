"""Repository scanner coordinating file discovery, AST parsing, and SQLite index synchronization."""

from __future__ import annotations

import fnmatch
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.models import FileInfo, ParseResult, RepositoryMetrics
from codepulse.core.repository_scanner.java_parser import JavaParser
from codepulse.core.repository_scanner.javascript_parser import JavaScriptParser
from codepulse.core.repository_scanner.parser_base import BaseLanguageParser
from codepulse.core.repository_scanner.python_parser import PythonParser
from codepulse.core.repository_scanner.typescript_parser import TypeScriptParser


DEFAULT_IGNORE_PATTERNS = {
    ".git",
    ".git/*",
    ".venv",
    ".venv/*",
    "venv",
    "venv/*",
    "node_modules",
    "node_modules/*",
    "__pycache__",
    "__pycache__/*",
    ".pytest_cache",
    ".pytest_cache/*",
    ".codepulse",
    ".codepulse/*",
    "dist",
    "dist/*",
    "build",
    "build/*",
    "*.egg-info",
    "*.pyc",
    "*.class",
}


class RepositoryScanner:
    def __init__(self, store: SQLiteStore, repo_id: str = "default") -> None:
        self.store = store
        self.repo_id = repo_id
        self.parsers: Dict[str, BaseLanguageParser] = {}
        self.extension_map: Dict[str, BaseLanguageParser] = {}

        # Register default parsers
        self.register_parser(PythonParser())
        self.register_parser(JavaScriptParser())
        self.register_parser(TypeScriptParser())
        self.register_parser(JavaParser())

    def register_parser(self, parser: BaseLanguageParser) -> None:
        self.parsers[parser.language_name] = parser
        for ext in parser.file_extensions:
            self.extension_map[ext.lower()] = parser

    def load_ignore_patterns(self, root_dir: Path) -> Set[str]:
        patterns = set(DEFAULT_IGNORE_PATTERNS)
        gitignore_path = root_dir / ".gitignore"
        if gitignore_path.is_file():
            try:
                with open(gitignore_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.add(line.rstrip("/"))
                            patterns.add(f"{line.rstrip('/')}/*")
            except Exception:
                pass
        return patterns

    def is_ignored(self, rel_path: str, ignore_patterns: Set[str]) -> bool:
        clean_path = rel_path.replace("\\", "/")
        parts = clean_path.split("/")

        # Check directory components
        for part in parts:
            if part in {".git", ".venv", "venv", "node_modules", "__pycache__", ".codepulse"}:
                return True

        for pat in ignore_patterns:
            if fnmatch.fnmatch(clean_path, pat) or fnmatch.fnmatch(parts[-1], pat):
                return True
        return False

    def scan_repository(self, root_path: Path, force: bool = False) -> Dict[str, Any]:
        start_time = time.time()
        root_dir = Path(root_path).resolve()
        self.store.register_repository(self.repo_id, str(root_dir))
        ignore_patterns = self.load_ignore_patterns(root_dir)

        scanned_files = 0
        parsed_files = 0
        skipped_files = 0
        total_symbols = 0
        current_disk_paths: Set[str] = set()

        for dirpath, dirnames, filenames in os.walk(root_dir):
            rel_dir = os.path.relpath(dirpath, root_dir)
            if rel_dir != "." and self.is_ignored(rel_dir, ignore_patterns):
                dirnames.clear()  # Do not recurse into ignored directories
                continue

            # Filter subdirs in place
            dirnames[:] = [
                d
                for d in dirnames
                if not self.is_ignored(
                    os.path.relpath(os.path.join(dirpath, d), root_dir), ignore_patterns
                )
            ]

            for filename in filenames:
                ext = Path(filename).suffix.lower()
                if ext not in self.extension_map:
                    continue

                full_path = Path(dirpath) / filename
                rel_path = str(full_path.relative_to(root_dir)).replace("\\", "/")

                if self.is_ignored(rel_path, ignore_patterns):
                    continue

                current_disk_paths.add(rel_path)
                scanned_files += 1

                try:
                    stat = full_path.stat()
                    mtime = stat.st_mtime
                    size = stat.st_size
                    code_bytes = full_path.read_bytes()
                    sha256 = BaseLanguageParser.compute_sha256(code_bytes)

                    # Check if file has changed
                    existing_file = self.store.get_file(self.repo_id, rel_path)
                    if (
                        not force
                        and existing_file
                        and existing_file.sha256 == sha256
                        and not existing_file.is_deleted
                    ):
                        skipped_files += 1
                        continue

                    # Parse AST
                    parser = self.extension_map[ext]
                    parse_result = parser.parse_code(rel_path, code_bytes, self.repo_id)
                    parse_result.file_info.mtime = mtime
                    parse_result.file_info.size_bytes = size

                    self.store.save_parse_result(self.repo_id, parse_result)
                    parsed_files += 1
                    total_symbols += len(parse_result.symbols)

                except Exception as e:
                    # Log error but continue scanning remaining files
                    pass

        # Handle deleted files
        stored_files = self.store.list_files(self.repo_id, include_deleted=False)
        deleted_count = 0
        for f in stored_files:
            if f.path not in current_disk_paths:
                self.store.delete_file_data(self.repo_id, f.path)
                f.is_deleted = True
                self.store.upsert_file(self.repo_id, f)
                deleted_count += 1

        self.store.update_last_scanned(self.repo_id)
        duration = round(time.time() - start_time, 3)

        metrics = self.store.get_metrics(self.repo_id)

        return {
            "scanned_files": scanned_files,
            "parsed_files": parsed_files,
            "skipped_files": skipped_files,
            "deleted_files": deleted_count,
            "total_symbols": metrics.symbol_count,
            "total_relationships": metrics.relationship_count,
            "languages": metrics.languages,
            "duration_seconds": duration,
        }
