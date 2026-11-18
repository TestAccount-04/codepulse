"""Base parser interface and utility functions for AST symbol extraction."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from codepulse.core.models import (
    ChangeStatus,
    FileInfo,
    ParseResult,
    Relationship,
    RelationshipType,
    Symbol,
    SymbolType,
)


class BaseLanguageParser(ABC):
    @property
    @abstractmethod
    def language_name(self) -> str:
        """Name of language, e.g. 'python', 'javascript', etc."""
        pass

    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """List of supported extensions with leading dot, e.g. ['.py']."""
        pass

    @abstractmethod
    def parse_code(self, file_path: str, code_bytes: bytes, repo_id: str = "default") -> ParseResult:
        """Parses source code bytes into symbols and relationships."""
        pass

    @staticmethod
    def compute_sha256(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def compute_symbol_hash(body_bytes: bytes) -> str:
        return hashlib.sha256(body_bytes.strip()).hexdigest()

    def build_file_info(self, file_path: str, code_bytes: bytes) -> FileInfo:
        return FileInfo(
            path=file_path.replace("\\", "/"),
            sha256=self.compute_sha256(code_bytes),
            mtime=0.0,
            size_bytes=len(code_bytes),
            language=self.language_name,
            is_deleted=False,
        )
