import numpy as np

from lmd.cv.overlay import encode_png, render_overlay
from lmd.cv.pipeline_a import PipelineAResult, TextField
from lmd.cv.stages.font_metrics import FontMetrics

_METRICS = FontMetrics(box_h_px=10, ink_h_px=6, height_mm=None, measurable=False, reason="no_calibration_reference_in_frame")


def test_render_overlay_does_not_mutate_input():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    original = image.copy()
    result = PipelineAResult(
        fields=[TextField(text="x", confidence=0.95, polygon=[[0, 0], [10, 0], [10, 10], [0, 10]], font_metrics=_METRICS)]
    )
    render_overlay(image, result, "COMPLIANT")
    assert np.array_equal(image, original)


def test_render_overlay_adds_banner_row_and_stays_encodable():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    result = PipelineAResult(fields=[])
    annotated = render_overlay(image, result, "NEEDS_REVIEW")
    assert annotated.shape[0] == 100 + 40
    assert annotated.shape[1] == 100
    png_bytes = encode_png(annotated)
    assert png_bytes.startswith(b"\x89PNG")
