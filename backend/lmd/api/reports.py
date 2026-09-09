"""POST /api/v1/cases/{case_id}/report -- generate the violation report PDF
and its Section 63 BSA certificate (CLAUDE.md: "signed PDF violation report
with a SHA-256 evidence chain and a Section 63 BSA 2023 certificate").

Generation is idempotent per case: the PDF is written once to the
`reports/{case_id}` Firestore document and served from there on subsequent
GETs, because the report embeds a generation timestamp -- regenerating on
every GET would silently mint a new "certified" document with a different
hash each time, which is exactly the kind of unstable evidence chain
CLAUDE.md's Section 63 claim depends on not doing. Storing the PDF as a
base64 field (rather than a file under data/uploads/reports/) is the same
move as scan images and case evidence: Render's disk does not survive a
redeploy, Firestore does.
"""
from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response

from lmd.evidence import report_pdf
from lmd.evidence.bsa63 import generate_certificate
from lmd.evidence.hashing import sha256_bytes
from lmd.store import repository

from .deps import get_db, require_inspector

router = APIRouter(prefix="/api/v1", tags=["reports"])


@router.post("/cases/{case_id}/report")
def generate_report(
    case_id: str,
    inspector_id: str = Depends(require_inspector),
    x_inspector_name: str = Header(default=None),
    conn=Depends(get_db),
):
    case = repository.get_case(conn, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"case not found: {case_id}")
    scan = repository.get_scan(conn, case["scan_id"])
    evidence_list = repository.list_evidence(conn, case_id)

    pdf_bytes = report_pdf.generate_report(
        case, scan, evidence_list,
        inspector={"name": x_inspector_name or inspector_id, "inspector_id": inspector_id},
    )

    doc_hash = sha256_bytes(pdf_bytes)
    cert = generate_certificate(
        device_identification=f"lmd-api-server (generated for inspector {inspector_id})",
        production_process_description=(
            "Rule engine evaluation (packages/rules/lmd_rules.v1.json) + "
            "lmd.evidence.report_pdf.generate_report, reportlab renderer."
        ),
        record_sha256=doc_hash,
    )
    repository.insert_certificate(conn, cert)
    repository.save_report(
        conn,
        case_id=case_id,
        pdf_base64=base64.b64encode(pdf_bytes).decode("ascii"),
        document_sha256=doc_hash,
        certificate_id=cert.certificate_id,
    )

    return {
        "case_id": case_id,
        "document_sha256": doc_hash,
        "certificate": cert.to_dict(),
        "download_url": f"/api/v1/cases/{case_id}/report",
    }


@router.get("/cases/{case_id}/report")
def download_report(case_id: str, conn=Depends(get_db)):
    report = repository.get_report(conn, case_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"no report generated yet for case {case_id}; POST /api/v1/cases/{case_id}/report first",
        )
    return Response(content=base64.b64decode(report["pdf_base64"]), media_type="application/pdf")
