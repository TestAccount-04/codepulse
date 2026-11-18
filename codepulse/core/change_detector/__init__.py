"""Change detection engine for CodePulse."""

from codepulse.core.change_detector.diff_engine import DiffEngine
from codepulse.core.change_detector.git_tracker import GitTracker
from codepulse.core.change_detector.watcher import RepositoryWatcher
from codepulse.core.change_detector.coordinator import ChangeCoordinator

__all__ = [
    "DiffEngine",
    "GitTracker",
    "RepositoryWatcher",
    "ChangeCoordinator",
]
