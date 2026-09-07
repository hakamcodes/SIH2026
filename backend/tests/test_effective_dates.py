"""Point-in-time law evaluation. Per CLAUDE.md: 'the system performs point-in-time
legal evaluation -- it can state which version of the law it applied to a given
scan date.' Proves per-rule effective_from/effective_to filtering actually works.
"""
from pathlib import Path

import pytest
from lmd.engine.engine import RuleEngine
from lmd.engine.loader import load_rules
from lmd.engine.models import RuleStatus, Verdict

RULES_PATH = Path(__file__).resolve().parents[2] / "packages" / "rules" / "lmd_rules.v1.json"


@pytest.fixture(scope="module")
def engine():
    return RuleEngine(load_rules(RULES_PATH))


def _base_product():
    return {
        "scan_source": "package_image",
        "commodity": {"category": "food", "subtype": "biscuits", "is_imported": False, "is_exempt": False},
        "net_quantity": {"value": 500.0, "unit": "g"},
        "mrp": {"value": 100.0, "currency_marker": "₹", "raw_text": "MRP Rs. 100.00 incl. of all taxes"},
        "mfg_date": "2017-01-01",
        "best_before_date": "2017-12-01",
        "manufacturer_or_packer_or_importer": {"name": "Acme Foods", "address": "Pune, MH"},
        "common_or_generic_name": "Glucose Biscuits",
        "brand_name": "Acme Gold",
        "consumer_care": {"phone": "+919876543210"},
    }


def test_pre_2011_scan_is_rejected_by_ruleset_meta_rule(engine):
    result = engine.evaluate(_base_product(), scan_date="2010-05-15")
    assert result.rule_results["LM-T01"].status == RuleStatus.FAIL
    assert result.overall_verdict == Verdict.NON_COMPLIANT


def test_best_before_rule_not_in_force_before_2018(engine):
    """LM-C08 (Rule 6(1)(da), effective 2018-01-01) must not apply to a 2017 scan --
    a missing best_before_date on that date was not yet a violation."""
    product = _base_product()
    del product["best_before_date"]
    result = engine.evaluate(product, scan_date="2017-06-01")
    assert result.rule_results["LM-C08"].status == RuleStatus.NOT_IN_FORCE


def test_best_before_rule_in_force_after_2018(engine):
    product = _base_product()
    del product["best_before_date"]
    product["mfg_date"] = "2026-01-01"
    result = engine.evaluate(product, scan_date="2026-06-01")
    assert result.rule_results["LM-C08"].status == RuleStatus.FAIL


def test_usp_rule_not_in_force_before_2022(engine):
    """LM-M01 (Rule 6(11) USP, effective 2022-04-01) must not apply pre-2022."""
    product = _base_product()
    product["usp_declared"] = 999.0  # would mismatch if evaluated
    result = engine.evaluate(product, scan_date="2020-01-01")
    assert result.rule_results["LM-M01"].status == RuleStatus.NOT_IN_FORCE


def test_second_schedule_rule5_blocker_in_force_from_2012_07_01(engine):
    """LM-M04a (Rule 5 non-standard-size blocker) must not apply before 2012-07-01,
    even though the base Act was already in force."""
    product = {
        "scan_source": "package_image",
        "commodity": {"category": "food", "subtype": "biscuits", "is_imported": False, "is_exempt": False},
        "net_quantity": {"value": 120.0, "unit": "g"},
        "mrp": {"value": 30.0, "currency_marker": "₹"},
    }
    result = engine.evaluate(product, scan_date="2012-01-01")
    assert result.rule_results["LM-M04a"].status == RuleStatus.NOT_IN_FORCE
    result2 = engine.evaluate(product, scan_date="2013-01-01")
    assert result2.rule_results["LM-M04a"].status == RuleStatus.FAIL
