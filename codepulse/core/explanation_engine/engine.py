"""Grounded explanation engine generating What / Why / Impact assessments for code changes."""

from __future__ import annotations

from typing import Any, Dict, Optional

from codepulse.core.explanation_engine.llm_provider import BaseLLMProvider, LocalRuleBasedProvider
from codepulse.core.models import (
    ChangeExplanation,
    ChangeStatus,
    ImpactReport,
    SymbolDiff,
    SymbolType,
)


class ExplanationEngine:
    def __init__(self, provider: Optional[BaseLLMProvider] = None) -> None:
        self.provider = provider or LocalRuleBasedProvider()

    def explain_change(
        self,
        diff: SymbolDiff,
        task_description: Optional[str] = None,
        impact_report: Optional[ImpactReport] = None,
    ) -> ChangeExplanation:
        """Constructs evidence-grounded What / Why / Impact explanation for a symbol diff."""
        what_changed = self._generate_what_changed(diff)
        why = self._generate_why(task_description)
        impact = self._generate_impact(diff, impact_report)
        risk = impact_report.risk_level if impact_report else "LOW"

        return ChangeExplanation(
            symbol_name=diff.symbol_name,
            status=diff.status,
            what_changed=what_changed,
            why=why,
            impact=impact,
            risk_level=risk,
            grounded_evidence={
                "symbol_id": diff.symbol_id,
                "file_path": diff.file_path,
                "status": diff.status.value,
                "has_task_description": bool(task_description),
                "direct_callers_count": len(impact_report.direct_callers) if impact_report else 0,
                "related_tests_count": len(impact_report.related_tests) if impact_report else 0,
                "provider": self.provider.provider_name,
            },
        )

    @staticmethod
    def _generate_what_changed(diff: SymbolDiff) -> str:
        if diff.status == ChangeStatus.ADDED:
            sig = f" with signature `{diff.new_signature}`" if diff.new_signature else ""
            return f"Added new {diff.symbol_type.value} `{diff.symbol_name}`{sig} at line {diff.new_start_line or 'unknown'}."

        if diff.status == ChangeStatus.DELETED:
            return f"Removed {diff.symbol_type.value} `{diff.symbol_name}` (previously at line {diff.old_start_line or 'unknown'})."

        if diff.status == ChangeStatus.RENAMED:
            return f"Renamed symbol to `{diff.symbol_name}` with identical body logic."

        if diff.status == ChangeStatus.MODIFIED:
            parts = []
            if diff.old_signature and diff.new_signature and diff.old_signature != diff.new_signature:
                parts.append(f"Signature updated from `{diff.old_signature}` to `{diff.new_signature}`")

            if diff.diff_text:
                additions = sum(1 for line in diff.diff_text.splitlines() if line.startswith("+") and not line.startswith("+++"))
                deletions = sum(1 for line in diff.diff_text.splitlines() if line.startswith("-") and not line.startswith("---"))
                parts.append(f"modified implementation (+{additions} / -{deletions} lines)")
            else:
                parts.append("modified implementation body")

            return f"Modified {diff.symbol_type.value} `{diff.symbol_name}`: {'; '.join(parts)}."

        return f"{diff.symbol_type.value.capitalize()} `{diff.symbol_name}` is unchanged."

    @staticmethod
    def _generate_why(task_description: Optional[str]) -> str:
        if task_description and task_description.strip():
            return f"Correlated with observed agent task: \"{task_description.strip()}\""
        return "Reason not available from observed evidence."

    @staticmethod
    def _generate_impact(diff: SymbolDiff, impact_report: Optional[ImpactReport]) -> str:
        if not impact_report:
            return "Impact analysis not computed."

        direct_count = len(impact_report.direct_callers)
        indirect_count = len(impact_report.indirect_callers)
        test_count = len(impact_report.related_tests)

        if direct_count == 0 and indirect_count == 0:
            return f"No upstream callers detected in repository. Potential standalone change with {test_count} related test(s)."

        caller_names = [c.get("caller_name", "") for c in impact_report.direct_callers[:3]]
        callers_str = ", ".join(f"`{name}`" for name in caller_names if name)
        if direct_count > 3:
            callers_str += f" and {direct_count - 3} others"

        test_note = f"Covered by {test_count} test file(s)." if test_count > 0 else "No direct automated tests identified."

        return (
            f"{direct_count} direct caller(s) ({callers_str}) and {indirect_count} indirect dependent(s) "
            f"may be affected by changes to `{diff.symbol_name}`. {test_note}"
        )
