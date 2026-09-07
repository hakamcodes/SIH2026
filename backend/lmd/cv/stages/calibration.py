"""ID-1 calibration card detection (CLAUDE.md section 2 and invariant 9).

An ISO/ID-1 card (85.60 mm x 53.98 mm, aspect ratio 85.60/53.98 = 1.586) is
detected by contour aspect ratio using base OpenCV -- no ArUco, no ML model,
no opencv-contrib. If no card-shaped contour is found, calibration MUST be
reported as absent rather than guessed (invariant 9: "Never guess a physical
scale... emit height_mm: null, measurable: false").
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

ID1_ASPECT_RATIO = 85.60 / 53.98  # 1.586
_ASPECT_TOLERANCE = 0.12
_MIN_AREA_FRACTION = 0.01  # card must occupy at least 1% of the frame to be a plausible in-frame ID card


@dataclass
class CalibrationResult:
    px_per_mm: float
    card_width_px: float
    card_height_px: float
    bounding_box: tuple[int, int, int, int]


def detect_calibration_card(image: np.ndarray) -> CalibrationResult | None:
    """Return px_per_mm if an ID-1-shaped quadrilateral is found, else None.

    Never raises; an image with no card-shaped contour, or with multiple
    ambiguous candidates, resolves to None (no calibration reference in frame).
    """
    if image is None or image.size == 0:
        return None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    frame_area = image.shape[0] * image.shape[1]

    best: CalibrationResult | None = None
    best_area = 0.0

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < _MIN_AREA_FRACTION * frame_area:
            continue

        rect = cv2.minAreaRect(contour)
        (_, _), (w, h), _ = rect
        if w == 0 or h == 0:
            continue

        long_side, short_side = max(w, h), min(w, h)
        ratio = long_side / short_side
        if abs(ratio - ID1_ASPECT_RATIO) > _ASPECT_TOLERANCE:
            continue

        # Reject overly non-rectangular contours (a card's contour area should
        # closely fill its minAreaRect; loose fits are usually clutter/text blobs).
        rect_area = w * h
        if rect_area == 0 or area / rect_area < 0.75:
            continue

        if area > best_area:
            best_area = area
            x, y, bw, bh = cv2.boundingRect(contour)
            best = CalibrationResult(
                px_per_mm=long_side / 85.60,
                card_width_px=long_side,
                card_height_px=short_side,
                bounding_box=(x, y, bw, bh),
            )

    return best
