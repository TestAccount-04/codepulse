"""Tests for RepositoryWatcher and debounced change handler."""

import time
from pathlib import Path
from codepulse.core.change_detector.watcher import RepositoryWatcher


def test_watcher_lifecycle_and_debounce(tmp_path: Path):
    events = []

    def on_change(event_type: str, path: str):
        events.append((event_type, path))

    watcher = RepositoryWatcher(
        root_dir=tmp_path,
        callback=on_change,
        debounce_seconds=0.1,
    )

    watcher.start()
    assert watcher.is_alive() is True
    time.sleep(0.15)

    # Create file
    test_file = tmp_path / "stream.py"
    test_file.write_text("x = 1\n", encoding="utf-8")

    # Rapid writes within debounce window
    time.sleep(0.02)
    test_file.write_text("x = 2\n", encoding="utf-8")
    time.sleep(0.02)
    test_file.write_text("x = 3\n", encoding="utf-8")

    # Wait for debounce timer to flush
    time.sleep(0.5)

    watcher.stop()
    assert watcher.is_alive() is False
    assert len(events) >= 1
    assert any("stream.py" in e[1] for e in events)
