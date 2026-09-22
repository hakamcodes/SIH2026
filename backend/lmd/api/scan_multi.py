"""POST /api/v1/scans/multi - scan multiple panels (front/back/side/other) sequentially.

Panel bodies are read and processed one at a time (never all held in memory
at once) and freed with release_to_os() between panels -- a multi-panel scan
on Render's 512MB free tier otherwise ratchets RSS upward across panels
because glibc doesn't return freed arenas to the OS on its own."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import date
from typing import Any

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from lmd import config
from lmd.api.memory import release_to_os, rss_mb
from lmd.api.progress import ProgressReporter, ndjson_response, wants_ndjson
from lmd.cv.pipeline_a import OnStage, run_pipeline_a
from lmd.cv.reconcile import reconcile
from lmd.evidence.image_codec import compress_for_storage, encode_base64
from lmd.store import repository

from .deps import get_db, get_engine
from .scan import (
    _detect_barcodes_safe,
    _maybe_run_pipeline_b,
    _resize_to_max_dim,
    _serialize_calibration,
    _serialize_ocr_boxes,
)

router = APIRouter(prefix="/api/v1", tags=["scan"])
logger = logging.getLogger(__name__)

# Stage counts per panel: decode, calibration, glare, ocr, roi_retry, vision,
# reconcile always fire (7). The first present panel additionally captures
# barcodes and prepares overlay boxes for the frontend (+2 = 9). Shared
# stages fired once after all panels: merge, rules, compress, persist (4).
_STAGES_PER_PANEL = 7
_STAGES_FOR_FRONT_PANEL = 9
_SHARED_MULTI_STAGES = 4


def _multi_scan_total_stages(panel_count: int) -> int:
    if panel_count == 0:
        return _SHARED_MULTI_STAGES
    return _STAGES_FOR_FRONT_PANEL + _STAGES_PER_PANEL * (panel_count - 1) + _SHARED_MULTI_STAGES


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


def _process_panel_sync(
    image_bytes: bytes,
    panel_name: str,
    capture_extras: bool,
    on_stage: OnStage | None = None,
) -> dict[str, Any] | None:
    """Decode, resize, run pipeline A+B on one panel synchronously.
    Called inside a single worker thread per panel (the caller awaits each
    call before starting the next), so only one panel's arrays are ever alive
    at a time. When capture_extras is True (the first present panel, whose
    image is what gets displayed and stored), also returns barcodes, OCR
    boxes, calibration and the resized-JPEG bytes for that panel so the
    frontend's live SVG overlay has something to draw over.
    """
    np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
    cv_image_raw = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    np_arr = None
    if cv_image_raw is None:
        logger.warning("panel %s: could not decode, skipping", panel_name)
        return None
    if on_stage:
        on_stage("decode", "Decoding image", f"{cv_image_raw.shape[1]}x{cv_image_raw.shape[0]}px")

    cv_image = _resize_to_max_dim(cv_image_raw)
    if cv_image is not cv_image_raw:
        cv_image_raw = None

    extras: dict[str, Any] = {}
    if capture_extras:
        extras["barcodes"] = _detect_barcodes_safe(cv_image)
        if on_stage:
            found = extras["barcodes"]
            on_stage("barcode", "Scanning for barcodes", f"{len(found)} found" if found else "none found")

    t0 = time.perf_counter()
    pipeline_a_result = run_pipeline_a(cv_image, on_stage)
    vision_fields = _maybe_run_pipeline_b(image_bytes, on_stage)
    logger.info(
        "panel %s: A+B took %.2fs rss=%.1fMB", panel_name, time.perf_counter() - t0, rss_mb()
    )

    if capture_extras:
        ok, encoded_jpg = cv2.imencode(".jpg", cv_image)
        extras["image_bytes"] = encoded_jpg.tobytes() if ok else image_bytes
        extras["image_width"] = int(cv_image.shape[1])
        extras["image_height"] = int(cv_image.shape[0])
        extras["ocr_boxes"] = _serialize_ocr_boxes(pipeline_a_result)
        extras["calibration"] = _serialize_calibration(pipeline_a_result)
        if on_stage:
            on_stage("boxes", "Preparing overlay boxes", f"{len(extras['ocr_boxes'])} box(es)")
    cv_image = None

    envelope = reconcile(pipeline_a_result, vision_fields, scan_source=f"panel_{panel_name}")
    if on_stage:
        on_stage("reconcile", "Reconciling OCR and vision fields", None)
    return {"envelope": envelope, **extras}


async def _run_multi_scan(
    present: list[tuple[str, UploadFile]],
    scan_source: str,
    scan_date: str | None,
    commodity_category: str | None,
    commodity_subtype: str | None,
    commodity_is_imported: bool,
    commodity_is_exempt: bool,
    conn: Any,
    engine: Any,
    reporter: ProgressReporter | None,
) -> dict[str, Any]:
    """The actual multi-panel scan pipeline, shared by the plain-JSON and
    NDJSON-streamed routes below. `reporter` is None for the plain-JSON path."""

    effective_scan_date = scan_date or date.today().isoformat()

    # Read and process one panel at a time -- never hold more than one
    # panel's raw bytes in memory, and release freed arenas back to the OS
    # between panels so RSS doesn't ratchet upward across panels.
    panel_envelopes: list[tuple[str, dict[str, Any]]] = []
    front_extras: dict[str, Any] | None = None
    for index, (name, upload) in enumerate(present):
        data = await upload.read()

        def on_stage(key: str, label: str, detail: str | None = None, _panel: str = name) -> None:
            if reporter is not None:
                reporter.stage(_panel, key, label, detail)

        outcome = await asyncio.to_thread(_process_panel_sync, data, name, index == 0, on_stage)
        data = None
        if outcome is not None:
            panel_envelopes.append((name, outcome["envelope"]))
            if index == 0:
                front_extras = outcome
            if reporter is not None:
                reporter.panel_done(name, len(outcome["envelope"]))
        release_to_os(f"panel {name}")

    if not panel_envelopes:
        raise HTTPException(status_code=422, detail="no panel image could be decoded")

    def emit(key: str, label: str, detail: str | None = None) -> None:
        if reporter is not None:
            reporter.stage(None, key, label, detail)

    merged_envelope, panel_sources = _merge_envelopes(panel_envelopes)
    emit("merge", "Merging panel data", f"{len(panel_envelopes)} panel(s) merged")
    merged_envelope["commodity"] = {
        "category": commodity_category,
        "subtype": commodity_subtype,
        "is_imported": commodity_is_imported,
        "is_exempt": commodity_is_exempt,
    }

    result = engine.evaluate(merged_envelope, scan_date=effective_scan_date)
    emit("rules", "Evaluating ruleset", f"{len(result.rule_results)} rule(s) evaluated")

    images_base64: dict[str, str | None] = {}
    ocr_boxes: list[dict[str, Any]] = []
    calibration: dict[str, Any] | None = None
    barcodes: list[dict[str, Any]] = []
    if front_extras is not None and front_extras.get("image_bytes"):
        images_base64["original"] = encode_base64(
            compress_for_storage(front_extras["image_bytes"], "JPEG")
        )
        ocr_boxes = front_extras.get("ocr_boxes") or []
        calibration = front_extras.get("calibration")
        barcodes = front_extras.get("barcodes") or []
    front_extras = None
    emit("compress", "Compressing images for storage")

    # See scan.py's create_scan for why the image write is split in two.
    scan_id = repository.create_scan(
        conn,
        scan_date=effective_scan_date,
        scan_source=scan_source,
        ruleset_version=config.RULESET_VERSION,
        result=result,
        extraction_envelope=merged_envelope,
        images_base64=None,
        ocr_boxes=ocr_boxes,
        panel_sources=panel_sources,
    )
    repository.update_scan_images(conn, scan_id, images_base64)
    images_base64 = None
    emit("persist", "Saving scan record")

    response = {
        "scan_id": scan_id,
        "overall_verdict": result.overall_verdict.value,
        "extraction_envelope": merged_envelope,
        "panel_sources": panel_sources,
        "panels_processed": [name for name, _ in panel_envelopes],
        "barcodes": barcodes,
        "ocr_boxes": ocr_boxes,
        "calibration": calibration,
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
    release_to_os("multi scan done")
    return response


@router.post("/scans/multi")
async def create_multi_scan(
    request: Request,
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
    if len(present) > config.LMD_MAX_PANELS:
        raise HTTPException(
            status_code=400,
            detail=f"at most {config.LMD_MAX_PANELS} panel images are supported per scan",
        )

    args = (
        present, scan_source, scan_date, commodity_category, commodity_subtype,
        commodity_is_imported, commodity_is_exempt, conn, engine,
    )

    if wants_ndjson(request):
        total = _multi_scan_total_stages(len(present))
        return await ndjson_response(total, lambda reporter: _run_multi_scan(*args, reporter))
    return await _run_multi_scan(*args, None)
