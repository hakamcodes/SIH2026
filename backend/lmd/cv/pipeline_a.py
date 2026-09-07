"""Pipeline A: deterministic OCR via RapidOCR (CLAUDE.md section 2 -- pure
Python wheel, bundled ONNX models, fully offline, chosen over paddleocr and
over rapidocr-onnxruntime which hard-fails on Python 3.13).

Per CLAUDE.md invariant 11 ("no global image preprocessing"): OCR runs on the
raw image first. Glare masking (invariant 11's sole exception) is applied
before detection. For any box below `_LOW_CONFIDENCE_THRESHOLD`, the same
region is re-OCR'd after local CLAHE + adaptive threshold enhancement, and
the result with the higher confidence wins (`max(raw, enhanced)` per box) --
never a blanket re-run over the whole frame.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import cv2
import numpy as np
from rapidocr import RapidOCR

from .stages.calibration import CalibrationResult, detect_calibration_card
from .stages.font_metrics import FontMetrics, measure_ink_height
from .stages.glare import apply_glare_mask

_LOW_CONFIDENCE_THRESHOLD = 0.80


@dataclass
class TextField:
    text: str
    confidence: float
    polygon: list[list[float]]
    font_metrics: FontMetrics
    enhanced: bool = False


@dataclass
class PipelineAResult:
    fields: list[TextField] = field(default_factory=list)
    calibration: CalibrationResult | None = None

    @property
    def full_text(self) -> str:
        return " ".join(f.text for f in self.fields)


@lru_cache(maxsize=1)
def _get_engine() -> RapidOCR:
    return RapidOCR()


def _enhance_roi(gray_crop: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray_crop)
    enhanced = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def _rerun_ocr_on_crop(crop_bgr: np.ndarray) -> tuple[str, float] | None:
    engine = _get_engine()
    result = engine(crop_bgr)
    if result is None or not result.txts:
        return None
    # A re-OCR'd single-line crop should yield one dominant line; join if the
    # detector still split it, use the mean confidence across the fragments.
    text = " ".join(result.txts)
    conf = float(np.mean(result.scores)) if result.scores else 0.0
    return text, conf


def run_pipeline_a(image: np.ndarray) -> PipelineAResult:
    """image: BGR ndarray (e.g. from cv2.imread). Never raises on ordinary
    low-quality input -- a field that cannot be read is simply absent from
    `fields`, per the extraction contract's "absence, never invented" rule.
    """
    calibration = detect_calibration_card(image)
    px_per_mm = calibration.px_per_mm if calibration else None

    masked = apply_glare_mask(image)
    engine = _get_engine()
    raw_result = engine(masked)

    fields: list[TextField] = []
    if raw_result is None or not raw_result.txts:
        return PipelineAResult(fields=[], calibration=calibration)

    for polygon, text, score in zip(raw_result.boxes, raw_result.txts, raw_result.scores):
        best_text, best_score, was_enhanced = text, float(score), False

        if best_score < _LOW_CONFIDENCE_THRESHOLD:
            x, y, w, h = cv2.boundingRect(np.asarray(polygon, dtype=np.int32))
            x, y = max(x, 0), max(y, 0)
            crop = image[y : y + h, x : x + w]
            if crop.size > 0:
                gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
                enhanced_crop = _enhance_roi(gray_crop)
                rerun = _rerun_ocr_on_crop(enhanced_crop)
                if rerun is not None and rerun[1] > best_score:
                    best_text, best_score, was_enhanced = rerun[0], rerun[1], True

        metrics = measure_ink_height(image, np.asarray(polygon), px_per_mm)
        fields.append(
            TextField(
                text=best_text,
                confidence=best_score,
                polygon=np.asarray(polygon).tolist(),
                font_metrics=metrics,
                enhanced=was_enhanced,
            )
        )

    return PipelineAResult(fields=fields, calibration=calibration)
