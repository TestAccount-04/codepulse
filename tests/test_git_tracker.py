"""Tests for GitTracker uncommitted tracking and diff extraction."""

from pathlib import Path
import subprocess
import pytest
from codepulse.core.change_detector.git_tracker import GitTracker


def test_git_tracker_on_initialized_repo(tmp_path: Path):
    # Initialize a test git repo
    subprocess.check_call(["git", "init"], cwd=str(tmp_path), stderr=subprocess.DEVNULL)
    subprocess.check_call(
        ["git", "config", "user.name", "Test User"],
        cwd=str(tmp_path),
        stderr=subprocess.DEVNULL,
    )
    subprocess.check_call(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(tmp_path),
        stderr=subprocess.DEVNULL,
    )

    tracker = GitTracker(tmp_path)
    assert tracker.is_git_repo is True

    # Create file and commit
    test_file = tmp_path / "hello.py"
    test_file.write_text("def initial(): return 1\n", encoding="utf-8")
    subprocess.check_call(["git", "add", "hello.py"], cwd=str(tmp_path), stderr=subprocess.DEVNULL)
    subprocess.check_call(["git", "commit", "-m", "initial commit"], cwd=str(tmp_path), stderr=subprocess.DEVNULL)

    # Check commit sha and content at HEAD
    head_sha = tracker.get_head_commit()
    assert head_sha is not None
    head_content = tracker.get_file_content_at_head("hello.py")
    assert head_content is not None
    assert head_content.replace(b"\r\n", b"\n") == b"def initial(): return 1\n"

    # Modify file
    test_file.write_text("def initial(): return 2\n", encoding="utf-8")
    uncommitted = tracker.get_uncommitted_changes()
    assert "hello.py" in uncommitted["modified"]

    # Diff
    diff = tracker.get_file_diff("hello.py")
    assert "-def initial(): return 1" in diff
    assert "+def initial(): return 2" in diff


def test_git_tracker_non_git_dir(tmp_path: Path):
    tracker = GitTracker(tmp_path)
    # If not a git repo or in subfolder without search_parent
    # We test graceful handling
    uncommitted = tracker.get_uncommitted_changes()
    assert isinstance(uncommitted, dict)
    assert tracker.get_file_diff("fake.py") == ""
