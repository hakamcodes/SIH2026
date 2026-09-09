"""GET /api/v1/scans/{scan_id}/image and /overlay -- Phase 0 addition.

scan.py stores the (compressed) original upload and the annotated overlay
PNG as base64 fields directly on the scan's Firestore document
(scans/{scan_id}.images_base64), not as files on disk -- Render's disk is
ephemeral, so anything that needs to survive a redeploy has to live in
Firestore instead. These two routes decode that field back to raw bytes.
Route contract (URL, status codes, media types) is unchanged from the
disk-backed version, so the frontend needed no changes for this swap.
"""
from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from lmd.store import repository

from .deps import get_db

router = APIRouter(prefix="/api/v1", tags=["images"])


def _images_for_scan(conn, scan_id: str) -> dict:
    scan = repository.get_scan(conn, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail=f"scan not found: {scan_id}")
    return scan.get("images_base64") or {}


@router.get("/scans/{scan_id}/image")
def get_scan_image(scan_id: str, conn=Depends(get_db)):
    b64 = _images_for_scan(conn, scan_id).get("original")
    if not b64:
        raise HTTPException(status_code=404, detail=f"no original image stored for scan {scan_id}")
    return Response(content=base64.b64decode(b64), media_type="image/jpeg")


@router.get("/scans/{scan_id}/overlay")
def get_scan_overlay(scan_id: str, conn=Depends(get_db)):
    b64 = _images_for_scan(conn, scan_id).get("overlay")
    if not b64:
        raise HTTPException(status_code=404, detail=f"no overlay image stored for scan {scan_id}")
    return Response(content=base64.b64decode(b64), media_type="image/png")
