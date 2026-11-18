"""Tests for repository scanner and incremental updates."""

from pathlib import Path
from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.repository_scanner.scanner import RepositoryScanner


def test_scanner_discovers_and_parses_files(tmp_path: Path):
    db_file = tmp_path / ".codepulse" / "codepulse.db"
    store = SQLiteStore(db_file)
    scanner = RepositoryScanner(store, repo_id="test")

    # Create dummy source files
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "app.py").write_text("def run_app():\n    return 42\n", encoding="utf-8")
    (src_dir / "index.js").write_text("function main() { console.log('hello'); }\n", encoding="utf-8")
    (src_dir / "types.ts").write_text("interface Config { port: number; }\n", encoding="utf-8")

    # Ignored directory
    ignored_dir = tmp_path / ".git"
    ignored_dir.mkdir()
    (ignored_dir / "git_internal.py").write_text("def git_thing(): pass\n", encoding="utf-8")

    result = scanner.scan_repository(tmp_path)
    assert result["scanned_files"] == 3
    assert result["parsed_files"] == 3
    assert result["skipped_files"] == 0

    metrics = store.get_metrics("test")
    assert metrics.file_count == 3
    assert metrics.languages.get("python") == 1
    assert metrics.languages.get("javascript") == 1
    assert metrics.languages.get("typescript") == 1


def test_scanner_incremental_skips_unchanged(tmp_path: Path):
    db_file = tmp_path / ".codepulse" / "codepulse.db"
    store = SQLiteStore(db_file)
    scanner = RepositoryScanner(store, repo_id="test")

    (tmp_path / "service.py").write_text("def process(): pass\n", encoding="utf-8")

    # First scan: parses 1 file
    res1 = scanner.scan_repository(tmp_path)
    assert res1["parsed_files"] == 1
    assert res1["skipped_files"] == 0

    # Second scan: file unchanged, so skipped!
    res2 = scanner.scan_repository(tmp_path)
    assert res2["parsed_files"] == 0
    assert res2["skipped_files"] == 1

    # Modify file
    (tmp_path / "service.py").write_text("def process():\n    return 'updated'\n", encoding="utf-8")
    res3 = scanner.scan_repository(tmp_path)
    assert res3["parsed_files"] == 1
    assert res3["skipped_files"] == 0


def test_scanner_handles_deleted_files(tmp_path: Path):
    db_file = tmp_path / ".codepulse" / "codepulse.db"
    store = SQLiteStore(db_file)
    scanner = RepositoryScanner(store, repo_id="test")

    temp_file = tmp_path / "temp.py"
    temp_file.write_text("def to_be_deleted(): pass\n", encoding="utf-8")

    scanner.scan_repository(tmp_path)
    assert len(store.list_files("test", include_deleted=False)) == 1

    # Delete file from disk
    temp_file.unlink()

    res = scanner.scan_repository(tmp_path)
    assert res["deleted_files"] == 1
    assert len(store.list_files("test", include_deleted=False)) == 0
    assert len(store.list_symbols("test")) == 0
