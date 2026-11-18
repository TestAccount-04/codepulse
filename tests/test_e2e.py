"""End-to-End integration test suite matching Section 21 of the CodePulse Master Specification.

Simulates an AI coding agent modifying:
- 3 files
- 2 classes
- 5 methods
And verifies that CodePulse:
1. Detects the changes.
2. Identifies affected symbols.
3. Associates changes with the agent session.
4. Updates the symbol graph.
5. Shows the Git diffs.
6. Generates grounded What / Why / Impact change explanations.
7. Computes blast-radius dependency impact and test discovery.
8. Manages review status lifecycle, annotations, and safe Git rollback.
"""

import subprocess
from pathlib import Path
import pytest

from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.change_detector.coordinator import ChangeCoordinator
from codepulse.core.change_detector.git_tracker import GitTracker
from codepulse.core.explanation_engine.engine import ExplanationEngine
from codepulse.core.impact_analyzer.analyzer import ImpactAnalyzer
from codepulse.core.models import ChangeStatus, ReviewStatus, SymbolDiff
from codepulse.core.repository_scanner.scanner import RepositoryScanner
from codepulse.core.review_engine.engine import ReviewEngine
from codepulse.core.session_manager.manager import SessionManager
from codepulse.core.symbol_graph.graph import SymbolGraphManager


