"""packages/rules/schema/*.json must actually validate the real artifacts they
document -- a schema that silently drifts from lmd_rules.v1.json or
ExtractionEnvelope is worse than no schema.
"""
import json
from pathlib import Path

import jsonschema
from lmd.extraction.contract import ExtractionEnvelope

from .fixtures.compliance_test_cases import TEST_CASES

_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "packages" / "rules" / "schema"
_RULES_PATH = Path(__file__).resolve().parents[2] / "packages" / "rules" / "lmd_rules.v1.json"


def test_rules_file_validates_against_schema():
    rules = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    schema = json.loads((_SCHEMA_DIR / "rules.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(rules, schema)


def test_v2_draft_rules_file_validates_against_schema_and_loads():
    from lmd.engine.loader import load_rules

    v2_path = _RULES_PATH.parent / "lmd_rules.v2.draft.json"
    rules = json.loads(v2_path.read_text(encoding="utf-8"))
    schema = json.loads((_SCHEMA_DIR / "rules.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(rules, schema)
    assert len(load_rules(v2_path)) == len(rules)


def test_fixture_envelopes_validate_against_extraction_schema():
    schema = json.loads((_SCHEMA_DIR / "extraction.v1.schema.json").read_text(encoding="utf-8"))
    for case in TEST_CASES:
        envelope = ExtractionEnvelope.model_validate(case["input_data"])
        dumped = envelope.model_dump(exclude_none=True, mode="json")
        dumped.setdefault("schema_version", "1.0")
        jsonschema.validate(dumped, schema)
