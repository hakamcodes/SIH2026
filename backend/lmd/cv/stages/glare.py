"""Specular-highlight (glare) masking. CLAUDE.md invariant 11: this is the
single pre-recognition exception to "no global image preprocessing" --
glare produces confident false-positive text detections rather than blanks
(measured on 01_curved_pouch_dense_text.jpg's holographic band), so it must
be suppressed before detection, unlike CLAHE/adaptive-threshold which are
applied only per-ROI after cropping.
"""
from __future__ import annotations

import cv2
import numpy as np

_V_THRESHOLD = 235
_S_THRESHOLD = 30


def glare_mask(image: np.ndarray) -> np.ndarray:
    """Return a uint8 mask (255 = glare) of near-white, low-saturation regions."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    _, s, v = cv2.split(hsv)
    mask = ((v >= _V_THRESHOLD) & (s <= _S_THRESHOLD)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=1)
    return mask


def apply_glare_mask(image: np.ndarray) -> np.ndarray:
    """Return a copy of image with glare regions replaced by local median grey,
    so the detector sees neutral background instead of a false-positive-prone
    bright blob, without altering non-glare pixels (no global preprocessing).
    """
    mask = glare_mask(image)
    if not mask.any():
        return image
    out = image.copy()
    fill_value = int(np.median(image[mask == 0])) if (mask == 0).any() else 127
    out[mask == 255] = fill_value
    return out
