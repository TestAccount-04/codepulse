"""Tests for ImpactAnalyzer caller traversal, test suite discovery, and risk scoring."""

from pathlib import Path
from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.impact_analyzer.analyzer import ImpactAnalyzer
from codepulse.core.models import (
    FileInfo,
    ParseResult,
    Relationship,
    RelationshipType,
    Symbol,
    SymbolType,
)


def test_impact_analysis_with_callers_and_tests(tmp_path: Path):
    db_file = tmp_path / "test.db"
    store = SQLiteStore(db_file)
    store.register_repository("test_repo", str(tmp_path))

    # Target symbol: authenticate_user in src/auth.py
    target = Symbol(
        id="src/auth.py::function::authenticate_user",
        repo_id="test_repo",
        file_path="src/auth.py",
        name="authenticate_user",
        symbol_type=SymbolType.FUNCTION,
        start_line=10,
        end_line=20,
    )

    # Caller 1: login_controller in src/controller.py
    caller1 = Symbol(
        id="src/controller.py::function::login_controller",
        repo_id="test_repo",
        file_path="src/controller.py",
        name="login_controller",
        symbol_type=SymbolType.FUNCTION,
        start_line=5,
        end_line=15,
    )

    # Test caller: test_login in tests/test_auth.py
    test_caller = Symbol(
        id="tests/test_auth.py::function::test_login",
        repo_id="test_repo",
        file_path="tests/test_auth.py",
        name="test_login",
        symbol_type=SymbolType.FUNCTION,
        start_line=8,
        end_line=18,
    )

    # Save symbols
    store.save_parse_result(
        "test_repo",
        ParseResult(
            file_info=FileInfo(path="src/auth.py", sha256="1", mtime=1, size_bytes=10, language="python"),
            symbols=[target],
            relationships=[],
        ),
    )
    store.save_parse_result(
        "test_repo",
        ParseResult(
            file_info=FileInfo(path="src/controller.py", sha256="2", mtime=1, size_bytes=10, language="python"),
            symbols=[caller1],
            relationships=[
                Relationship(source_id=caller1.id, target_id=target.id, relationship_type=RelationshipType.CALLS)
            ],
        ),
    )
    store.save_parse_result(
        "test_repo",
        ParseResult(
            file_info=FileInfo(path="tests/test_auth.py", sha256="3", mtime=1, size_bytes=10, language="python"),
            symbols=[test_caller],
            relationships=[
                Relationship(source_id=test_caller.id, target_id=target.id, relationship_type=RelationshipType.CALLS)
            ],
        ),
    )

    analyzer = ImpactAnalyzer(store, repo_id="test_repo")
    report = analyzer.analyze_symbol_impact(target.id, depth=3)

    assert report.symbol_name == "authenticate_user"
    assert len(report.direct_callers) >= 2

    caller_names = {c["caller_name"] for c in report.direct_callers}
    assert "login_controller" in caller_names
    assert "test_login" in caller_names

    # Verify test suite discovery
    assert len(report.related_tests) >= 1
    assert any("test_auth.py" in t for t in report.related_tests)

    # Verify risk score calculated
    assert report.risk_score > 0.0
    assert report.risk_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
