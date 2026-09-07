"""Every fixture's input_data must validate against ExtractionEnvelope, and
running the engine against ExtractionEnvelope.model_dump() must produce the
identical verdict as running it against the raw fixture dict -- proving the
contract really is the same dotted-path keyspace the rule engine already
speaks (CLAUDE.md section 6), not a parallel shape that needs translation.
"""
from pathlib import Path

import pytest
from lmd.engine.engine import RuleEngine
from lmd.engine.loader import load_rules
from lmd.extraction.adapters.legacy_names import from_legacy
from lmd.extraction.contract import ExtractionEnvelope, flatten

from .fixtures.compliance_test_cases import DEFAULT_SCAN_DATE, TEST_CASES

RULES_PATH = Path(__file__).resolve().parents[2] / "packages" / "rules" / "lmd_rules.v1.json"


@pytest.fixture(scope="module")
def engine():
    return RuleEngine(load_rules(RULES_PATH))


@pytest.mark.parametrize("case", TEST_CASES, ids=[c["test_case_id"] for c in TEST_CASES])
def test_fixture_validates_against_contract_and_reproduces_verdict(engine, case):
    envelope = ExtractionEnvelope.model_validate(case["input_data"])
    dumped = envelope.model_dump(exclude_none=True, exclude={"schema_version"})

    scan_date = case.get("scan_date", DEFAULT_SCAN_DATE)
    raw_result = engine.evaluate(case["input_data"], scan_date=scan_date)
    envelope_result = engine.evaluate(dumped, scan_date=scan_date)

    assert envelope_result.overall_verdict == raw_result.overall_verdict


def test_flatten_produces_dotted_paths():
    envelope = ExtractionEnvelope.model_validate(
        {
            "scan_source": "package_image",
            "net_quantity": {"value": 500.0, "unit": "g"},
            "mrp": {"value": 100.0},
        }
    )
    entries = flatten(envelope)
    paths = {e["field_name"]: e["value"] for e in entries}
    assert paths["scan_source"] == "package_image"
    assert paths["net_quantity.value"] == 500.0
    assert paths["net_quantity.unit"] == "g"
    assert paths["mrp.value"] == 100.0
    assert "mrp.currency_marker" not in paths  # None fields are omitted, never invented


def test_legacy_adapter_maps_known_fields_only():
    legacy = {
        "image_analysis_parameters": {
            "product_category": "food",
            "commodity_subtype": "biscuits",
            "is_imported": False,
            "net_quantity": {"declared_value": 200.0, "declared_unit": "g"},
            "mrp_price": {"value": 50.0, "currency": "₹", "format_compliant": True},
            "packing_date": {"month": 8, "year": 2026, "raw_text_detected": True},
            "special_declarations": {
                "best_before_present": True,
                "country_of_origin": "India",
                "dimensions_declared": False,
            },
        }
    }
    canonical = from_legacy(legacy)
    assert canonical["commodity"]["category"] == "food"
    assert canonical["net_quantity"]["value"] == 200.0
    assert canonical["mrp"]["value"] == 50.0
    assert canonical["mfg_or_pack_or_import_month_year"] == "2026-08"
    assert canonical["country_of_origin"] == "India"
    # boolean-only presence flags must never be turned into fabricated values
    assert "best_before_date" not in canonical
    assert "dimensions" not in canonical

    # Result must validate against the canonical contract.
    ExtractionEnvelope.model_validate(canonical)
