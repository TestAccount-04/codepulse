"""Impact and blast-radius analyzer with test relationship discovery and risk scoring."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import networkx as nx

from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.models import (
    ImpactReport,
    RelationshipType,
    Symbol,
    SymbolType,
)
from codepulse.core.symbol_graph.graph import SymbolGraphManager


class ImpactAnalyzer:
    def __init__(self, store: SQLiteStore, repo_id: str = "default") -> None:
        self.store = store
        self.repo_id = repo_id
        self.graph_mgr = SymbolGraphManager(store, repo_id=self.repo_id)

    def analyze_symbol_impact(self, symbol_id: str, depth: int = 3) -> ImpactReport:
        """Performs deep blast-radius analysis across callers, inheritance, and test suites."""
        target_symbol = self.store.get_symbol_by_id(self.repo_id, symbol_id)
        symbol_name = target_symbol.name if target_symbol else symbol_id.split("::")[-1]
        file_path = target_symbol.file_path if target_symbol else ""

        dep_graph = self.graph_mgr.build_dependency_graph()

        direct_callers: List[Dict[str, Any]] = []
        indirect_callers_set: Set[str] = set()
        direct_callees: List[str] = []
        imports_list: List[str] = []
        inherits_list: List[str] = []
        related_tests: List[str] = []

        # Target outgoing relationships
        outgoing_rels = self.store.get_relationships(self.repo_id, source_id=symbol_id)
        for rel in outgoing_rels:
            if rel.relationship_type == RelationshipType.CALLS:
                direct_callees.append(rel.target_id)
            elif rel.relationship_type == RelationshipType.IMPORTS:
                imports_list.append(rel.target_id)
            elif rel.relationship_type == RelationshipType.INHERITS:
                inherits_list.append(rel.target_id)

        # Incoming relationships: callers of this symbol or its name
        incoming_rels = self.store.get_relationships(self.repo_id, target_id=symbol_id)
        # Also check name-based matching if callers referenced symbol by name
        if target_symbol:
            name_incoming = self.store.get_relationships(self.repo_id, target_id=target_symbol.name)
            for r in name_incoming:
                if r not in incoming_rels:
                    incoming_rels.append(r)

        direct_caller_ids: Set[str] = set()
        for r in incoming_rels:
            if r.relationship_type == RelationshipType.CALLS:
                direct_caller_ids.add(r.source_id)
                caller_sym = self.store.get_symbol_by_id(self.repo_id, r.source_id)
                direct_callers.append({
                    "caller_id": r.source_id,
                    "caller_name": caller_sym.name if caller_sym else r.source_id,
                    "file_path": caller_sym.file_path if caller_sym else "",
                    "line": caller_sym.start_line if caller_sym else 0,
                    "is_static": True,
                })

        # Multi-hop indirect callers traversal
        current_layer = set(direct_caller_ids)
        visited = set(direct_caller_ids) | {symbol_id}

        for _ in range(1, depth):
            next_layer: Set[str] = set()
            for cid in current_layer:
                if cid in dep_graph:
                    preds = set(dep_graph.predecessors(cid)) - visited
                    next_layer.update(preds)
            indirect_callers_set.update(next_layer)
            visited.update(next_layer)
            current_layer = next_layer
            if not current_layer:
                break

        # Test relationship discovery
        all_callers = set(direct_caller_ids) | indirect_callers_set
        for caller_id in all_callers:
            if self._is_test_symbol(caller_id):
                related_tests.append(caller_id)

        # Check if test files in repo import the target's file
        if file_path:
            file_rels = self.store.get_relationships(self.repo_id, target_id=file_path)
            for fr in file_rels:
                if fr.relationship_type in (RelationshipType.IMPORTS, RelationshipType.TESTS):
                    if self._is_test_symbol(fr.source_id):
                        related_tests.append(fr.source_id)

        # Risk scoring calculation
        risk_score, risk_level = self._compute_risk_score(
            direct_callers_count=len(direct_callers),
            indirect_callers_count=len(indirect_callers_set),
            has_tests=len(related_tests) > 0,
            inherits_count=len(inherits_list),
        )

        return ImpactReport(
            symbol_id=symbol_id,
            symbol_name=symbol_name,
            file_path=file_path,
            direct_callers=direct_callers,
            indirect_callers=sorted(list(indirect_callers_set)),
            direct_callees=sorted(list(set(direct_callees))),
            imports=sorted(list(set(imports_list))),
            inherits=sorted(list(set(inherits_list))),
            related_tests=sorted(list(set(related_tests))),
            risk_level=risk_level,
            risk_score=risk_score,
        )

    @staticmethod
    def _is_test_symbol(symbol_or_path: str) -> bool:
        lower = symbol_or_path.lower()
        parts = lower.replace("\\", "/").split("/")
        filename = parts[-1]
        return (
            "test" in filename
            or "spec" in filename
            or filename.startswith("test_")
            or filename.endswith("_test.py")
            or ".spec." in filename
            or ".test." in filename
        )

    @staticmethod
    def _compute_risk_score(
        direct_callers_count: int,
        indirect_callers_count: int,
        has_tests: bool,
        inherits_count: int,
    ) -> tuple[float, str]:
        score = 1.0  # Base score
        score += direct_callers_count * 1.5
        score += indirect_callers_count * 0.8
        score += inherits_count * 1.2

        if not has_tests and (direct_callers_count > 0 or indirect_callers_count > 0):
            score += 2.0  # Penalty for unmonitored blast radius
        elif has_tests:
            score = max(1.0, score - 1.0)  # Credit for test coverage

        score = min(10.0, round(score, 1))

        if score >= 7.5:
            level = "CRITICAL"
        elif score >= 5.0:
            level = "HIGH"
        elif score >= 2.5:
            level = "MEDIUM"
        else:
            level = "LOW"

        return score, level
