"""Verdict aggregation -- covers CLAUDE.md defect #8 (inverted precedence)
and the DIAGNOSTIC-severity exclusion from section 4.2.
"""
from lmd.engine.models import RuleResult, RuleStatus, Severity, Verdict
from lmd.engine.verdict import aggregate


def _result(rule_id: str, severity: Severity, status: RuleStatus) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        category="TEST",
        severity=severity,
        status=status,
        on_fail_code=None,
        message="",
        legal_basis="",
    )


def test_all_pass_is_compliant():
    results = {"R1": _result("R1", Severity.BLOCKER, RuleStatus.PASS)}
    assert aggregate(results) == Verdict.COMPLIANT


def test_all_not_applicable_is_compliant():
    results = {"R1": _result("R1", Severity.BLOCKER, RuleStatus.NOT_APPLICABLE)}
    assert aggregate(results) == Verdict.COMPLIANT


def test_review_alongside_pass_is_needs_review():
    results = {
        "R1": _result("R1", Severity.BLOCKER, RuleStatus.PASS),
        "R2": _result("R2", Severity.MAJOR, RuleStatus.REVIEW),
    }
    assert aggregate(results) == Verdict.NEEDS_REVIEW


def test_blocker_fail_outranks_review():
    """CLAUDE.md defect #8: a single low-confidence REVIEW must never mask
    a definite BLOCKER failure by outranking it."""
    results = {
        "R1": _result("R1", Severity.BLOCKER, RuleStatus.FAIL),
        "R2": _result("R2", Severity.MAJOR, RuleStatus.REVIEW),
    }
    assert aggregate(results) == Verdict.NON_COMPLIANT


def test_minor_fail_also_non_compliant():
    results = {"R1": _result("R1", Severity.MINOR, RuleStatus.FAIL)}
    assert aggregate(results) == Verdict.NON_COMPLIANT


def test_diagnostic_fail_can_never_cause_non_compliant():
    """CLAUDE.md section 4.2: LM-M03 (MRP paise rounding) is DIAGNOSTIC and
    structurally incapable of producing a non-compliant verdict."""
    results = {"LM-M03": _result("LM-M03", Severity.DIAGNOSTIC, RuleStatus.FAIL)}
    assert aggregate(results) == Verdict.COMPLIANT


def test_diagnostic_fail_does_not_even_force_review():
    results = {"LM-M03": _result("LM-M03", Severity.DIAGNOSTIC, RuleStatus.FAIL)}
    assert aggregate(results) != Verdict.NEEDS_REVIEW
