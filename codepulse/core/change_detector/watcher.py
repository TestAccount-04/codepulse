"""Filesystem change watcher with debouncing and ignore pattern filtering."""

from __future__ import annotations

import os
import platform
import threading
import time
from pathlib import Path
from typing import Callable, Dict, Optional, Set
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from codepulse.core.repository_scanner.scanner import DEFAULT_IGNORE_PATTERNS


class DebouncedChangeHandler(FileSystemEventHandler):
    def __init__(
        self,
        root_dir: Path,
        callback: Callable[[str, str], None],
        ignore_patterns: Set[str],
        supported_extensions: Set[str],
        debounce_seconds: float = 0.3,
    ) -> None:
        super().__init__()
        self.root_dir = Path(root_dir).resolve()
        self.callback = callback
        self.ignore_patterns = ignore_patterns
        self.supported_extensions = {ext.lower() for ext in supported_extensions}
        self.debounce_seconds = debounce_seconds

        self._pending_events: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._queue_event("created", event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._queue_event("modified", event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._queue_event("deleted", event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._queue_event("deleted", event.src_path)
            if hasattr(event, "dest_path"):
                self._queue_event("created", event.dest_path)

    def _queue_event(self, event_type: str, abs_path: str) -> None:
        path_obj = Path(abs_path)
        ext = path_obj.suffix.lower()
        if ext not in self.supported_extensions:
            return

        try:
            rel_path = Path(os.path.relpath(path_obj.resolve(), self.root_dir.resolve())).as_posix()
        except Exception:
            return

        # Check ignored path
        parts = rel_path.split("/")
        for part in parts:
            if part in {".git", ".venv", "venv", "node_modules", "__pycache__", ".codepulse"}:
                return

        with self._lock:
            self._pending_events[rel_path] = event_type
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_seconds, self._flush_events)
            self._timer.daemon = True
            self._timer.start()

    def _flush_events(self) -> None:
        with self._lock:
            events_to_emit = dict(self._pending_events)
            self._pending_events.clear()
            self._timer = None

        for rel_path, event_type in events_to_emit.items():
            try:
                self.callback(event_type, rel_path)
            except Exception:
                pass


class RepositoryWatcher:
    def __init__(
        self,
        root_dir: Path,
        callback: Callable[[str, str], None],
        ignore_patterns: Optional[Set[str]] = None,
        supported_extensions: Optional[Set[str]] = None,
        debounce_seconds: float = 0.3,
        observer_cls: Optional[type] = None,
    ) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.callback = callback
        self.ignore_patterns = ignore_patterns or set(DEFAULT_IGNORE_PATTERNS)
        self.supported_extensions = supported_extensions or {
            ".py",
            ".js",
            ".jsx",
            ".mjs",
            ".ts",
            ".tsx",
            ".java",
        }
        self.debounce_seconds = debounce_seconds

        if observer_cls is not None:
            self.observer_cls = observer_cls
        elif platform.system() == "Windows":
            self.observer_cls = PollingObserver
        else:
            self.observer_cls = Observer

        self._observer: Optional[Observer] = None
        self._handler = DebouncedChangeHandler(
            root_dir=self.root_dir,
            callback=self.callback,
            ignore_patterns=self.ignore_patterns,
            supported_extensions=self.supported_extensions,
            debounce_seconds=self.debounce_seconds,
        )

    def start(self) -> None:
        if self._observer and self._observer.is_alive():
            return
        if self.observer_cls == PollingObserver:
            self._observer = PollingObserver(timeout=0.1)
        else:
            self._observer = self.observer_cls()
        self._observer.schedule(self._handler, str(self.root_dir), recursive=True)
        self._observer.daemon = True
        self._observer.start()

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._observer = None

    def is_alive(self) -> bool:
        return self._observer is not None and self._observer.is_alive()
