"""Ink-height measurement via row-wise projection profile, NOT OCR bounding-box
height. CLAUDE.md section 6: "FontMetrics.ink_h_px comes from a row-wise
projection profile inside the box... not the OCR bounding-box height, which
includes leading and ascender/descender padding." Research doc §5 step 2:
binarize locally, take the vertical extent of actual ink pixels between the
first and last row whose dark-pixel density exceeds a threshold.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

_DENSITY_THRESHOLD = 0.02  # a row counts as "ink" if >=2% of its pixels are dark


@dataclass
class FontMetrics:
    box_h_px: int
    ink_h_px: int | None
    height_mm: float | None
    measurable: bool
    reason: str | None = None


def _crop_polygon(image: np.ndarray, polygon: np.ndarray) -> np.ndarray:
    x, y, w, h = cv2.boundingRect(polygon.astype(np.int32))
    x, y = max(x, 0), max(y, 0)
    return image[y : y + h, x : x + w]


def measure_ink_height(image: np.ndarray, polygon: np.ndarray, px_per_mm: float | None) -> FontMetrics:
    """polygon: Nx2 array of the OCR detector's box for one text line.

    px_per_mm is None whenever no calibration card was found in frame
    (invariant 9) -- height_mm is then always None, but ink_h_px (a relative
    pixel measurement) is still computed and remains valid for ratio
    comparisons between text lines in the same image.
    """
    crop = _crop_polygon(image, polygon)
    box_h_px = crop.shape[0]
    if crop.size == 0 or box_h_px == 0:
        return FontMetrics(box_h_px=0, ink_h_px=None, height_mm=None, measurable=False, reason="empty_crop")

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    row_density = binary.astype(np.float32).mean(axis=1) / 255.0
    ink_rows = np.where(row_density >= _DENSITY_THRESHOLD)[0]

    if ink_rows.size == 0:
        return FontMetrics(
            box_h_px=box_h_px, ink_h_px=None, height_mm=None, measurable=False, reason="no_ink_pixels_detected"
        )

    ink_h_px = int(ink_rows[-1] - ink_rows[0] + 1)

    if px_per_mm is None:
        return FontMetrics(
            box_h_px=box_h_px,
            ink_h_px=ink_h_px,
            height_mm=None,
            measurable=False,
            reason="no_calibration_reference_in_frame",
        )

    return FontMetrics(
        box_h_px=box_h_px,
        ink_h_px=ink_h_px,
        height_mm=ink_h_px / px_per_mm,
        measurable=True,
        reason=None,
    )
