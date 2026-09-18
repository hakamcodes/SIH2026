"""CRUD functions over Firestore. This is the only module that should
contain Firestore collection/document access outside of db.py's client
factory -- api/ handlers call through here, never through the Firestore
client directly.

Firestore has no JOIN and no GROUP BY. Two accommodations follow from that,
both applied at the call site below rather than via a query:
  - list_cases denormalizes scans.overall_verdict onto the case document at
    create_case() time, instead of joining at read time.
  - dashboard_counters fetches and tallies in Python. Fine at hackathon data
    volumes; would need real aggregation queries or maintained counters at
    any scale beyond that.

rule_results are embedded as an array field directly on the scan document
(not a subcollection) because they are never read independently of their
scan -- get_scan always wants both together, and nothing queries rule
results across scans.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from google.cloud.firestore import Client

from lmd.engine.models import ScanResult

from . import audit
from .models import REASON_TO_BELIEVE_GATED_STATUSES, CaseStatus

def _encode_ocr_boxes(ocr_boxes: list[dict]) -> list[dict]:
    """Firestore rejects an array value that directly contains another array
    (google.api_core.exceptions.InvalidArgument: "Property array contains an
    invalid nested entity"). Each OCR box's polygon is a list of [x, y]
    pairs -- a list of lists -- so it has to be re-shaped to a list of
    {"x", "y"} maps before storage. _decode_ocr_boxes reverses this so every
    caller (the API response, the frontend overlay, report_pdf) keeps seeing
    the original list[list[float]] shape."""
    encoded = []
    for box in ocr_boxes:
        box = dict(box)
        polygon = box.get("polygon")
        if polygon:
            box["polygon"] = [{"x": p[0], "y": p[1]} for p in polygon]
        encoded.append(box)
    return encoded


def _decode_ocr_boxes(ocr_boxes: list[dict]) -> list[dict]:
    decoded = []
    for box in ocr_boxes:
        box = dict(box)
        polygon = box.get("polygon")
        if polygon:
            box["polygon"] = [[p["x"], p["y"]] for p in polygon]
        decoded.append(box)
    return decoded


_SCANS = "scans"
_CASES = "cases"
_EVIDENCE = "evidence"
_EVIDENCE_CERTIFICATES = "evidence_certificates"
_INSPECTORS = "inspectors"
_REPORTS = "reports"


class ReasonToBelieveRequired(Exception):
    """Raised when a case status transition needs a recorded reason-to-believe
    note and none is present. Maps to HTTP 422 in the API layer, citing
    Section 15(4), Legal Metrology Act 2009 (CLAUDE.md invariant 12).

    This is now the *only* enforcement of that gate -- Firestore has no CHECK
    constraint equivalent to sqlite's chk_verified_reason, so there is no
    database-level backstop behind this Python check anymore."""


def create_scan(
    client: Client,
    scan_date: str,
    scan_source: str,
    ruleset_version: str,
    result: ScanResult,
    extraction_envelope: dict,
    images_base64: dict[str, str | None] | None = None,
    ocr_boxes: list[dict] | None = None,
) -> str:
    scan_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    rule_results = [
        {
            "rule_id": rule_id,
            "category": r.category,
            "severity": r.severity.value,
            "status": r.status.value,
            "on_fail_code": r.on_fail_code,
            "message": r.message,
            "legal_basis": r.legal_basis,
            "citation_verified": r.citation_verified,
        }
        for rule_id, r in result.rule_results.items()
    ]
    client.collection(_SCANS).document(scan_id).set(
        {
            "scan_id": scan_id,
            "scan_date": scan_date,
            "scan_source": scan_source,
            "ruleset_version": ruleset_version,
            "overall_verdict": result.overall_verdict.value,
            "extraction_envelope": extraction_envelope,
            "images_base64": images_base64 or {},
            "ocr_boxes": _encode_ocr_boxes(ocr_boxes or []),
            "rule_results": rule_results,
            "created_at": created_at,
        }
    )
    return scan_id


def get_scan(client: Client, scan_id: str) -> dict | None:
    doc = client.collection(_SCANS).document(scan_id).get()
    if not doc.exists:
        return None
    scan = doc.to_dict()
    scan.setdefault("images_base64", {})
    scan["ocr_boxes"] = _decode_ocr_boxes(scan.get("ocr_boxes") or [])
    scan.setdefault("rule_results", [])
    return scan


def ensure_inspector(client: Client, inspector_id: str) -> None:
    """The API's auth layer (lmd.api.deps.require_inspector) authenticates by
    shared bearer token + a caller-supplied inspector ID, with no separate
    registration endpoint (CLAUDE.md section 1 -- full RBAC/user management is
    out of scope). Upsert a minimal inspectors doc on first use so
    cases.assigned_inspector_id has something real to point at.
    """
    ref = client.collection(_INSPECTORS).document(inspector_id)
    if not ref.get().exists:
        ref.set({"inspector_id": inspector_id, "name": inspector_id, "designation": "Inspector", "active": True})


def create_case(client: Client, scan_id: str, actor_id: str) -> str:
    ensure_inspector(client, actor_id)
    scan = get_scan(client, scan_id)
    case_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    client.collection(_CASES).document(case_id).set(
        {
            "case_id": case_id,
            "scan_id": scan_id,
            "status": CaseStatus.QUEUED.value,
            "assigned_inspector_id": None,
            "reason_to_believe_note": None,
            "created_at": created_at,
            "verified_at": None,
            "closed_at": None,
            # Denormalized so list_cases never needs a join (Firestore has none).
            "scan_overall_verdict": scan["overall_verdict"] if scan else None,
        }
    )
    audit.append(client, actor_id=actor_id, action=f"created case from scan {scan_id}", case_id=case_id)
    return case_id


def get_case(client: Client, case_id: str) -> dict | None:
    doc = client.collection(_CASES).document(case_id).get()
    return doc.to_dict() if doc.exists else None


def list_cases(
    client: Client,
    status: CaseStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Case queue for the frontend. scan_overall_verdict is read straight off
    the case document (denormalized at create_case time) instead of joining
    against scans.

    The status filter is applied in Python, not via Firestore where(), so
    this never combines with order_by() into a composite query -- that
    combination requires a composite index Firestore does not create by
    default, which would otherwise force a manual one-time setup step in the
    Firebase console on every fresh project this gets deployed against."""
    query = client.collection(_CASES).order_by("created_at", direction="DESCENDING")
    docs = [doc.to_dict() for doc in query.stream()]
    if status is not None:
        docs = [doc for doc in docs if doc.get("status") == status.value]
    return docs[offset : offset + limit]


def update_case_status(
    client: Client,
    case_id: str,
    new_status: CaseStatus,
    actor_id: str,
    reason_to_believe_note: str | None = None,
    assigned_inspector_id: str | None = None,
) -> dict:
    existing = get_case(client, case_id)
    if existing is None:
        raise KeyError(f"case not found: {case_id}")

    ensure_inspector(client, actor_id)
    if assigned_inspector_id:
        ensure_inspector(client, assigned_inspector_id)

    effective_note = reason_to_believe_note or existing.get("reason_to_believe_note")
    if new_status in REASON_TO_BELIEVE_GATED_STATUSES and not effective_note:
        raise ReasonToBelieveRequired(
            f"case {case_id} cannot move to {new_status.value} without a recorded "
            "reason-to-believe note (Section 15(4), Legal Metrology Act 2009)."
        )

    now = datetime.now(timezone.utc).isoformat()
    verified_at = now if new_status in REASON_TO_BELIEVE_GATED_STATUSES else existing.get("verified_at")
    closed_at = now if new_status == CaseStatus.CLOSED else existing.get("closed_at")

    client.collection(_CASES).document(case_id).update(
        {
            "status": new_status.value,
            "reason_to_believe_note": effective_note,
            "assigned_inspector_id": assigned_inspector_id or existing.get("assigned_inspector_id"),
            "verified_at": verified_at,
            "closed_at": closed_at,
        }
    )
    audit.append(client, actor_id=actor_id, action=f"status -> {new_status.value}", case_id=case_id)
    return get_case(client, case_id)


def insert_certificate(client: Client, cert) -> None:
    client.collection(_EVIDENCE_CERTIFICATES).document(cert.certificate_id).set(
        {
            "certificate_id": cert.certificate_id,
            "device_identification": cert.device_identification,
            "production_process_description": cert.production_process_description,
            "certifying_officer": cert.certifying_officer,
            "generated_at": cert.generated_at,
            "integrity_hash": cert.record_sha256,
        }
    )


def insert_evidence(
    client: Client,
    case_id: str,
    evidence_type: str,
    file_base64: str,
    sha256_hash: str,
    captured_by: str,
    bsa_s63_certificate_id: str | None = None,
) -> str:
    evidence_id = str(uuid.uuid4())
    capture_timestamp = datetime.now(timezone.utc).isoformat()
    client.collection(_EVIDENCE).document(evidence_id).set(
        {
            "evidence_id": evidence_id,
            "case_id": case_id,
            "evidence_type": evidence_type,
            "file_base64": file_base64,
            "sha256_hash": sha256_hash,
            "capture_timestamp": capture_timestamp,
            "captured_by": captured_by,
            "bsa_s63_certificate_id": bsa_s63_certificate_id,
        }
    )
    return evidence_id


def list_evidence(client: Client, case_id: str) -> list[dict]:
    docs = client.collection(_EVIDENCE).where("case_id", "==", case_id).stream()
    return [doc.to_dict() for doc in docs]


def save_report(client: Client, case_id: str, pdf_base64: str, document_sha256: str, certificate_id: str) -> None:
    """Idempotent-per-case report cache, replacing the old on-disk
    data/uploads/reports/<case_id>.pdf. The PDF embeds a generation
    timestamp, so regenerating on every GET would mint a new "certified"
    document with a different hash each time -- storing it once and re-
    serving it is what keeps the Section 63 evidence chain stable."""
    client.collection(_REPORTS).document(case_id).set(
        {
            "case_id": case_id,
            "pdf_base64": pdf_base64,
            "document_sha256": document_sha256,
            "certificate_id": certificate_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def get_report(client: Client, case_id: str) -> dict | None:
    doc = client.collection(_REPORTS).document(case_id).get()
    return doc.to_dict() if doc.exists else None


def dashboard_counters(client: Client) -> dict:
    """The single counters page (CLAUDE.md section 1: 'a single counters page
    is the only dashboard'). No state/district/platform breakdown -- that
    tiering is explicitly out of scope. Firestore has no GROUP BY, so this
    fetches and tallies in Python; fine at hackathon data volumes.

    Extended to return:
    - top_failed_rules: top 10 rule IDs by FAIL count across all scans
    - top_missing_fields: top fields absent from extraction_envelope
    - compliance_by_category: {category: {verdict: count}}
    - recent_scans: last 10 scans with id/date/verdict/created_at
    """
    scans = [doc.to_dict() for doc in client.collection(_SCANS).stream()]
    cases = [doc.to_dict() for doc in client.collection(_CASES).stream()]

    # --- existing counters -------------------------------------------------
    by_verdict: dict[str, int] = {}
    for scan in scans:
        verdict = scan.get("overall_verdict")
        by_verdict[verdict] = by_verdict.get(verdict, 0) + 1

    by_case_status: dict[str, int] = {}
    for case in cases:
        status = case.get("status")
        by_case_status[status] = by_case_status.get(status, 0) + 1

    # --- top failed rules --------------------------------------------------
    rule_fail_counts: dict[str, int] = {}
    for scan in scans:
        for rr in scan.get("rule_results") or []:
            if rr.get("status") == "FAIL":
                rid = rr.get("rule_id", "unknown")
                rule_fail_counts[rid] = rule_fail_counts.get(rid, 0) + 1
    top_failed_rules = sorted(rule_fail_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # --- top missing fields ------------------------------------------------
    _TRACKED_FIELDS = [
        "net_quantity", "mrp", "manufacturer_or_packer_or_importer",
        "common_or_generic_name", "country_of_origin", "best_before_date",
        "mfg_date", "consumer_care",
    ]
    missing_counts: dict[str, int] = {}
    for scan in scans:
        envelope = scan.get("extraction_envelope") or {}
        for field in _TRACKED_FIELDS:
            if field not in envelope or envelope[field] is None:
                missing_counts[field] = missing_counts.get(field, 0) + 1
    top_missing_fields = sorted(missing_counts.items(), key=lambda x: x[1], reverse=True)

    # --- compliance by commodity category ----------------------------------
    compliance_by_category: dict[str, dict[str, int]] = {}
    for scan in scans:
        envelope = scan.get("extraction_envelope") or {}
        commodity = envelope.get("commodity") or {}
        category = commodity.get("category") or "unknown"
        verdict = scan.get("overall_verdict") or "unknown"
        cat_dict = compliance_by_category.setdefault(category, {})
        cat_dict[verdict] = cat_dict.get(verdict, 0) + 1

    # --- recent scans (last 10 by created_at) ------------------------------
    sorted_scans = sorted(
        scans, key=lambda s: s.get("created_at") or "", reverse=True
    )
    recent_scans = [
        {
            "scan_id": s.get("scan_id"),
            "scan_date": s.get("scan_date"),
            "overall_verdict": s.get("overall_verdict"),
            "created_at": s.get("created_at"),
        }
        for s in sorted_scans[:10]
    ]

    return {
        "total_scans": len(scans),
        "scans_by_verdict": by_verdict,
        "cases_by_status": by_case_status,
        "top_failed_rules": [{"rule_id": rid, "fail_count": cnt} for rid, cnt in top_failed_rules],
        "top_missing_fields": [{"field": f, "missing_count": cnt} for f, cnt in top_missing_fields],
        "compliance_by_category": compliance_by_category,
        "recent_scans": recent_scans,
    }
