"""Runs every compliance-test-cases fixture through the real engine and
asserts the actual overall_verdict -- not just expected_triggered_rules
membership (CLAUDE.md section 8: the original harness never did this, and
"18/22 passing" was hiding four self-contradictory fixtures).
"""
from pathlib import Path

import pytest
from lmd.engine.engine import RuleEngine
from lmd.engine.loader import load_rules
from lmd.engine.models import Verdict

from .fixtures.compliance_test_cases import DEFAULT_SCAN_DATE, TEST_CASES

RULES_PATH = Path(__file__).resolve().parents[2] / "packages" / "rules" / "lmd_rules.v1.json"


@pytest.fixture(scope="module")
def engine():
    return RuleEngine(load_rules(RULES_PATH))


@pytest.mark.parametrize("case", TEST_CASES, ids=[c["test_case_id"] for c in TEST_CASES])
def test_fixture_verdict(engine, case):
    scan_date = case.get("scan_date", DEFAULT_SCAN_DATE)
    result = engine.evaluate(case["input_data"], scan_date=scan_date)

    # Full rule_results mapping must be present for every loaded rule --
    # never a silently-dropped subset (CLAUDE.md section 8).
    assert set(result.rule_results.keys()) == {r.rule_id for r in engine.rules}

    actual = result.overall_verdict.value
    expected = case["expected_verdict"]
    assert actual == expected, (
        f"{case['test_case_id']} ({case['scenario_name']}): "
        f"expected {expected}, got {actual}. "
        f"failed={result.failed_rule_ids} review={result.review_rule_ids}"
    )


def test_diagnostic_rule_never_forces_non_compliant(engine):
    """LM-M03 (MRP paise rounding) is DIAGNOSTIC -- structurally incapable of
    producing a non-compliant verdict, per CLAUDE.md 4.2."""
    product = {
        "scan_source": "package_image",
        "commodity": {"category": "hardware", "subtype": "fastener", "is_imported": False, "is_exempt": False},
        "net_quantity": {"value": 200.0, "unit": "g"},
        "mrp": {"value": 48.0, "computed_value": 47.7, "currency_marker": "₹", "raw_text": "MRP Rs. 48.00 incl. of all taxes"},
        "mfg_date": "2026-08-01",
        "manufacturer_or_packer_or_importer": {"name": "Acme Hardware", "address": "Nashik, MH"},
        "common_or_generic_name": "Steel Bolts",
        "brand_name": "Acme Fasteners",
        "consumer_care": {"phone": "+919876543210"},
    }
    result = engine.evaluate(product, scan_date=DEFAULT_SCAN_DATE)
    assert result.rule_results["LM-M03"].status.value == "FAIL"
    assert result.overall_verdict == Verdict.COMPLIANT
