"""Golden-image expectations for the full scan pipeline (pipeline A + reconcile
+ rule engine) against the seven real research photographs, per CLAUDE.md
section 8: "encode measured reality, including known failures... must assert
they never return COMPLIANT."

Known, honestly-documented limitation: lmd.cv.stages.structuring does not yet
parse manufacturer_or_packer_or_importer (name/address) or
common_or_generic_name out of raw OCR text -- there is no reliable lexical
marker for "this line is the manufacturer address" the way there is for
"MRP"/"Net Wt."/"MFD". Because those are structural COMPLETENESS BLOCKER
fields (LM-C03, LM-C07), every real photo in this repository currently
evaluates to NON_COMPLIANT via a genuinely-missing mandatory declaration,
regardless of whether pipeline A read the rest of the label well. This is
measured reality, not a bug being papered over: CLAUDE.md invariant 5
("structural absence beats confidence") means an unparsed mandatory field
must fail, not silently pass. What we assert here is the one invariant that
actually matters for a pre-screening tool: none of these ever comes back
COMPLIANT when they demonstrably have unread/unverifiable declarations.
"""
from pathlib import Path

import cv2
import pytest

from lmd import config
from lmd.cv.pipeline_a import run_pipeline_a
from lmd.cv.reconcile import reconcile
from lmd.engine.engine import RuleEngine
from lmd.engine.loader import load_rules
from lmd.engine.models import Verdict

_IMG_DIR = Path(__file__).resolve().parents[2] / "research" / "mainResearch"

pytestmark = pytest.mark.slow

# Plausible commodity classification an inspector would select at capture
# time -- CV commodity classification is not a pipeline stage this build
# implements (CLAUDE.md's 8-stage CV pipeline has no "classify commodity"
# step), so this models the realistic inspector-assisted workflow.
_COMMODITY_BY_IMAGE = {
    "01_curved_pouch_dense_text.jpg": {"category": "food", "subtype": "snack", "is_imported": False, "is_exempt": False},
    "02_flat_box_clean.jpg": {"category": "personal_care", "subtype": "toothpaste", "is_imported": False, "is_exempt": False},
    "04_rotated_blurry_dotmatrix.jpg": {"category": "food", "subtype": "packaged_food", "is_imported": False, "is_exempt": False},
    "06_curved_jar.jpg": {"category": "food", "subtype": "jar_food", "is_imported": False, "is_exempt": False},
}


@pytest.fixture(scope="module")
def engine():
    return RuleEngine(load_rules(config.RULES_PATH))


def _evaluate(name: str, engine: RuleEngine):
    image = cv2.imread(str(_IMG_DIR / name))
    assert image is not None, f"missing golden image: {name}"
    pipeline_a_result = run_pipeline_a(image)
    envelope = reconcile(pipeline_a_result, vision_fields={}, scan_source="package_image")
    envelope["commodity"] = _COMMODITY_BY_IMAGE[name]
    return engine.evaluate(envelope, scan_date="2026-09-06")


@pytest.mark.parametrize("name", sorted(_COMMODITY_BY_IMAGE))
def test_no_real_photo_ever_comes_back_compliant(name, engine):
    result = _evaluate(name, engine)
    assert result.overall_verdict != Verdict.COMPLIANT, (
        f"{name} evaluated COMPLIANT -- a real, imperfectly-photographed package "
        "must never pass with zero human review; this is the one failure mode "
        "an inspector-facing pre-screening tool cannot tolerate."
    )


def test_dot_matrix_and_curved_jar_never_compliant_even_under_disagreement():
    # These two are CLAUDE.md's explicitly named zero-recovery cases. Assert
    # the specific images by name so a future change that starts silently
    # trusting fabricated dot-matrix/curved-surface reads is caught here.
    engine = RuleEngine(load_rules(config.RULES_PATH))
    for name in ["04_rotated_blurry_dotmatrix.jpg", "06_curved_jar.jpg"]:
        result = _evaluate(name, engine)
        assert result.overall_verdict != Verdict.COMPLIANT
