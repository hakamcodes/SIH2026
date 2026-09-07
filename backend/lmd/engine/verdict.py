"""Verdict aggregation. Fixes CLAUDE.md defect #8 (inverted precedence).

Precedence, highest first: NON_COMPLIANT > NEEDS_REVIEW > COMPLIANT.
A DIAGNOSTIC-severity rule can never contribute to NON_COMPLIANT (CLAUDE.md
section 4.2) -- it is structurally excluded from the FAIL check below.
"""
from __future__ import annotations

from .models import RuleResult, RuleStatus, Severity, Verdict

_BLOCKING_SEVERITIES = (Severity.BLOCKER, Severity.MAJOR, Severity.MINOR)


def aggregate(rule_results: dict[str, RuleResult]) -> Verdict:
    has_fail = any(
        r.status == RuleStatus.FAIL and r.severity in _BLOCKING_SEVERITIES
        for r in rule_results.values()
    )
    if has_fail:
        return Verdict.NON_COMPLIANT

    has_review = any(r.status == RuleStatus.REVIEW for r in rule_results.values())
    if has_review:
        return Verdict.NEEDS_REVIEW

    return Verdict.COMPLIANT
