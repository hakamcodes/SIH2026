"""POST /api/v1/scans -- the vertical slice's entry point: image in, rule
verdict out. Runs pipeline A always; pipeline B only if ANTHROPIC_API_KEY is
configured (CLAUDE.md invariant 7 already means an absent pipeline B simply
leaves numeric fields without a cross-check, which the existing LM-U02 rule
and confidence gates handle -- this endpoint does not fabricate a vision
reading when the key is missing).
"""
from __future__ import annotations

import asyncio
import gc
import logging
import os
import time
from datetime import date
from typing import Any

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from lmd import config
from lmd.cv.overlay import encode_png, render_overlay
from lmd.cv.pipeline_a import PipelineAResult, run_pipeline_a
from lmd.cv.reconcile import reconcile
from lmd.evidence.hashing import sha256_bytes
from lmd.evidence.image_codec import compress_for_storage, encode_base64
from lmd.store import repository

from .deps import get_db, get_engine

router = APIRouter(prefix="/api/v1", tags=["scan"])
logger = logging.getLogger(__name__)

# Hard cap applied at the API boundary before any pipeline touches the image.
# Pipeline A has an internal _MAX_DETECTION_DIM cap but pre-resizing here
# ensures the full-res array is never kept alive during the async gather with
# pipeline B, reducing peak RSS.
_API_MAX_DIM = 1280


def _resize_to_max_dim(image: np.ndarray, max_dim: int = _API_MAX_DIM) -> np.ndarray:
    """Return image unchanged when already within max_dim; otherwise downscale
    (AREA interpolation, best for downscaling) keeping aspect ratio. Never
    upscales -- a small image must stay small."""
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest <= max_dim:
        return image
    scale = max_dim / longest
    new_w, new_h = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _detect_barcodes_safe(image: np.ndarray) -> list[dict[str, Any]]:
    """Best-effort barcode/QR detection. Returns [] when zxingcpp is not
    installed or detection fails -- barcode is always optional and must never
    break an ordinary scan."""
    try:
        import zxingcpp  # type: ignore[import-untyped]

        results = zxingcpp.read_barcodes(image)
        return [{"format": str(r.format), "text": r.text} for r in results if r.text]
    except ImportError:
        return []
    except Exception:  # noqa: BLE001
        logger.debug("barcode detection failed (non-fatal)", exc_info=True)
        return []


def _maybe_run_pipeline_b(image_bytes: bytes) -> dict[str, Any]:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.info("pipeline B skipped: ANTHROPIC_API_KEY not set")
        return {}
    from lmd.cv.pipeline_b import extract_with_vision

    try:
        return extract_with_vision(image_bytes)
    except Exception:  # noqa: BLE001 -- a vision-pipeline failure must never break the scan
        logger.exception("pipeline B failed; continuing with pipeline A only")
        return {}


def _serialize_ocr_boxes(pipeline_a_result: PipelineAResult) -> list[dict[str, Any]]:
    """Frontend Phase 0 addition: expose the box geometry that already exists
    inside PipelineAResult (never persisted or returned before this) so the
    frontend can draw an interactive overlay instead of only the baked PNG.
    Read-only projection -- does not change what pipeline A computes."""
    boxes: list[dict[str, Any]] = []
    for f in pipeline_a_result.fields:
        boxes.append(
            {
                "text": f.text,
                "confidence": f.confidence,
                "polygon": f.polygon,
                "enhanced": f.enhanced,
                "font_metrics": {
                    "box_h_px": f.font_metrics.box_h_px,
                    "ink_h_px": f.font_metrics.ink_h_px,
                    "height_mm": f.font_metrics.height_mm,
                    "measurable": f.font_metrics.measurable,
                    "reason": f.font_metrics.reason,
                },
            }
        )
    return boxes


def _serialize_calibration(pipeline_a_result: PipelineAResult) -> dict[str, Any] | None:
    calibration = pipeline_a_result.calibration
    if calibration is None:
        return None
    return {
        "px_per_mm": calibration.px_per_mm,
        "card_width_px": calibration.card_width_px,
        "card_height_px": calibration.card_height_px,
        "bounding_box": list(calibration.bounding_box),
    }


