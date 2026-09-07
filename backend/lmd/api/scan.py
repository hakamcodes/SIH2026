"""POST /api/v1/scans -- the vertical slice's entry point: image in, rule
verdict out. Runs pipeline A always; pipeline B only if ANTHROPIC_API_KEY is
configured (CLAUDE.md invariant 7 already means an absent pipeline B simply
leaves numeric fields without a cross-check, which the existing LM-U02 rule
and confidence gates handle -- this endpoint does not fabricate a vision
reading when the key is missing).
"""
from __future__ import annotations

import os
import uuid
from datetime import date
from typing import Any

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from lmd import config
from lmd.cv.overlay import encode_png, render_overlay
from lmd.cv.pipeline_a import run_pipeline_a
from lmd.cv.reconcile import reconcile
from lmd.evidence.hashing import sha256_bytes
from lmd.store import repository

from .deps import get_db, get_engine

router = APIRouter(prefix="/api/v1", tags=["scan"])


def _maybe_run_pipeline_b(image_bytes: bytes) -> dict[str, Any]:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {}
    from lmd.cv.pipeline_b import extract_with_vision

    try:
        return extract_with_vision(image_bytes)
    except Exception:  # noqa: BLE001 -- a vision-pipeline failure must never break the scan
        return {}


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

    pipeline_a_result = run_pipeline_a(cv_image)
    vision_fields = _maybe_run_pipeline_b(image_bytes)
    envelope = reconcile(pipeline_a_result, vision_fields, scan_source=scan_source)

    envelope["commodity"] = {
        "category": commodity_category,
        "subtype": commodity_subtype,
        "is_imported": commodity_is_imported,
        "is_exempt": commodity_is_exempt,
    }

    result = engine.evaluate(envelope, scan_date=effective_scan_date)

    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    image_id = str(uuid.uuid4())
    image_path = config.UPLOAD_DIR / f"{image_id}.jpg"
    image_path.write_bytes(image_bytes)

    overlay_image = render_overlay(cv_image, pipeline_a_result, result.overall_verdict.value)
    overlay_path = config.UPLOAD_DIR / f"{image_id}_overlay.png"
    overlay_path.write_bytes(encode_png(overlay_image))

    scan_id = repository.create_scan(
        conn,
        scan_date=effective_scan_date,
        scan_source=scan_source,
        ruleset_version=config.RULESET_VERSION,
        result=result,
        extraction_envelope=envelope,
        image_paths=[str(image_path), str(overlay_path)],
    )

    return {
        "scan_id": scan_id,
        "overall_verdict": result.overall_verdict.value,
        "extraction_envelope": envelope,
        "image_sha256": sha256_bytes(image_bytes),
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
