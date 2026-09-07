"""Case lifecycle: create from a scan, inspector review, evidence attachment.
The reason-to-believe hard gate (CLAUDE.md invariant 12) is enforced by
lmd.store.repository.update_case_status raising ReasonToBelieveRequired,
which lmd.api.errors turns into a 422 citing Section 15(4).
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from lmd import config
from lmd.evidence.bsa63 import generate_certificate
from lmd.evidence.hashing import sha256_bytes
from lmd.store import repository
from lmd.store.models import CaseStatus, EvidenceType

from .deps import get_db, require_inspector

router = APIRouter(prefix="/api/v1", tags=["cases"])


class CreateCaseRequest(BaseModel):
    scan_id: str


class UpdateCaseRequest(BaseModel):
    status: CaseStatus
    reason_to_believe_note: Optional[str] = None


@router.post("/cases")
def create_case(body: CreateCaseRequest, inspector_id: str = Depends(require_inspector), conn=Depends(get_db)):
    scan = repository.get_scan(conn, body.scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail=f"scan not found: {body.scan_id}")
    case_id = repository.create_case(conn, body.scan_id, actor_id=inspector_id)
    return repository.get_case(conn, case_id)


@router.get("/cases/{case_id}")
def get_case(case_id: str, conn=Depends(get_db)):
    case = repository.get_case(conn, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"case not found: {case_id}")
    case["evidence"] = repository.list_evidence(conn, case_id)
    return case


@router.put("/cases/{case_id}")
def update_case(
    case_id: str,
    body: UpdateCaseRequest,
    inspector_id: str = Depends(require_inspector),
    conn=Depends(get_db),
):
    if repository.get_case(conn, case_id) is None:
        raise HTTPException(status_code=404, detail=f"case not found: {case_id}")
    return repository.update_case_status(
        conn,
        case_id,
        body.status,
        actor_id=inspector_id,
        reason_to_believe_note=body.reason_to_believe_note,
        assigned_inspector_id=inspector_id,
    )


@router.post("/cases/{case_id}/evidence")
async def attach_evidence(
    case_id: str,
    file: UploadFile,
    evidence_type: EvidenceType,
    device_identification: str,
    inspector_id: str = Depends(require_inspector),
    conn=Depends(get_db),
):
    if repository.get_case(conn, case_id) is None:
        raise HTTPException(status_code=404, detail=f"case not found: {case_id}")

    data = await file.read()
    file_hash = sha256_bytes(data)

    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    file_path = config.UPLOAD_DIR / f"evidence_{file_id}_{file.filename}"
    file_path.write_bytes(data)

    cert = generate_certificate(
        device_identification=device_identification,
        production_process_description="Inspector-captured evidence upload via lmd API /cases/{case_id}/evidence",
        record_sha256=file_hash,
    )
    repository.insert_certificate(conn, cert)

    evidence_id = repository.insert_evidence(
        conn,
        case_id=case_id,
        evidence_type=evidence_type.value,
        file_path=str(file_path),
        sha256_hash=file_hash,
        captured_by=inspector_id,
        bsa_s63_certificate_id=cert.certificate_id,
    )
    return {"evidence_id": evidence_id, "sha256_hash": file_hash, "certificate": cert.to_dict()}
