"""Tests for ExplanationEngine grounded What / Why / Impact assessments."""

from codepulse.core.explanation_engine.engine import ExplanationEngine
from codepulse.core.models import (
    ChangeStatus,
    ImpactReport,
    SymbolDiff,
    SymbolType,
)


def test_explanation_grounded_in_task_and_evidence():
    engine = ExplanationEngine()

    diff = SymbolDiff(
        symbol_id="src/auth.py::function::validate_token",
        symbol_name="validate_token",
        symbol_type=SymbolType.FUNCTION,
        file_path="src/auth.py",
        status=ChangeStatus.MODIFIED,
        old_signature="def validate_token(token)",
        new_signature="def validate_token(token, check_expiry=True)",
        diff_text="+    if check_expiry and is_expired(token): return False\n",
        new_start_line=15,
    )

    impact = ImpactReport(
        symbol_id=diff.symbol_id,
        symbol_name=diff.symbol_name,
        file_path=diff.file_path,
        direct_callers=[{"caller_name": "authenticate_user", "file_path": "src/auth.py", "line": 40}],
        indirect_callers=["src/api.py::function::login_handler"],
        related_tests=["tests/test_token.py::function::test_validate"],
        risk_level="MEDIUM",
        risk_score=3.5,
    )

    task_desc = "Reject expired JWT tokens during authentication"

    explanation = engine.explain_change(
        diff=diff,
        task_description=task_desc,
        impact_report=impact,
    )

    # 1. Verify What Changed
    assert "validate_token" in explanation.what_changed
    assert "Signature updated" in explanation.what_changed

    # 2. Verify Why (Grounded in task)
    assert task_desc in explanation.why

    # 3. Verify Impact
    assert "authenticate_user" in explanation.impact
    assert "Covered by 1 test file(s)" in explanation.impact
    assert explanation.risk_level == "MEDIUM"


def test_explanation_fallback_when_no_evidence():
    engine = ExplanationEngine()

    diff = SymbolDiff(
        symbol_id="src/calc.py::function::add",
        symbol_name="add",
        symbol_type=SymbolType.FUNCTION,
        file_path="src/calc.py",
        status=ChangeStatus.MODIFIED,
    )

    explanation = engine.explain_change(
        diff=diff,
        task_description=None,  # No evidence
        impact_report=None,
    )

    # Specification requirement: If the reason cannot be established, report exact string
    assert explanation.why == "Reason not available from observed evidence."