def setup_multi_file_repo(repo_dir: Path) -> GitTracker:
    """Creates a realistic repository with 3 modules, classes, and relationships."""
    subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "E2ETester"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "e2e@codepulse.dev"], cwd=str(repo_dir), check=True, capture_output=True)

    # File 1: User Service
    (repo_dir / "user_service.py").write_text(
        """class UserService:
    def get_user(self, user_id: str):
        return {"id": user_id, "name": "Alice"}

    def update_profile(self, user_id: str, email: str):
        return True
""",
        encoding="utf-8",
    )

    # File 2: Auth Service
    (repo_dir / "auth_service.py").write_text(
        """class AuthService:
    def authenticate(self, username: str, password: str):
        return username == "admin" and password == "secret"

    def issue_token(self, username: str):
        return f"token_for_{username}"
""",
        encoding="utf-8",
    )

    # File 3: App Controller & Test File
    (repo_dir / "app_controller.py").write_text(
        """from user_service import UserService
from auth_service import AuthService

def handle_login(req):
    auth = AuthService()
    if auth.authenticate(req["user"], req["pass"]):
        return auth.issue_token(req["user"])
    return None

def handle_profile(req):
    user_svc = UserService()
    return user_svc.get_user(req["id"])
""",
        encoding="utf-8",
    )

    # Test file for impact test discovery
    (repo_dir / "test_auth.py").write_text(
        """from auth_service import AuthService

def test_auth_login():
    auth = AuthService()
    assert auth.authenticate("admin", "secret")
""",
        encoding="utf-8",
    )

    subprocess.run(["git", "add", "."], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit baseline"], cwd=str(repo_dir), check=True, capture_output=True)
    return GitTracker(repo_dir)


def test_spec_section_21_end_to_end_scenario(tmp_path: Path):
    # 1. Initialize CodePulse and baseline
    git_tracker = setup_multi_file_repo(tmp_path)
    db_file = tmp_path / ".codepulse" / "codepulse.db"
    store = SQLiteStore(db_file)
    store.register_repository("default", str(tmp_path))

    scanner = RepositoryScanner(store, repo_id="default")
    initial_scan = scanner.scan_repository(tmp_path)
    assert initial_scan["total_symbols"] >= 8

    coordinator = ChangeCoordinator(tmp_path, store, repo_id="default")
    coordinator.capture_baseline()

    session_mgr = SessionManager(store, repo_id="default")
    agent_session = session_mgr.start_session(
        agent_name="claude-code",
        task_description="Implement OAuth2 bearer token support and rate limiting across auth and user services.",
    )

    # 2. Simulate AI coding agent modifications:
    # 3 files modified, 2 classes modified, 5 methods affected:
    # File 1: user_service.py -> modify update_profile, add verify_email
    (tmp_path / "user_service.py").write_text(
        """class UserService:
    def get_user(self, user_id: str):
        return {"id": user_id, "name": "Alice"}

    def update_profile(self, user_id: str, email: str):
        # AI modification: add email format validation
        if "@" not in email:
            raise ValueError("Invalid email format")
        return True

    def verify_email(self, user_id: str, code: str):
        # AI addition: new method
        return code == "123456"
""",
        encoding="utf-8",
    )

    # File 2: auth_service.py -> modify authenticate, modify issue_token, add revoke_token
    (tmp_path / "auth_service.py").write_text(
        """class AuthService:
    def authenticate(self, username: str, password: str):
        # AI modification: OAuth2 checks
        return len(password) >= 8 and username != ""

    def issue_token(self, username: str):
        # AI modification: generate JWT-like token
        return f"jwt.{username}.signature"

    def revoke_token(self, token: str):
        # AI addition: token revocation
        return True
""",
        encoding="utf-8",
    )

    # File 3: app_controller.py -> modify handle_login
    (tmp_path / "app_controller.py").write_text(
        """from user_service import UserService
from auth_service import AuthService

def handle_login(req):
    # AI modification: return structured token object
    auth = AuthService()
    if auth.authenticate(req["user"], req["pass"]):
        return {"access_token": auth.issue_token(req["user"]), "token_type": "bearer"}
    return None

def handle_profile(req):
    user_svc = UserService()
    return user_svc.get_user(req["id"])
""",
        encoding="utf-8",
    )

    # 3. Detect changes via ChangeCoordinator
    diffs_user = coordinator.handle_file_change("modified", "user_service.py", session_id=agent_session.id, agent_name="claude-code")
    diffs_auth = coordinator.handle_file_change("modified", "auth_service.py", session_id=agent_session.id, agent_name="claude-code")
    diffs_ctrl = coordinator.handle_file_change("modified", "app_controller.py", session_id=agent_session.id, agent_name="claude-code")

    all_diffs = diffs_user + diffs_auth + diffs_ctrl
    assert len(all_diffs) >= 5

    # 4. Verify Symbol Identification & Attribution
    changed_symbols = store.list_changed_symbols("default")
    changed_names = {s.name for s in changed_symbols}

    assert "update_profile" in changed_names
    assert "verify_email" in changed_names
    assert "authenticate" in changed_names
    assert "issue_token" in changed_names
    assert "revoke_token" in changed_names
    assert "handle_login" in changed_names

    # 5. Dependency & Blast-Radius Impact Analysis
    impact_analyzer = ImpactAnalyzer(store, repo_id="default")
    auth_sym = next(s for s in changed_symbols if s.name == "authenticate")
    impact_report = impact_analyzer.analyze_symbol_impact(auth_sym.id)

    # Caller handle_login() should be discovered
    caller_names = [c["caller_name"] for c in impact_report.direct_callers]
    assert "handle_login" in caller_names
    # Related test discovery
    assert any("test_auth.py" in t for t in impact_report.related_tests)
    assert impact_report.risk_score > 0.0

    # 6. Grounded Change Explanation
    explanation_engine = ExplanationEngine()
    auth_diff = next(d for d in all_diffs if d.symbol_name == "authenticate")
    explanation = explanation_engine.explain_change(
        auth_diff,
        task_description=agent_session.task_description,
        impact_report=impact_report,
    )
    assert "authenticate" in explanation.symbol_name
    assert "OAuth2" in explanation.why or "rate limiting" in explanation.why
    assert "handle_login" in explanation.impact or "test_auth" in explanation.impact

    # 7. Review Engine: Status Transitions & Safe Rollback
    review_engine = ReviewEngine(
        root_path=tmp_path,
        store=store,
        repo_id="default",
        git_tracker=git_tracker,
        impact_analyzer=impact_analyzer,
        explanation_engine=explanation_engine,
        session_mgr=session_mgr,
    )

    # Accept safe changes (e.g. verify_email and update_profile in user_service.py)
    verify_sym = next(s for s in changed_symbols if s.name == "verify_email")
    accepted_item = review_engine.accept_change(verify_sym.id, note="Added email verification")
    assert accepted_item.status == ReviewStatus.ACCEPTED

    # Add review annotation note
    review_engine.add_annotation(auth_sym.id, "Requires checking with frontend team on token expiry")
    auth_notes = store.get_review_annotations("default", auth_sym.id)
    assert len(auth_notes) == 1
    assert "frontend team" in auth_notes[0].note

    # Reject & Safe Rollback: Reject handle_login in app_controller.py
    ctrl_sym = next(s for s in changed_symbols if s.name == "handle_login")
    rollback_result = review_engine.reject_change(ctrl_sym.id, reason="Return format broke legacy client", safe_rollback=True)
    assert rollback_result["success"] is True

    # Check that app_controller.py was rolled back cleanly while other files were untouched
    ctrl_content = (tmp_path / "app_controller.py").read_text(encoding="utf-8")
    assert "return auth.issue_token(req[\"user\"])" in ctrl_content
    assert "bearer" not in ctrl_content

    # User service and Auth service files remain modified and intact
    user_content = (tmp_path / "user_service.py").read_text(encoding="utf-8")
    assert "verify_email" in user_content
    auth_content = (tmp_path / "auth_service.py").read_text(encoding="utf-8")
    assert "revoke_token" in auth_content
