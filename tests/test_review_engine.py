"""Tests for CodePulse Review Engine, safe Git rollback, review lifecycle, and API endpoints."""

import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from codepulse.backend.api.app import create_app
from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.change_detector.coordinator import ChangeCoordinator
from codepulse.core.change_detector.git_tracker import GitTracker
from codepulse.core.models import ChangeStatus, ReviewStatus, Symbol, SymbolType
from codepulse.core.repository_scanner.scanner import RepositoryScanner
from codepulse.core.review_engine.engine import ReviewEngine


def setup_git_repo(repo_dir: Path) -> GitTracker:
    """Helper to initialize a Git repository with an initial commit."""
    subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "TestUser"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@codepulse.dev"], cwd=str(repo_dir), check=True, capture_output=True)

    auth_file = repo_dir / "auth.py"
    auth_file.write_text(
        "def login(user, password):\n    return False\n\ndef logout(user):\n    return True\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial baseline"], cwd=str(repo_dir), check=True, capture_output=True)
    return GitTracker(repo_dir)


def test_review_storage_and_annotations(tmp_path: Path):
    db_file = tmp_path / "test.db"
    store = SQLiteStore(db_file)
    store.register_repository("default", str(tmp_path))

    # Get or create review
    rev = store.get_or_create_review("default", "sym_1", "src/file.py")
    assert rev.status == ReviewStatus.PENDING
    assert rev.symbol_id == "sym_1"

    # Add annotations
    ann1 = store.add_review_annotation("default", "sym_1", "First note", author="alice")
    ann2 = store.add_review_annotation("default", "sym_1", "Second note", author="bob")
    assert ann1.note == "First note"
    assert ann2.author == "bob"

    # Set status
    updated = store.set_review_status(
        "default", "sym_1", ReviewStatus.ACCEPTED, decision_reason="Looks solid"
    )
    assert updated.status == ReviewStatus.ACCEPTED
    assert updated.decision_reason == "Looks solid"
    assert len(updated.annotations) == 2

    # Query reviews
    all_revs = store.list_reviews("default")
    assert len(all_revs) == 1
    assert all_revs[0].status == ReviewStatus.ACCEPTED


def test_review_engine_lifecycle(tmp_path: Path):
    git_tracker = setup_git_repo(tmp_path)
    db_file = tmp_path / ".codepulse" / "codepulse.db"
    store = SQLiteStore(db_file)
    store.register_repository("default", str(tmp_path))

    scanner = RepositoryScanner(store, repo_id="default")
    scanner.scan_repository(tmp_path)

    # Modify login()
    auth_file = tmp_path / "auth.py"
    auth_file.write_text(
        "def login(user, password):\n    # Enhanced auth with token check\n    return token_verify(user, password)\n\ndef logout(user):\n    return True\n",
        encoding="utf-8",
    )

    coordinator = ChangeCoordinator(tmp_path, store, repo_id="default")
    diffs = coordinator.handle_file_change("modified", "auth.py")
    assert len(diffs) >= 1

    review_engine = ReviewEngine(
        root_path=tmp_path,
        store=store,
        repo_id="default",
        git_tracker=git_tracker,
    )

    # Check reviews list
    reviews = review_engine.get_reviews()
    assert len(reviews) >= 1
    assert any(r.status == ReviewStatus.PENDING for r in reviews)

    # Detail check
    login_sym = next(s for s in store.list_symbols("default") if s.name == "login")
    detail = review_engine.get_review_detail(login_sym.id)
    assert detail is not None
    assert detail.symbol_name == "login"
    assert "return False" in (detail.original_code or "")
    assert "token_verify" in (detail.updated_code or "")
    assert detail.explanation is not None

    # Mark as reviewed with note
    reviewed_item = review_engine.mark_reviewed(login_sym.id, note="Checked logic flow")
    assert reviewed_item.status == ReviewStatus.REVIEWED
    assert len(reviewed_item.annotations) >= 1

    # Accept change (spec rule: acceptance preserves repository files)
    accepted_item = review_engine.accept_change(login_sym.id)
    assert accepted_item.status == ReviewStatus.ACCEPTED
    # Verify disk code is preserved intact
    assert "token_verify" in auth_file.read_text(encoding="utf-8")


