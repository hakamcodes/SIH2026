"""POST /api/v1/scans -- the vertical slice's entry point: image in, rule
verdict out. Runs pipeline A always; pipeline B only if ANTHROPIC_API_KEY is
configured (CLAUDE.md invariant 7 already means an absent pipeline B simply
leaves numeric fields without a cross-check, which the existing LM-U02 rule
and confidence gates handle -- this endpoint does not fabricate a vision
reading when the key is missing).
"""
from __future__ import annotations

import asyncio
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
    cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if cv_image is None:
        raise HTTPException(status_code=400, detail="uploaded file is not a decodable image")

    effective_scan_date = scan_date or date.today().isoformat()

    t0 = time.perf_counter()
    # Pipeline A (CPU-bound OCR) and pipeline B (network-bound vision call,
    # a no-op when no API key or on a cache hit) are independent -- running
    # them concurrently in worker threads keeps pipeline B's latency off the
    # critical path and stops either from blocking the event loop.
    pipeline_a_result, vision_fields = await asyncio.gather(
        asyncio.to_thread(run_pipeline_a, cv_image),
        asyncio.to_thread(_maybe_run_pipeline_b, image_bytes),
    )
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
    images_base64 = {
        "original": encode_base64(compress_for_storage(image_bytes, "JPEG")),
        "overlay": encode_base64(compress_for_storage(encode_png(overlay_image), "PNG")),
    }

    ocr_boxes = _serialize_ocr_boxes(pipeline_a_result)

    scan_id = repository.create_scan(
        conn,
        scan_date=effective_scan_date,
        scan_source=scan_source,
        ruleset_version=config.RULESET_VERSION,
        result=result,
        extraction_envelope=envelope,
        images_base64=images_base64,
        ocr_boxes=ocr_boxes,
    )

    return {
        "scan_id": scan_id,
        "overall_verdict": result.overall_verdict.value,
        "extraction_envelope": envelope,
        "image_sha256": sha256_bytes(image_bytes),
        "image_width": cv_image.shape[1],
        "image_height": cv_image.shape[0],
        "ocr_boxes": ocr_boxes,
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


@router.get("/scans/{scan_id}")
def get_scan(scan_id: str, conn=Depends(get_db)):
    scan = repository.get_scan(conn, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail=f"scan not found: {scan_id}")
    return scan