@router.post("/scans")
async def create_scan(
    image: UploadFile = File(...),
    scan_source: str = Form("package_image"),
    scan_date: str | None = Form(default=None),
    commodity_category: str | None = Form(default=None),
    commodity_subtype: str | None = Form(default=None),
    commodity_is_imported: bool = Form(default=False),
    commodity_is_exempt: bool = Form(default=False),
    conn=Depends(get_db),
    engine=Depends(get_engine),
):
    image_bytes = await image.read()
    np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
    cv_image_raw = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    np_arr = None  # release the intermediate buffer; cv_image_raw owns the pixel data now
    if cv_image_raw is None:
        raise HTTPException(status_code=400, detail="uploaded file is not a decodable image")

    # Resize to the API-level cap before any pipeline work.  This keeps the
    # peak-resident array small for the duration of the async gather below.
    cv_image = _resize_to_max_dim(cv_image_raw)
    if cv_image is not cv_image_raw:
        cv_image_raw = None  # allow GC of the full-res array now that we have the smaller one

    effective_scan_date = scan_date or date.today().isoformat()

    # Detect barcodes on the (already-resized) image before starting the OCR
    # pipelines; detection is fast and purely optional.
    barcodes = _detect_barcodes_safe(cv_image)

    t0 = time.perf_counter()
    # Pipeline A (CPU-bound OCR) and pipeline B (network-bound vision call,
    # a no-op when no API key or on a cache hit) are run sequentially, not
    # concurrently -- on the 512MB Render free tier, overlapping both peaks
    # at once was pushing RSS over the instance cap. Sequential costs some
    # latency but keeps only one pipeline's peak memory live at a time.
    pipeline_a_result = await asyncio.to_thread(run_pipeline_a, cv_image)
    vision_fields = await asyncio.to_thread(_maybe_run_pipeline_b, image_bytes)
    image_bytes_for_hash = image_bytes  # keep a reference for sha256 below
    image_bytes = None  # release before the expensive overlay/storage steps
    logger.info("scan %s: pipelines A+B took %.2fs", scan_source, time.perf_counter() - t0)
    envelope = reconcile(pipeline_a_result, vision_fields, scan_source=scan_source)

    envelope["commodity"] = {
        "category": commodity_category,
        "subtype": commodity_subtype,
        "is_imported": commodity_is_imported,
        "is_exempt": commodity_is_exempt,
    }

    result = engine.evaluate(envelope, scan_date=effective_scan_date)

    # Images live as base64 fields on the scan document, not files on disk --
    # Render's disk is ephemeral, so anything meant to survive a redeploy has
    # to go to Firestore. compress_for_storage keeps each field well under
    # Firestore's 1 MiB document cap before the ~33% base64 overhead is added.
    overlay_image = render_overlay(cv_image, pipeline_a_result, result.overall_verdict.value)
    # Encode cv_image so the stored original exactly matches the resized dimensions
    # used by pipeline_a. This guarantees the frontend SVG viewBox aligns with the OCR boxes.
    ok, encoded_jpg = cv2.imencode(".jpg", cv_image)
    stored_original_bytes = encoded_jpg.tobytes() if ok else image_bytes_for_hash
    
    images_base64 = {
        "original": encode_base64(compress_for_storage(stored_original_bytes, "JPEG")),
        # Tighter budget than the 600 KB/1600px default: the overlay is a
        # display/download convenience (the frontend draws live SVG boxes
        # over the "original" JPEG for the main view), so a smaller, palette
        # PNG is enough and keeps the Firestore doc smaller.
        "overlay": encode_base64(
            compress_for_storage(
                encode_png(overlay_image), "PNG", max_bytes=250_000, max_dimension_px=900, palette=True
            )
        ),
    }
    overlay_image = None  # release overlay array after encoding

    ocr_boxes = _serialize_ocr_boxes(pipeline_a_result)
    image_width, image_height = cv_image.shape[1], cv_image.shape[0]
    image_sha256 = sha256_bytes(image_bytes_for_hash)
    cv_image = None  # released; only its already-extracted shape/hash are needed below

    # Write the scan doc without the (large) image fields first, then patch
    # them in with a second, smaller write -- keeps the peak in-memory dict
    # (protobuf-serialized by the Firestore client) from holding both base64
    # image strings plus the rest of the scan document at once.
    scan_id = repository.create_scan(
        conn,
        scan_date=effective_scan_date,
        scan_source=scan_source,
        ruleset_version=config.RULESET_VERSION,
        result=result,
        extraction_envelope=envelope,
        images_base64=None,
        ocr_boxes=ocr_boxes,
    )
    repository.update_scan_images(conn, scan_id, images_base64)
    images_base64 = None  # released after the second write

    response = {
        "scan_id": scan_id,
        "overall_verdict": result.overall_verdict.value,
        "extraction_envelope": envelope,
        "image_sha256": image_sha256,
        "image_width": image_width,
        "image_height": image_height,
        "ocr_boxes": ocr_boxes,
        "barcodes": barcodes,
        "calibration": _serialize_calibration(pipeline_a_result),
        "rule_results": {
            rid: {
                "status": r.status.value,
                "severity": r.severity.value,
                "category": r.category,
                "on_fail_code": r.on_fail_code,
                "message": r.message,
                "legal_basis": r.legal_basis,
                "citation_verified": r.citation_verified,
            }
            for rid, r in result.rule_results.items()
        },
    }
    # Reclaim the NumPy arrays/base64 strings from this scan immediately --
    # Python's generational GC doesn't guarantee it before the next request,
    # and there is no RAM headroom to spare on Render's 512 MB free tier.
    gc.collect()
    return response


@router.get("/scans/{scan_id}")
def get_scan(scan_id: str, conn=Depends(get_db)):
    scan = repository.get_scan(conn, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail=f"scan not found: {scan_id}")
    return scan
