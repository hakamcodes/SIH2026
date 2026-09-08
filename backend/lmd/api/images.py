"""GET /api/v1/scans/{scan_id}/image and /overlay -- Phase 0 addition.

scan.py already writes the original upload and the annotated overlay PNG to
config.UPLOAD_DIR and stores their filesystem paths in scans.image_paths_json
(index 0 = original, index 1 = overlay), but nothing serves them over HTTP --
a browser frontend cannot show the annotated overlay at all without this.

Both paths are resolved from the database, then re-validated to sit strictly
inside config.UPLOAD_DIR before being read, so a scan row can never be used
to read an arbitrary file off disk (path traversal / symlink escape guard).
No auth change: these were already reachable in spirit via GET
/api/v1/scans/{scan_id}'s image_paths field, which is itself unauthenticated.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from lmd import config
from lmd.store import repository

from .deps import get_db

router = APIRouter(prefix="/api/v1", tags=["images"])


def _resolve_within_upload_dir(raw_path: str) -> Path:
    upload_root = config.UPLOAD_DIR.resolve()
    candidate = Path(raw_path).resolve()
    if upload_root not in candidate.parents and candidate != upload_root:
        raise HTTPException(status_code=404, detail="image not found")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="image not found")
    return candidate


def _image_paths_for_scan(conn, scan_id: str) -> list[str]:
    scan = repository.get_scan(conn, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail=f"scan not found: {scan_id}")
    return scan["image_paths"]


@router.get("/scans/{scan_id}/image")
def get_scan_image(scan_id: str, conn=Depends(get_db)):
    image_paths = _image_paths_for_scan(conn, scan_id)
    if not image_paths:
        raise HTTPException(status_code=404, detail=f"no original image stored for scan {scan_id}")
    path = _resolve_within_upload_dir(image_paths[0])
    return FileResponse(path, media_type="image/jpeg")


@router.get("/scans/{scan_id}/overlay")
def get_scan_overlay(scan_id: str, conn=Depends(get_db)):
    image_paths = _image_paths_for_scan(conn, scan_id)
    if len(image_paths) < 2:
        raise HTTPException(status_code=404, detail=f"no overlay image stored for scan {scan_id}")
    path = _resolve_within_upload_dir(image_paths[1])
    return FileResponse(path, media_type="image/png")
