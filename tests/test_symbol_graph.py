"""Tests for SymbolGraphManager (architecture graph, blast radius, hierarchical tree)."""

from pathlib import Path
from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.models import (
    FileInfo,
    ParseResult,
    Relationship,
    RelationshipType,
    Symbol,
    SymbolType,
)
from codepulse.core.symbol_graph.graph import SymbolGraphManager


def test_symbol_graph_architecture_and_blast_radius(tmp_path: Path):
    db_file = tmp_path / "test.db"
    store = SQLiteStore(db_file)
    repo_id = "test_repo"
    store.register_repository(repo_id, str(tmp_path))

    # Create symbols: A calls B, B calls C
    file_sym = Symbol(
        id="app.py::file::app.py",
        repo_id=repo_id,
        file_path="app.py",
        name="app.py",
        symbol_type=SymbolType.FILE,
        start_line=1,
        end_line=50,
    )

    func_a = Symbol(
        id="app.py::function::endpoint_handler",
        repo_id=repo_id,
        file_path="app.py",
        name="endpoint_handler",
        symbol_type=SymbolType.FUNCTION,
        parent_symbol_id=file_sym.id,
        start_line=5,
        end_line=15,
    )

    func_b = Symbol(
        id="app.py::function::service_layer",
        repo_id=repo_id,
        file_path="app.py",
        name="service_layer",
        symbol_type=SymbolType.FUNCTION,
        parent_symbol_id=file_sym.id,
        start_line=20,
        end_line=30,
    )

    func_c = Symbol(
        id="app.py::function::database_query",
        repo_id=repo_id,
        file_path="app.py",
        name="database_query",
        symbol_type=SymbolType.FUNCTION,
        parent_symbol_id=file_sym.id,
        start_line=35,
        end_line=45,
    )

    parse_result = ParseResult(
        file_info=FileInfo(
            path="app.py",
            sha256="abc",
            mtime=1.0,
            size_bytes=100,
            language="python",
        ),
        symbols=[file_sym, func_a, func_b, func_c],
        relationships=[
            Relationship(source_id=file_sym.id, target_id=func_a.id, relationship_type=RelationshipType.CONTAINS),
            Relationship(source_id=file_sym.id, target_id=func_b.id, relationship_type=RelationshipType.CONTAINS),
            Relationship(source_id=file_sym.id, target_id=func_c.id, relationship_type=RelationshipType.CONTAINS),
            # Invocations: A -> B -> C
            Relationship(source_id=func_a.id, target_id=func_b.id, relationship_type=RelationshipType.CALLS),
            Relationship(source_id=func_b.id, target_id=func_c.id, relationship_type=RelationshipType.CALLS),
        ],
    )

    store.save_parse_result(repo_id, parse_result)
    graph_mgr = SymbolGraphManager(store, repo_id=repo_id)

    # 1. Architecture graph
    arch_graph = graph_mgr.build_architecture_graph()
    assert arch_graph.number_of_nodes() == 4
    assert arch_graph.has_edge(file_sym.id, func_a.id)

    # 2. Blast radius calculation on func_c (database_query)
    # If C changes, B is an upstream caller, and A calls B (transitive caller!)
    blast_c = graph_mgr.get_blast_radius(func_c.id, max_depth=3)
    assert blast_c["upstream_callers_count"] == 2
    assert func_b.id in blast_c["upstream_callers"]
    assert func_a.id in blast_c["upstream_callers"]

    # 3. Hierarchical tree
    tree = graph_mgr.get_hierarchical_tree()
    assert len(tree["children"]) == 1
    file_node = tree["children"][0]
    assert file_node["name"] == "app.py"
    assert len(file_node["functions"]) == 3
