"""Performance and scalability benchmarks for CodePulse repository scanner and symbol graph."""

import time
from pathlib import Path
import pytest

from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.repository_scanner.scanner import RepositoryScanner
from codepulse.core.symbol_graph.graph import SymbolGraphManager


def test_large_repository_scan_performance(tmp_path: Path):
    """Verifies scanner performance on a multi-module repository with 100 files and 400+ symbols."""
    db_file = tmp_path / "perf.db"
    store = SQLiteStore(db_file)
    store.register_repository("default", str(tmp_path))

    # Generate 100 python source files
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)

    for i in range(100):
        module_file = src_dir / f"module_{i}.py"
        content = f"""# Module {i}
class Handler_{i}:
    def process_{i}(self, data: str) -> bool:
        return len(data) > 0

    def validate_{i}(self, item: int) -> int:
        return item * 2

def helper_{i}(x: int) -> int:
    h = Handler_{i}()
    return h.validate_{i}(x)
"""
        module_file.write_text(content, encoding="utf-8")

    scanner = RepositoryScanner(store, repo_id="default")

    # Measure initial full scan duration
    t0 = time.perf_counter()
    result = scanner.scan_repository(tmp_path)
    t1 = time.perf_counter()
    full_scan_time = t1 - t0

    assert result["scanned_files"] == 100
    assert result["parsed_files"] == 100
    assert result["total_symbols"] >= 300
    # Full scan of 100 files with Tree-sitter and SQLite must finish in under 5.0 seconds
    assert full_scan_time < 5.0, f"Full scan took too long: {full_scan_time:.2f}s"

    # Measure incremental scan duration (no files modified)
    t2 = time.perf_counter()
    inc_result = scanner.scan_repository(tmp_path)
    t3 = time.perf_counter()
    inc_scan_time = t3 - t2

    assert inc_result["scanned_files"] == 100
    assert inc_result["parsed_files"] == 0
    assert inc_result["skipped_files"] == 100
    # Incremental scan must be fast (< 0.5s for 100 files)
    assert inc_scan_time < 0.5, f"Incremental scan took too long: {inc_scan_time:.2f}s"
    assert full_scan_time > inc_scan_time


def test_deep_blast_radius_traversal_performance(tmp_path: Path):
    """Verifies graph traversal performance across deeply nested call chains."""
    db_file = tmp_path / "graph_perf.db"
    store = SQLiteStore(db_file)
    store.register_repository("default", str(tmp_path))

    src_dir = tmp_path / "chain"
    src_dir.mkdir()

    # Generate a linear call chain of 20 functions: f0 calls f1, f1 calls f2...
    for i in range(20):
        next_call = f"    from chain.step_{i+1} import step_{i+1}\n    return step_{i+1}()\n" if i < 19 else "    return 42\n"
        code = f"def step_{i}():\n{next_call}"
        (src_dir / f"step_{i}.py").write_text(code, encoding="utf-8")

    scanner = RepositoryScanner(store, repo_id="default")
    scanner.scan_repository(tmp_path)

    graph_mgr = SymbolGraphManager(store, repo_id="default")

    target_sym_id = "chain/step_19.py::function::step_19"

    t0 = time.perf_counter()
    blast = graph_mgr.get_blast_radius(target_sym_id, max_depth=10)
    t1 = time.perf_counter()

    traversal_time = t1 - t0
    # Graph traversal should complete in less than 50 milliseconds
    assert traversal_time < 0.05, f"Graph traversal took too long: {traversal_time:.4f}s"
