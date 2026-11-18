"""Tests for SQLiteStore persistence and relational queries."""

from pathlib import Path
import pytest

from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.models import (
    ChangeStatus,
    FileInfo,
    ParseResult,
    Relationship,
    RelationshipType,
    Symbol,
    SymbolType,
)


@pytest.fixture
def temp_store(tmp_path: Path) -> SQLiteStore:
    db_file = tmp_path / "test_codepulse.db"
    return SQLiteStore(db_file)


def test_repository_registration(temp_store: SQLiteStore, tmp_path: Path):
    temp_store.register_repository("test_repo", str(tmp_path))
    temp_store.update_last_scanned("test_repo")
    metrics = temp_store.get_metrics("test_repo")
    assert metrics.last_scanned_at is not None
    assert metrics.file_count == 0


def test_save_and_retrieve_parse_result(temp_store: SQLiteStore):
    repo_id = "test_repo"
    temp_store.register_repository(repo_id, "/dummy/path")

    file_info = FileInfo(
        path="src/auth.py",
        sha256="abc123hash",
        mtime=1700000000.0,
        size_bytes=512,
        language="python",
    )

    func_sym = Symbol(
        id="src/auth.py::function::login",
        repo_id=repo_id,
        file_path="src/auth.py",
        name="login",
        symbol_type=SymbolType.FUNCTION,
        start_line=10,
        end_line=25,
        start_byte=100,
        end_byte=350,
        signature="def login(username, password)",
        docstring="Authenticates user.",
    )

    parse_result = ParseResult(
        file_info=file_info,
        symbols=[func_sym],
        relationships=[
            Relationship(
                source_id="src/auth.py::file::src/auth.py",
                target_id=func_sym.id,
                relationship_type=RelationshipType.CONTAINS,
            ),
            Relationship(
                source_id=func_sym.id,
                target_id="validate_token",
                relationship_type=RelationshipType.CALLS,
            ),
        ],
    )

    temp_store.save_parse_result(repo_id, parse_result)

    # Verify file saved
    retrieved_file = temp_store.get_file(repo_id, "src/auth.py")
    assert retrieved_file is not None
    assert retrieved_file.sha256 == "abc123hash"

    # Verify symbol saved
    syms = temp_store.get_symbols_by_file(repo_id, "src/auth.py")
    assert len(syms) == 1
    assert syms[0].name == "login"
    assert syms[0].docstring == "Authenticates user."

    # Verify relationships
    calls = temp_store.get_relationships(repo_id, rel_type=RelationshipType.CALLS)
    assert len(calls) == 1
    assert calls[0].source_id == func_sym.id
    assert calls[0].target_id == "validate_token"


def test_incremental_update_cleans_prior_symbols(temp_store: SQLiteStore):
    repo_id = "test_repo"
    temp_store.register_repository(repo_id, "/dummy")

    file_info = FileInfo(
        path="service.py",
        sha256="hash1",
        mtime=1.0,
        size_bytes=100,
        language="python",
    )

    sym1 = Symbol(
        id="service.py::function::old_func",
        repo_id=repo_id,
        file_path="service.py",
        name="old_func",
        symbol_type=SymbolType.FUNCTION,
        start_line=1,
        end_line=5,
    )

    temp_store.save_parse_result(
        repo_id,
        ParseResult(file_info=file_info, symbols=[sym1], relationships=[]),
    )
    assert len(temp_store.get_symbols_by_file(repo_id, "service.py")) == 1

    # Now update file with new_func
    sym2 = Symbol(
        id="service.py::function::new_func",
        repo_id=repo_id,
        file_path="service.py",
        name="new_func",
        symbol_type=SymbolType.FUNCTION,
        start_line=1,
        end_line=10,
    )
    temp_store.save_parse_result(
        repo_id,
        ParseResult(
            file_info=FileInfo(
                path="service.py",
                sha256="hash2",
                mtime=2.0,
                size_bytes=200,
                language="python",
            ),
            symbols=[sym2],
            relationships=[],
        ),
    )

    updated_syms = temp_store.get_symbols_by_file(repo_id, "service.py")
    assert len(updated_syms) == 1
    assert updated_syms[0].name == "new_func"
