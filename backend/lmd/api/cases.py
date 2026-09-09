"""Case lifecycle: create from a scan, inspector review, evidence attachment.
The reason-to-believe hard gate (CLAUDE.md invariant 12) is enforced by
lmd.store.repository.update_case_status raising ReasonToBelieveRequired,
which lmd.api.errors turns into a 422 citing Section 15(4).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from lmd.evidence.bsa63 import generate_certificate
from lmd.evidence.hashing import sha256_bytes
from lmd.evidence.image_codec import compress_for_storage, encode_base64
from lmd.store import audit, repository
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


@router.get("/cases")
def list_cases(
    status: Optional[CaseStatus] = None,
    limit: int = 50,
    offset: int = 0,
    conn=Depends(get_db),
):
    return {"cases": repository.list_cases(conn, status=status, limit=limit, offset=offset)}


@router.get("/cases/{case_id}")
def get_case(case_id: str, conn=Depends(get_db)):
    case = repository.get_case(conn, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"case not found: {case_id}")
    case["evidence"] = repository.list_evidence(conn, case_id)
    return case


@router.get("/cases/{case_id}/audit")
def get_case_audit(case_id: str, conn=Depends(get_db)):
    """Read-only view of the hash-chained audit log for this case (CLAUDE.md
    Section 63 certifiability claim rests on this chain being unbroken).
    Additive endpoint -- no existing write path or schema is touched."""
    if repository.get_case(conn, case_id) is None:
        raise HTTPException(status_code=404, detail=f"case not found: {case_id}")
    return {
        "entries": audit.list_entries(conn, case_id=case_id),
        "chain_verified": audit.verify(conn, case_id=case_id),
    }


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
    # Hash the bytes actually persisted (post-compression), not the original
    # upload -- the original is never stored anywhere, so a hash of it could
    # never be verified against anything. Hashing what's in Firestore keeps
    # the SHA-256 chain meaningful: it proves the stored evidence hasn't been
    # altered since ingestion, which is the guarantee this system can back.
    stored_bytes = compress_for_storage(data)
    file_hash = sha256_bytes(stored_bytes)

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
        file_base64=encode_base64(stored_bytes),
        sha256_hash=file_hash,
        captured_by=inspector_id,
        bsa_s63_certificate_id=cert.certificate_id,
    )
    return {"evidence_id": evidence_id, "sha256_hash": file_hash, "certificate": cert.to_dict()}
