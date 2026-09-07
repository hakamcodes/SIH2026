"""Annotated overlay: draw pipeline A's detected text boxes on the source
image, color-coded by OCR confidence, plus a verdict banner. This is the
image the frontend's AnnotatedCanvas renders and that gets stored as
EvidenceType.ANNOTATED_OVERLAY.

Boxes are colored by extraction confidence, not by rule pass/fail -- this
module has no reliable box-to-rule mapping (that would require a
field-to-polygon association pipeline_a/reconcile do not build), so it never
claims a box is "the reason rule X failed." Overclaiming that link would be
exactly the kind of fabricated precision CLAUDE.md prohibits.
"""
from __future__ import annotations

import cv2
import numpy as np

from .pipeline_a import PipelineAResult

_HIGH_CONF_COLOR = (30, 160, 30)  # green, BGR
_MED_CONF_COLOR = (0, 165, 255)  # orange, BGR
_LOW_CONF_COLOR = (30, 30, 200)  # red, BGR

_HIGH_CONF_THRESHOLD = 0.90
_MED_CONF_THRESHOLD = 0.70


def _color_for_confidence(confidence: float) -> tuple[int, int, int]:
    if confidence >= _HIGH_CONF_THRESHOLD:
        return _HIGH_CONF_COLOR
    if confidence >= _MED_CONF_THRESHOLD:
        return _MED_CONF_COLOR
    return _LOW_CONF_COLOR


def render_overlay(image: np.ndarray, result: PipelineAResult, verdict: str) -> np.ndarray:
    """Return a new BGR image with detection boxes and a verdict banner drawn.
    Never mutates the input image."""
    annotated = image.copy()

    for f in result.fields:
        polygon = np.asarray(f.polygon, dtype=np.int32)
        color = _color_for_confidence(f.confidence)
        cv2.polylines(annotated, [polygon], isClosed=True, color=color, thickness=2)

    if result.calibration is not None:
        x, y, w, h = result.calibration.bounding_box
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv2.putText(
            annotated, "calibration card", (x, max(y - 8, 0)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2,
        )

    banner_height = 40
    banner = np.full((banner_height, annotated.shape[1], 3), 255, dtype=np.uint8)
    banner_color = {
        "COMPLIANT": _HIGH_CONF_COLOR,
        "NON_COMPLIANT": _LOW_CONF_COLOR,
        "NEEDS_REVIEW": _MED_CONF_COLOR,
    }.get(verdict, (0, 0, 0))
    cv2.putText(
        banner, f"VERDICT: {verdict} (advisory pre-screening only)", (10, 27),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, banner_color, 2,
    )
    return np.vstack([banner, annotated])


def encode_png(image: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("failed to encode overlay image as PNG")
    return buf.tobytes()