def test_review_engine_safe_rollback_single_symbol(tmp_path: Path):
    git_tracker = setup_git_repo(tmp_path)
    db_file = tmp_path / ".codepulse" / "codepulse.db"
    store = SQLiteStore(db_file)
    store.register_repository("default", str(tmp_path))

    scanner = RepositoryScanner(store, repo_id="default")
    scanner.scan_repository(tmp_path)

    auth_file = tmp_path / "auth.py"
    auth_file.write_text(
        "def login(user, password):\n    raise NotImplementedError()\n\ndef logout(user):\n    return True\n",
        encoding="utf-8",
    )

    coordinator = ChangeCoordinator(tmp_path, store, repo_id="default")
    coordinator.handle_file_change("modified", "auth.py")

    review_engine = ReviewEngine(
        root_path=tmp_path,
        store=store,
        repo_id="default",
        git_tracker=git_tracker,
    )

    login_sym = next(s for s in store.list_symbols("default") if s.name == "login")
    res = review_engine.reject_change(login_sym.id, reason="Bad exception raised", safe_rollback=True)
    assert res["success"] is True
    assert res["rolled_back"] is True

    # Check file was safely restored to HEAD
    restored_content = auth_file.read_text(encoding="utf-8")
    assert "return False" in restored_content
    assert "NotImplementedError" not in restored_content


def test_review_engine_safe_rollback_preserves_unrelated_changes(tmp_path: Path):
    git_tracker = setup_git_repo(tmp_path)
    db_file = tmp_path / ".codepulse" / "codepulse.db"
    store = SQLiteStore(db_file)
    store.register_repository("default", str(tmp_path))

    scanner = RepositoryScanner(store, repo_id="default")
    scanner.scan_repository(tmp_path)

    # Modify BOTH login() and logout()
    auth_file = tmp_path / "auth.py"
    auth_file.write_text(
        "def login(user, password):\n    # Unwanted AI edit\n    return 'hacked'\n\ndef logout(user):\n    # User personal edit\n    print('User logged out')\n    return True\n",
        encoding="utf-8",
    )

    coordinator = ChangeCoordinator(tmp_path, store, repo_id="default")
    coordinator.handle_file_change("modified", "auth.py")

    review_engine = ReviewEngine(
        root_path=tmp_path,
        store=store,
        repo_id="default",
        git_tracker=git_tracker,
    )

    login_sym = next(s for s in store.list_symbols("default") if s.name == "login")
    # Reject ONLY login() with safe rollback
    res = review_engine.reject_change(login_sym.id, reason="Unwanted AI edit", safe_rollback=True)
    assert res["success"] is True

    current_content = auth_file.read_text(encoding="utf-8")
    # Verify login() was reverted to HEAD
    assert "return False" in current_content
    assert "'hacked'" not in current_content
    # CRITICAL: Verify the user's unrelated edit to logout() was PRESERVED!
    assert "User personal edit" in current_content
    assert "print('User logged out')" in current_content


def test_review_api_endpoints(tmp_path: Path):
    setup_git_repo(tmp_path)
    db_file = tmp_path / ".codepulse" / "codepulse.db"
    store = SQLiteStore(db_file)
    store.register_repository("default", str(tmp_path))

    # Modify file
    auth_file = tmp_path / "auth.py"
    auth_file.write_text(
        "def login(user, password):\n    return True\n\ndef logout(user):\n    return True\n",
        encoding="utf-8",
    )

    app = create_app(repo_root=tmp_path, db_path=db_file)
    with TestClient(app) as client:
        # Trigger scan
        client.post("/api/scan")

        # Symbols
        syms = client.get("/api/symbols").json()
        login_sym = next(s for s in syms if s["name"] == "login")

        # GET /api/reviews
        rev_resp = client.get("/api/reviews")
        assert rev_resp.status_code == 200

        # GET /api/reviews/{symbol_id}
        det_resp = client.get(f"/api/reviews/{login_sym['id']}")
        assert det_resp.status_code == 200
        det_data = det_resp.json()
        assert det_data["symbol_name"] == "login"

        # POST /api/reviews/{symbol_id}/notes
        note_resp = client.post(
            f"/api/reviews/{login_sym['id']}/notes",
            json={"note": "Test review note", "author": "tester"},
        )
        assert note_resp.status_code == 200
        assert note_resp.json()["note"] == "Test review note"

        # POST /api/reviews/{symbol_id}/status (Accept)
        status_resp = client.post(
            f"/api/reviews/{login_sym['id']}/status",
            json={"status": "accepted", "author": "tester"},
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "accepted"

        # POST /api/reviews/{symbol_id}/rollback
        rb_resp = client.post(
            f"/api/reviews/{login_sym['id']}/rollback",
            json={"reason": "Testing rollback endpoint", "safe_rollback": True},
        )
        assert rb_resp.status_code == 200
        assert rb_resp.json()["success"] is True
