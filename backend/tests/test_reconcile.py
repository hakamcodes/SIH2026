from lmd.cv.pipeline_a import PipelineAResult, TextField
from lmd.cv.reconcile import VISION_ONLY_CONFIDENCE, reconcile
from lmd.cv.stages.font_metrics import FontMetrics

_NO_METRICS = FontMetrics(box_h_px=20, ink_h_px=14, height_mm=None, measurable=False, reason="no_calibration_reference_in_frame")


def _field(text: str, confidence: float) -> TextField:
    return TextField(text=text, confidence=confidence, polygon=[[0, 0], [1, 0], [1, 1], [0, 1]], font_metrics=_NO_METRICS)


def test_reconcile_populates_net_quantity_and_mrp_from_ocr_only():
    result = PipelineAResult(fields=[_field("Net Wt. 200 g", 0.95), _field("MRP Rs. 150", 0.9)])
    envelope = reconcile(result, vision_fields={})
    assert envelope["net_quantity"] == {"value": 200.0, "unit": "g"}
    assert envelope["mrp"]["value"] == 150.0
    # vision never contributed -- no ocr_pipeline/llm_pipeline pair recorded
    assert "ocr_pipeline" not in envelope


def test_reconcile_surfaces_a_vision_only_numeric_value_at_capped_confidence():
    # Pipeline A found nothing at all (e.g. a split-line MRP/quantity RapidOCR
    # never joined) -- the value must still be surfaced, never silently
    # dropped, but capped below every BLOCKER rule's min_field_confidence so
    # LM-U01's Trust Gate can never let it alone reach COMPLIANT.
    result = PipelineAResult(fields=[])
    envelope = reconcile(result, vision_fields={"net_quantity": {"value": 250.0, "unit": "g"}})
    assert envelope["net_quantity"] == {"value": 250.0, "unit": "g"}
    assert envelope["field_confidences"]["net_quantity"] == VISION_ONLY_CONFIDENCE
    # no OCR reading exists, so this must not be mistaken for a dual-pipeline
    # agreement signal
    assert "ocr_pipeline" not in envelope


def test_reconcile_fills_country_of_origin_gap_from_vision_at_capped_confidence():
    result = PipelineAResult(fields=[_field("some unrelated ocr line", 0.99)])
    envelope = reconcile(result, vision_fields={"country_of_origin": "China"})
    assert envelope["country_of_origin"] == "China"
    assert envelope["field_confidences"]["country_of_origin"] == VISION_ONLY_CONFIDENCE


def test_reconcile_populates_dual_pipeline_signal_when_both_agree_on_mrp():
    result = PipelineAResult(fields=[_field("MRP Rs. 150", 0.9)])
    envelope = reconcile(result, vision_fields={"mrp": {"value": 150.0}})
    assert envelope["ocr_pipeline"]["numeric_val"] == 150.0
    assert envelope["llm_pipeline"]["numeric_val"] == 150.0


def test_reconcile_populates_dual_pipeline_signal_on_disagreement_too():
    result = PipelineAResult(fields=[_field("MRP Rs. 150", 0.9)])
    envelope = reconcile(result, vision_fields={"mrp": {"value": 190.0}})
    assert envelope["ocr_pipeline"]["numeric_val"] == 150.0
    assert envelope["llm_pipeline"]["numeric_val"] == 190.0
    # the accepted mrp.value itself is still the OCR reading, not vision's
    assert envelope["mrp"]["value"] == 150.0


def test_reconcile_attaches_ocr_confidence_to_structured_field():
    result = PipelineAResult(fields=[_field("Net Wt. 200 g", 0.42)])
    envelope = reconcile(result, vision_fields={})
    assert envelope["field_confidences"]["net_quantity"] == 0.42
