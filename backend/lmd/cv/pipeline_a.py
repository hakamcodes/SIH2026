"""Pipeline A: deterministic OCR via RapidOCR (CLAUDE.md section 2 -- pure
Python wheel, bundled ONNX models, fully offline, chosen over paddleocr and
over rapidocr-onnxruntime which hard-fails on Python 3.13).

Per CLAUDE.md invariant 11 ("no global image preprocessing"): OCR runs on the
raw image first. Glare masking (invariant 11's sole exception) is applied
before detection. For any box below `_LOW_CONFIDENCE_THRESHOLD`, the same
region is re-OCR'd after local CLAHE + adaptive threshold enhancement, and
the result with the higher confidence wins (`max(raw, enhanced)` per box) --
never a blanket re-run over the whole frame.

Detection/recognition and calibration-card contour search run against a
resolution-capped working frame (see `_prepare_working_frame`): this is a
capture-resolution choice, not the pixel *enhancement* invariant 11 forbids
-- a raw phone photo (e.g. 4000x3000) fed uncapped into CPU-only ONNX
inference (no GPU per CLAUDE.md section 2) scales cost with resolution for
no accuracy benefit past a few thousand pixels on the long side. Every box
polygon and calibration measurement is rescaled back to the *original*
image's pixel space before being returned, so the per-ROI enhancement crop,
`measure_ink_height`, `render_overlay`, and the frontend's AnnotatedCanvas
(which all index into the original full-resolution image/bytes) see
coordinates in the same space they always did. When the source image is
already at or under the cap, scale is 1.0 and nothing changes.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from functools import lru_cache

import cv2
import numpy as np
from rapidocr import RapidOCR

from .stages.calibration import CalibrationResult, detect_calibration_card
from .stages.font_metrics import FontMetrics, measure_ink_height
from .stages.glare import apply_glare_mask

_LOW_CONFIDENCE_THRESHOLD = 0.80
# Longest-side cap (px) for detection/recognition and calibration search.
# Chosen well above what any Rule 7 font-height measurement needs (those
# operate on small per-box crops taken from the original-resolution image,
# never from this capped frame) and well below typical 8-12MP phone photos.
_MAX_DETECTION_DIM = 1800

logger = logging.getLogger(__name__)

# RapidOCR's ONNX session is shared via `_get_engine`'s lru_cache; guard
# concurrent calls (e.g. two scans processed in overlapping worker threads)
# since nothing in this module has verified the session is thread-safe.
_ENGINE_LOCK = threading.Lock()


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
    # Caps onnxruntime's intra/inter-op thread pools, shared across the det/
    # cls/rec sessions via EngineConfig.onnxruntime. Left at the library
    # default (-1 = one thread per CPU core), a multi-core Render box lets
    # each session spin up its own per-core native thread pool, which is
    # what pushed a single-request scan over the 512MB instance cap.
    return RapidOCR(
        params={
            "EngineConfig.onnxruntime.intra_op_num_threads": 1,
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
        }
    )


def _enhance_roi(gray_crop: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray_crop)
    enhanced = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def _rerun_ocr_on_crop(crop_bgr: np.ndarray) -> tuple[str, float] | None:
    # The crop is already a tight single-line box (cv2.boundingRect of a box
    # pipeline A's own detector already found) -- re-running detection and
    # the angle classifier on it is pure overhead. use_det=False/use_cls=False
    # sends the whole crop straight to recognition, which is the documented
    # RapidOCR pattern for a pre-cropped line and is the dominant cost this
    # skips (measured: this loop was the single largest contributor to
    # multi-minute scans on dense-text images).
    engine = _get_engine()
    with _ENGINE_LOCK:
        result = engine(crop_bgr, use_det=False, use_cls=False, use_rec=True)
    if result is None or not result.txts:
        return None
    # A re-OCR'd single-line crop should yield one dominant line; join if the
    # detector still split it, use the mean confidence across the fragments.
    text = " ".join(result.txts)
    conf = float(np.mean(result.scores)) if result.scores else 0.0
    return text, conf


def _prepare_working_frame(image: np.ndarray) -> tuple[np.ndarray, float]:
    """Return (frame, scale) where frame is `image` downscaled so its longest
    side is at most `_MAX_DETECTION_DIM`, and scale is frame_dim/original_dim
    (<=1.0). scale is 1.0 (frame is `image` itself, no copy) when the image
    is already within the cap."""
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest <= _MAX_DETECTION_DIM:
        return image, 1.0
    scale = _MAX_DETECTION_DIM / longest
    small = cv2.resize(image, (int(round(w * scale)), int(round(h * scale))), interpolation=cv2.INTER_AREA)
    return small, scale


def _rescale_calibration(calibration: CalibrationResult, inv_scale: float) -> CalibrationResult:
    x, y, bw, bh = calibration.bounding_box
    return CalibrationResult(
        px_per_mm=calibration.px_per_mm * inv_scale,
        card_width_px=calibration.card_width_px * inv_scale,
        card_height_px=calibration.card_height_px * inv_scale,
        bounding_box=(
            int(round(x * inv_scale)),
            int(round(y * inv_scale)),
            int(round(bw * inv_scale)),
            int(round(bh * inv_scale)),
        ),
    )


def run_pipeline_a(image: np.ndarray) -> PipelineAResult:
    """image: BGR ndarray (e.g. from cv2.imread). Never raises on ordinary
    low-quality input -- a field that cannot be read is simply absent from
    `fields`, per the extraction contract's "absence, never invented" rule.
    """
    t_start = time.perf_counter()
    working, scale = _prepare_working_frame(image)
    inv_scale = 1.0 / scale

    t0 = time.perf_counter()
    calibration = detect_calibration_card(working)
    if calibration is not None and scale != 1.0:
        calibration = _rescale_calibration(calibration, inv_scale)
    px_per_mm = calibration.px_per_mm if calibration else None
    t_calibration = time.perf_counter() - t0

    t0 = time.perf_counter()
    masked = apply_glare_mask(working)
    t_glare = time.perf_counter() - t0

    t0 = time.perf_counter()
    engine = _get_engine()
    with _ENGINE_LOCK:
        # RapidOCR's use_det/use_cls/use_rec are mutable state on the shared
        # engine instance (update_params only overwrites a kwarg when it is
        # not None), not per-call flags -- a prior _rerun_ocr_on_crop() call
        # (which deliberately sets use_det=False) would otherwise leak into
        # this full detect+recognize call. Always pass all three explicitly.
        raw_result = engine(masked, use_det=True, use_cls=True, use_rec=True)
    t_ocr = time.perf_counter() - t0

    fields: list[TextField] = []
    if raw_result is None or not raw_result.txts:
        logger.info(
            "pipeline_a: scale=%.3f calibration=%.2fs glare=%.2fs ocr=%.2fs roi_retries=0 total=%.2fs (no boxes)",
            scale, t_calibration, t_glare, t_ocr, time.perf_counter() - t_start,
        )
        return PipelineAResult(fields=[], calibration=calibration)

    t_roi_total = 0.0
    roi_retry_count = 0
    for polygon, text, score in zip(raw_result.boxes, raw_result.txts, raw_result.scores):
        # Boxes/scores come back in the (possibly downscaled) working
        # frame's coordinate space; rescale to the original image's pixel
        # space before any code below, which indexes into `image` directly.
        polygon_original = (np.asarray(polygon, dtype=np.float64) * inv_scale) if scale != 1.0 else np.asarray(polygon)
        best_text, best_score, was_enhanced = text, float(score), False

        if best_score < _LOW_CONFIDENCE_THRESHOLD:
            t_roi = time.perf_counter()
            roi_retry_count += 1
            x, y, w, h = cv2.boundingRect(polygon_original.astype(np.int32))
            x, y = max(x, 0), max(y, 0)
            crop = image[y : y + h, x : x + w]
            if crop.size > 0:
                gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
                enhanced_crop = _enhance_roi(gray_crop)
                rerun = _rerun_ocr_on_crop(enhanced_crop)
                if rerun is not None and rerun[1] > best_score:
                    best_text, best_score, was_enhanced = rerun[0], rerun[1], True
            t_roi_total += time.perf_counter() - t_roi

        metrics = measure_ink_height(image, polygon_original, px_per_mm)
        fields.append(
            TextField(
                text=best_text,
                confidence=best_score,
                polygon=polygon_original.tolist(),
                font_metrics=metrics,
                enhanced=was_enhanced,
            )
        )

    logger.info(
        "pipeline_a: scale=%.3f calibration=%.2fs glare=%.2fs ocr=%.2fs roi_retries=%d(%.2fs) total=%.2fs",
        scale, t_calibration, t_glare, t_ocr, roi_retry_count, t_roi_total, time.perf_counter() - t_start,
    )
    return PipelineAResult(fields=fields, calibration=calibration)
