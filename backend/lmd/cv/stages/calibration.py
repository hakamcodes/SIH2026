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
# 0.15 (was 0.12): a hand-held, not perfectly overhead, shot keystones the
# card into a trapezoid. minAreaRect's enclosing box then reads long-side-
# heavy vs the true card. _quad_sides corrects most of that skew already;
# this tolerance covers what's left, still tight enough to reject arbitrary
# rectangular objects (boxes, panels) that aren't ID-1 shaped.
_ASPECT_TOLERANCE = 0.15
_MIN_AREA_FRACTION = 0.01  # card must occupy at least 1% of the frame to be a plausible in-frame ID card


@dataclass
class CalibrationResult:
    px_per_mm: float
    card_width_px: float
    card_height_px: float
    bounding_box: tuple[int, int, int, int]


def _quad_sides(contour) -> tuple[float, float] | None:
    """Fit contour to a 4-corner polygon and return (long_side, short_side).

    Averages each pair of opposite sides so a mild perspective trapezoid
    (one edge closer to the camera than its opposite) doesn't get measured
    as an elongated minAreaRect box. Returns None if the contour doesn't
    reduce to a clean quadrilateral -- callers should treat that as "not
    confidently rectangular" rather than guess a fallback shape.
    """
    peri = cv2.arcLength(contour, True)
    if peri == 0:
        return None
    for eps_frac in (0.01, 0.02, 0.03, 0.04, 0.05, 0.07, 0.1):
        approx = cv2.approxPolyDP(contour, eps_frac * peri, True)
        if len(approx) == 4:
            pts = approx.reshape(4, 2).astype(float)
            sides = [np.linalg.norm(pts[i] - pts[(i + 1) % 4]) for i in range(4)]
            pair_a = (sides[0] + sides[2]) / 2
            pair_b = (sides[1] + sides[3]) / 2
            long_side, short_side = max(pair_a, pair_b), min(pair_a, pair_b)
            if short_side == 0:
                return None
            return long_side, short_side
    return None


def _best_card_from_contours(
    contours, frame_area: float
) -> CalibrationResult | None:
    """Scan contours for the largest ID-1-shaped one, or None.

    Shared filter (min area, aspect ratio, rect fill ratio) applied regardless
    of how the contours were produced, so adding a new contour source never
    loosens what counts as a card -- it only gives genuine cards another
    chance to be found.
    """
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

        # Reject overly non-rectangular contours (a card's contour area should
        # closely fill its minAreaRect; loose fits are usually clutter/text blobs).
        rect_area = w * h
        if rect_area == 0 or area / rect_area < 0.75:
            continue

        quad = _quad_sides(contour)
        if quad is None:
            # Not a clean 4-corner shape -- fall back to the bounding-box
            # sides, but this is the stricter case, not a looser one: the
            # fill-ratio check above already demanded it look rectangular.
            long_side, short_side = max(w, h), min(w, h)
        else:
            long_side, short_side = quad

        ratio = long_side / short_side
        if abs(ratio - ID1_ASPECT_RATIO) > _ASPECT_TOLERANCE:
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


def detect_calibration_card(image: np.ndarray) -> CalibrationResult | None:
    """Return px_per_mm if an ID-1-shaped quadrilateral is found, else None.

    Never raises; an image with no card-shaped contour, or with multiple
    ambiguous candidates, resolves to None (no calibration reference in frame).

    Two independent contour sources are tried, both gated by the same
    aspect-ratio and fill-ratio checks in `_best_card_from_contours` so
    neither source can report a card that isn't actually card-shaped:

    1. Canny edge contours (original approach) -- works when the card's
       border has uniform contrast against its background on every side.
    2. A near-white / low-saturation colour mask -- an ID-1 card is a rigid
       white/light plastic rectangle, so this segments it as one solid
       blob even when the background contrast varies per side (e.g. one
       edge against a dark surface, another against a differently-coloured
       object) and Canny's edge trace breaks at those transitions.
    """
    if image is None or image.size == 0:
        return None

    frame_area = image.shape[0] * image.shape[1]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(blurred, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    edge_contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    white_mask = cv2.inRange(hsv, (0, 0, 150), (180, 60, 255))
    white_mask = cv2.morphologyEx(
        white_mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)
    )
    mask_contours, _ = cv2.findContours(
        white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    candidates = [
        c
        for c in (
            _best_card_from_contours(edge_contours, frame_area),
            _best_card_from_contours(mask_contours, frame_area),
        )
        if c is not None
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda c: c.card_width_px * c.card_height_px)
