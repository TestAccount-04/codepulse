"""Git tracking and repository baseline extraction using Git CLI and GitPython."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import git


class GitTracker:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = Path(repo_path).resolve()
        self._repo: Optional[git.Repo] = None
        self._init_repo()

    def _init_repo(self) -> None:
        try:
            self._repo = git.Repo(self.repo_path, search_parent_directories=True)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            self._repo = None

    @property
    def is_git_repo(self) -> bool:
        return self._repo is not None

    def get_head_commit(self) -> Optional[str]:
        if not self._repo:
            return None
        try:
            return self._repo.head.commit.hexsha
        except Exception:
            return None

    def get_current_branch(self) -> Optional[str]:
        if not self._repo:
            return None
        try:
            return self._repo.active_branch.name
        except Exception:
            return None

    def get_uncommitted_changes(self) -> Dict[str, List[str]]:
        """Returns categorized list of all uncommitted files."""
        result: Dict[str, List[str]] = {
            "modified": [],
            "untracked": [],
            "staged": [],
            "deleted": [],
            "renamed": [],
        }
        if not self._repo:
            return result

        try:
            # Untracked files
            result["untracked"] = [
                Path(p).as_posix() for p in self._repo.untracked_files
            ]

            # Unstaged diff against index
            for diff in self._repo.index.diff(None):
                path = Path(diff.a_path or diff.b_path).as_posix()
                if diff.deleted_file:
                    result["deleted"].append(path)
                elif diff.renamed_file:
                    result["renamed"].append(path)
                else:
                    result["modified"].append(path)

            # Staged diff against HEAD (if commits exist)
            try:
                head_commit = self._repo.head.commit
                for diff in head_commit.diff():
                    path = Path(diff.a_path or diff.b_path).as_posix()
                    if path not in result["modified"] and path not in result["deleted"]:
                        result["staged"].append(path)
            except (ValueError, git.BadName):
                pass  # Empty repository with no commits yet

        except Exception:
            pass

        return result

    def get_file_diff(self, file_path: str, staged: bool = False) -> str:
        """Returns unified diff for a single file against HEAD or index."""
        if not self._repo:
            return ""

        clean_path = Path(file_path).as_posix()
        try:
            cmd = ["git", "diff"]
            if staged:
                cmd.append("--cached")
            cmd.extend(["--", clean_path])

            output = subprocess.check_output(
                cmd,
                cwd=str(self.repo_path),
                stderr=subprocess.DEVNULL,
            )
            return output.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def get_file_content_at_head(self, file_path: str) -> Optional[bytes]:
        """Retrieves file bytes as stored at HEAD commit."""
        if not self._repo:
            return None
        clean_path = Path(file_path).as_posix()
        try:
            output = subprocess.check_output(
                ["git", "show", f"HEAD:{clean_path}"],
                cwd=str(self.repo_path),
                stderr=subprocess.DEVNULL,
            )
            return output
        except Exception:
            return None
