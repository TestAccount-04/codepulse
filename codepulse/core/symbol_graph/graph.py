"""Symbol and dependency graph manager with NetworkX and hierarchical tree navigation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
import networkx as nx

from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.models import (
    Relationship,
    RelationshipType,
    Symbol,
    SymbolType,
)


class SymbolGraphManager:
    def __init__(self, store: SQLiteStore, repo_id: str = "default") -> None:
        self.store = store
        self.repo_id = repo_id

    def build_architecture_graph(self) -> nx.DiGraph:
        """Constructs hierarchical containment graph (Repo -> Folder -> File -> Class -> Method)."""
        g = nx.DiGraph()
        symbols = self.store.list_symbols(self.repo_id)

        # Add all symbols as nodes
        for sym in symbols:
            g.add_node(
                sym.id,
                name=sym.name,
                type=sym.symbol_type.value,
                file_path=sym.file_path,
                start_line=sym.start_line,
                end_line=sym.end_line,
                signature=sym.signature,
                status=sym.change_status.value,
            )

        # Add CONTAINS relationships
        contains_rels = self.store.get_relationships(
            self.repo_id, rel_type=RelationshipType.CONTAINS
        )
        for rel in contains_rels:
            g.add_edge(rel.source_id, rel.target_id, relationship="CONTAINS")

        return g

    def build_dependency_graph(self) -> nx.DiGraph:
        """Constructs relational graph (CALLS, INHERITS, IMPORTS, TESTS)."""
        g = nx.DiGraph()
        symbols = self.store.list_symbols(self.repo_id)
        for sym in symbols:
            g.add_node(
                sym.id,
                name=sym.name,
                type=sym.symbol_type.value,
                file_path=sym.file_path,
                status=sym.change_status.value,
            )

        rels = self.store.get_relationships(self.repo_id)
        for rel in rels:
            if rel.relationship_type != RelationshipType.CONTAINS:
                g.add_edge(
                    rel.source_id,
                    rel.target_id,
                    relationship=rel.relationship_type.value,
                    metadata=rel.metadata,
                )
        return g

    def get_blast_radius(self, symbol_id: str, max_depth: int = 3) -> Dict[str, Any]:
        """Calculates upstream callers and dependents impacted if symbol_id is modified."""
        dep_graph = self.build_dependency_graph()
        upstream_impacted: Set[str] = set()
        downstream_dependencies: Set[str] = set()

        if symbol_id in dep_graph:
            # Upstream: who calls or depends on this symbol? (predecessors in directed CALLS)
            current_layer = {symbol_id}
            for depth in range(1, max_depth + 1):
                next_layer = set()
                for node in current_layer:
                    preds = set(dep_graph.predecessors(node)) - upstream_impacted - {symbol_id}
                    next_layer.update(preds)
                upstream_impacted.update(next_layer)
                current_layer = next_layer
                if not current_layer:
                    break

            # Downstream: who does this symbol call? (successors)
            downstream_dependencies = set(dep_graph.successors(symbol_id))

        target_symbol = self.store.get_symbol_by_id(self.repo_id, symbol_id)

        return {
            "target_symbol_id": symbol_id,
            "target_name": target_symbol.name if target_symbol else symbol_id,
            "max_depth": max_depth,
            "upstream_callers_count": len(upstream_impacted),
            "upstream_callers": sorted(list(upstream_impacted)),
            "downstream_dependencies_count": len(downstream_dependencies),
            "downstream_dependencies": sorted(list(downstream_dependencies)),
        }

    def get_hierarchical_tree(self) -> Dict[str, Any]:
        """Returns structured nested tree for dashboard and CLI rendering."""
        files = self.store.list_files(self.repo_id, include_deleted=False)
        tree: Dict[str, Any] = {"name": "root", "type": "repository", "children": []}

        file_nodes: Dict[str, Dict[str, Any]] = {}
        for f in files:
            symbols = self.store.get_symbols_by_file(self.repo_id, f.path)

            # Separate classes and standalone functions
            classes: Dict[str, Dict[str, Any]] = {}
            functions: List[Dict[str, Any]] = []

            for sym in symbols:
                if sym.symbol_type == SymbolType.CLASS:
                    classes[sym.id] = {
                        "id": sym.id,
                        "name": sym.name,
                        "type": "class",
                        "start_line": sym.start_line,
                        "end_line": sym.end_line,
                        "methods": [],
                    }
                elif sym.symbol_type == SymbolType.FUNCTION:
                    functions.append({
                        "id": sym.id,
                        "name": sym.name,
                        "type": "function",
                        "signature": sym.signature,
                        "start_line": sym.start_line,
                        "end_line": sym.end_line,
                    })

            for sym in symbols:
                if sym.symbol_type == SymbolType.METHOD and sym.parent_symbol_id in classes:
                    classes[sym.parent_symbol_id]["methods"].append({
                        "id": sym.id,
                        "name": sym.name,
                        "type": "method",
                        "signature": sym.signature,
                        "start_line": sym.start_line,
                        "end_line": sym.end_line,
                    })

            file_nodes[f.path] = {
                "id": f.path,
                "name": f.path,
                "type": "file",
                "language": f.language,
                "classes": list(classes.values()),
                "functions": functions,
                "symbol_count": len(symbols),
            }

        tree["children"] = list(file_nodes.values())
        return tree
