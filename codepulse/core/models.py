"""Core domain models for CodePulse symbol graphs, files, and relationships."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SymbolType(str, Enum):
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    INTERFACE = "interface"
    MODULE = "module"


class RelationshipType(str, Enum):
    CONTAINS = "CONTAINS"
    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    INHERITS = "INHERITS"
    TESTS = "TESTS"


class ChangeStatus(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    UNCHANGED = "unchanged"
    IMPACTED = "impacted"


class Symbol(BaseModel):
    id: str
    repo_id: str = "default"
    file_path: str
    name: str
    symbol_type: SymbolType
    parent_symbol_id: Optional[str] = None
    start_line: int
    end_line: int
    start_byte: int = 0
    end_byte: int = 0
    signature: Optional[str] = None
    docstring: Optional[str] = None
    content_hash: Optional[str] = None
    change_status: ChangeStatus = ChangeStatus.UNCHANGED

    @staticmethod
    def build_id(file_path: str, name: str, symbol_type: SymbolType, parent_name: Optional[str] = None) -> str:
        clean_path = file_path.replace("\\", "/")
        if parent_name:
            return f"{clean_path}::{parent_name}::{symbol_type.value}::{name}"
        return f"{clean_path}::{symbol_type.value}::{name}"


class Relationship(BaseModel):
    id: Optional[int] = None
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FileInfo(BaseModel):
    path: str
    sha256: str
    mtime: float
    size_bytes: int
    language: str
    is_deleted: bool = False


class RepositoryMetrics(BaseModel):
    file_count: int = 0
    symbol_count: int = 0
    relationship_count: int = 0
    languages: Dict[str, int] = Field(default_factory=dict)
    last_scanned_at: Optional[str] = None


class ParseResult(BaseModel):
    file_info: FileInfo
    symbols: List[Symbol] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class SymbolDiff(BaseModel):
    symbol_id: str
    symbol_name: str
    symbol_type: SymbolType
    file_path: str
    status: ChangeStatus
    diff_text: Optional[str] = None
    old_signature: Optional[str] = None
    new_signature: Optional[str] = None
    old_start_line: Optional[int] = None
    new_start_line: Optional[int] = None


class ChangeEvent(BaseModel):
    id: str
    repo_id: str = "default"
    timestamp: str
    event_type: str
    file_path: str
    symbol_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_name: str = "unknown"
    diff_content: Optional[str] = None
    summary: Optional[str] = None


class AgentSession(BaseModel):
    id: str
    repo_id: str = "default"
    agent_name: str
    task_description: Optional[str] = None
    started_at: str
    ended_at: Optional[str] = None
    status: str = "active"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ImpactReport(BaseModel):
    symbol_id: str
    symbol_name: str
    file_path: str
    direct_callers: List[Dict[str, Any]] = Field(default_factory=list)
    indirect_callers: List[str] = Field(default_factory=list)
    direct_callees: List[str] = Field(default_factory=list)
    imports: List[str] = Field(default_factory=list)
    inherits: List[str] = Field(default_factory=list)
    related_tests: List[str] = Field(default_factory=list)
    risk_level: str = "LOW"
    risk_score: float = 0.0


class ChangeExplanation(BaseModel):
    symbol_name: str
    status: ChangeStatus
    what_changed: str
    why: str
    impact: str
    risk_level: str
    grounded_evidence: Dict[str, Any] = Field(default_factory=dict)
