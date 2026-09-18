"""POST /api/v1/scans/multi - scan multiple panels (front/back/side/other) sequentially."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import date
from typing import Any

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from lmd import config
from lmd.cv.pipeline_a import run_pipeline_a
from lmd.cv.reconcile import reconcile
from lmd.evidence.image_codec import compress_for_storage, encode_base64
from lmd.store import repository

from .deps import get_db, get_engine
from .scan import _detect_barcodes_safe, _maybe_run_pipeline_b, _resize_to_max_dim

router = APIRouter(prefix="/api/v1", tags=["scan"])
logger = logging.getLogger(__name__)


def _merge_envelopes(
    panel_envelopes: list[tuple[str, dict[str, Any]]],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Merge per-panel reconciled envelopes.
    For each field, the value from the panel with the highest field_confidences wins.
    For numeric fields (mrp, net_quantity), ocr_pipeline/llm_pipeline from the
    winning panel are preserved so LM-U02 disagreement routing is intact.
    panel_sources records which panel provided each field (informational only).
    """
    if not panel_envelopes:
        return {}, {}

    merged: dict[str, Any] = {
        "schema_version": panel_envelopes[0][1].get("schema_version", "1.0"),
        "scan_source": panel_envelopes[0][1].get("scan_source", "multi_panel"),
    }
    merged_confidences: dict[str, float] = {}
    panel_sources: dict[str, str] = {}

    _SKIP = {"schema_version", "scan_source", "commodity", "field_confidences",
              "ocr_pipeline", "llm_pipeline"}

    for panel_name, envelope in panel_envelopes:
        confidences = envelope.get("field_confidences") or {}
        for key, value in envelope.items():
            if key in _SKIP:
                continue
            field_conf = confidences.get(key, 1.0)
            if field_conf > merged_confidences.get(key, -1.0):
                merged[key] = value
                merged_confidences[key] = field_conf
                panel_sources[key] = panel_name

    for numeric_key in ("mrp", "net_quantity"):
        winning_panel = panel_sources.get(numeric_key)
        if winning_panel is None:
            continue
        for pe_name, pe_env in panel_envelopes:
            if pe_name == winning_panel:
                if "ocr_pipeline" in pe_env and "ocr_pipeline" not in merged:
                    merged["ocr_pipeline"] = pe_env["ocr_pipeline"]
                if "llm_pipeline" in pe_env and "llm_pipeline" not in merged:
                    merged["llm_pipeline"] = pe_env["llm_pipeline"]
                break

    if merged_confidences:
        merged["field_confidences"] = merged_confidences

    return merged, panel_sources


def _process_panel_sync(image_bytes: bytes, panel_name: str) -> dict[str, Any] | None:
    """Decode, resize, run pipeline A+B on one panel synchronously.
    Called inside a single worker thread so panels are processed one at a time.
    Arrays are released before returning.
    """
    np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
    cv_image_raw = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    np_arr = None
    if cv_image_raw is None:
        logger.warning("panel %s: could not decode, skipping", panel_name)
        return None

    cv_image = _resize_to_max_dim(cv_image_raw)
    if cv_image is not cv_image_raw:
        cv_image_raw = None

    t0 = time.perf_counter()
    pipeline_a_result = run_pipeline_a(cv_image)
    vision_fields = _maybe_run_pipeline_b(image_bytes)
    cv_image = None
    logger.info("panel %s: A+B took %.2fs", panel_name, time.perf_counter() - t0)

    return reconcile(pipeline_a_result, vision_fields, scan_source=f"panel_{panel_name}")


async def _process_panels_sequentially(
    panels: list[tuple[str, bytes]],
) -> list[tuple[str, dict[str, Any]]]:
    """Run all panels sequentially inside ONE worker thread to keep peak RAM flat."""
    def _run_all() -> list[tuple[str, dict[str, Any] | None]]:
        return [(name, _process_panel_sync(data, name)) for name, data in panels]

    raw = await asyncio.to_thread(_run_all)
    return [(name, env) for name, env in raw if env is not None]


@router.post("/scans/multi")
async def create_multi_scan(
    image_front: UploadFile | None = File(default=None),
    image_back: UploadFile | None = File(default=None),
    image_side: UploadFile | None = File(default=None),
    image_other: UploadFile | None = File(default=None),
    scan_source: str = Form("multi_panel"),
    scan_date: str | None = Form(default=None),
    commodity_category: str | None = Form(default=None),
    commodity_subtype: str | None = Form(default=None),
    commodity_is_imported: bool = Form(default=False),
    commodity_is_exempt: bool = Form(default=False),
    conn=Depends(get_db),
    engine=Depends(get_engine),
):
    present = [
        (name, upload)
        for name, upload in [
            ("front", image_front), ("back", image_back),
            ("side", image_side), ("other", image_other),
        ]
        if upload is not None
    ]
    if not present:
        raise HTTPException(status_code=400, detail="at least one panel image is required")

    panels: list[tuple[str, bytes]] = []
    first_image_bytes: bytes | None = None
    for name, upload in present:
        data = await upload.read()
        panels.append((name, data))
        if first_image_bytes is None:
            first_image_bytes = data

    effective_scan_date = scan_date or date.today().isoformat()

    barcodes: list[dict[str, Any]] = []
    if first_image_bytes:
        np_arr = np.frombuffer(first_image_bytes, dtype=np.uint8)
        first_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        np_arr = None
        if first_cv is not None:
            barcodes = _detect_barcodes_safe(_resize_to_max_dim(first_cv))
            first_cv = None

    panel_envelopes = await _process_panels_sequentially(panels)
    panels = []

    if not panel_envelopes:
        raise HTTPException(status_code=422, detail="no panel image could be decoded")

    merged_envelope, panel_sources = _merge_envelopes(panel_envelopes)
    merged_envelope["commodity"] = {
        "category": commodity_category,
        "subtype": commodity_subtype,
        "is_imported": commodity_is_imported,
        "is_exempt": commodity_is_exempt,
    }

    result = engine.evaluate(merged_envelope, scan_date=effective_scan_date)

    images_base64: dict[str, str | None] = {}
    if first_image_bytes:
        images_base64["original"] = encode_base64(
            compress_for_storage(first_image_bytes, "JPEG")
        )

    scan_id = repository.create_scan(
        conn,
        scan_date=effective_scan_date,
        scan_source=scan_source,
        ruleset_version=config.RULESET_VERSION,
        result=result,
        extraction_envelope=merged_envelope,
        images_base64=images_base64,
        ocr_boxes=[],
    )

    return {
        "scan_id": scan_id,
        "overall_verdict": result.overall_verdict.value,
        "extraction_envelope": merged_envelope,
        "panel_sources": panel_sources,
        "panels_processed": [name for name, _ in panel_envelopes],
        "barcodes": barcodes,
        "ocr_boxes": [],
        "calibration": None,
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
