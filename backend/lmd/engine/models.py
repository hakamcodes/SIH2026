"""Canonical severity/status/verdict vocabulary. Do not add synonyms elsewhere.

Per CLAUDE.md section 4.3:
- severity: BLOCKER / MAJOR / MINOR / DIAGNOSTIC
- rule status: PASS / FAIL / REVIEW / NOT_APPLICABLE / NOT_IN_FORCE / NOT_EVALUABLE
- verdict: COMPLIANT / NON_COMPLIANT / NEEDS_REVIEW
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    BLOCKER = "BLOCKER"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    DIAGNOSTIC = "DIAGNOSTIC"


class RuleStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_IN_FORCE = "NOT_IN_FORCE"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class Verdict(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


@dataclass
class RuleResult:
    rule_id: str
    category: str
    severity: Severity
    status: RuleStatus
    on_fail_code: str | None
    message: str
    legal_basis: str
    citation_verified: bool = True


@dataclass
class ScanResult:
    overall_verdict: Verdict
    scan_date: str
    rule_results: dict[str, RuleResult] = field(default_factory=dict)

    @property
    def failed_rule_ids(self) -> list[str]:
        return [
            rid
            for rid, r in self.rule_results.items()
            if r.status == RuleStatus.FAIL and r.severity != Severity.DIAGNOSTIC
        ]

    @property
    def review_rule_ids(self) -> list[str]:
        return [rid for rid, r in self.rule_results.items() if r.status == RuleStatus.REVIEW]

    @property
    def diagnostic_rule_ids(self) -> list[str]:
        return [
            rid
            for rid, r in self.rule_results.items()
            if r.severity == Severity.DIAGNOSTIC
            and r.status not in (RuleStatus.NOT_APPLICABLE, RuleStatus.NOT_IN_FORCE)
        ]

    @property
    def applicable_count(self) -> int:
        return sum(
            1
            for r in self.rule_results.values()
            if r.status not in (RuleStatus.NOT_APPLICABLE, RuleStatus.NOT_IN_FORCE)
        )
