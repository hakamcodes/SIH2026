"""CRUD functions over the sqlite schema in db.py. This is the only module
that should contain raw SQL outside of db.py's DDL -- api/ handlers call
through here, never through sqlite3 directly.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from lmd.engine.models import ScanResult

from . import audit
from .models import CaseStatus, REASON_TO_BELIEVE_GATED_STATUSES


class ReasonToBelieveRequired(Exception):
    """Raised when a case status transition needs a recorded reason-to-believe
    note and none is present. Maps to HTTP 422 in the API layer, citing
    Section 15(4), Legal Metrology Act 2009 (CLAUDE.md invariant 12)."""


def create_scan(
    conn: sqlite3.Connection,
    scan_date: str,
    scan_source: str,
    ruleset_version: str,
    result: ScanResult,
    extraction_envelope: dict,
    image_paths: list[str],
    ocr_boxes: list[dict] | None = None,
) -> str:
    scan_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO scans (scan_id, scan_date, scan_source, ruleset_version, overall_verdict,
                               extraction_envelope_json, image_paths_json, ocr_boxes_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            scan_id,
            scan_date,
            scan_source,
            ruleset_version,
            result.overall_verdict.value,
            json.dumps(extraction_envelope, ensure_ascii=False),
            json.dumps(image_paths),
            json.dumps(ocr_boxes or []),
            created_at,
        ),
    )
    for rule_id, r in result.rule_results.items():
        conn.execute(
            """INSERT INTO rule_results (scan_id, rule_id, category, severity, status,
                                          on_fail_code, message, legal_basis, citation_verified)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                scan_id,
                rule_id,
                r.category,
                r.severity.value,
                r.status.value,
                r.on_fail_code,
                r.message,
                r.legal_basis,
                int(r.citation_verified),
            ),
        )
    conn.commit()
    return scan_id


def get_scan(conn: sqlite3.Connection, scan_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM scans WHERE scan_id = ?", (scan_id,)).fetchone()
    if row is None:
        return None
    scan = dict(row)
    scan["extraction_envelope"] = json.loads(scan.pop("extraction_envelope_json"))
    scan["image_paths"] = json.loads(scan.pop("image_paths_json"))
    scan["ocr_boxes"] = json.loads(scan.pop("ocr_boxes_json", "[]") or "[]")
    rules = conn.execute("SELECT * FROM rule_results WHERE scan_id = ?", (scan_id,)).fetchall()
    scan["rule_results"] = [dict(r) for r in rules]
    return scan


def ensure_inspector(conn: sqlite3.Connection, inspector_id: str) -> None:
    """The API's auth layer (lmd.api.deps.require_inspector) authenticates by
    shared bearer token + a caller-supplied inspector ID, with no separate
    registration endpoint (CLAUDE.md section 1 -- full RBAC/user management is
    out of scope). Upsert a minimal inspectors row on first use so
    cases.assigned_inspector_id's foreign key has something real to point at.
    """
    conn.execute(
        "INSERT OR IGNORE INTO inspectors (inspector_id, name, designation, active) VALUES (?, ?, ?, 1)",
        (inspector_id, inspector_id, "Inspector"),
    )
    conn.commit()


def create_case(conn: sqlite3.Connection, scan_id: str, actor_id: str) -> str:
    ensure_inspector(conn, actor_id)
    case_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO cases (case_id, scan_id, status, created_at) VALUES (?, ?, ?, ?)",
        (case_id, scan_id, CaseStatus.QUEUED.value, created_at),
    )
    conn.commit()
    audit.append(conn, actor_id=actor_id, action=f"created case from scan {scan_id}", case_id=case_id)
    return case_id


def get_case(conn: sqlite3.Connection, case_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    return dict(row) if row is not None else None


def list_cases(
    conn: sqlite3.Connection,
    status: CaseStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Case queue for the frontend (no such listing existed before -- only
    get_case(case_id) did). Joins scans.overall_verdict so a queue row does
    not need a second round trip per case."""
    query = (
        "SELECT cases.*, scans.overall_verdict AS scan_overall_verdict "
        "FROM cases JOIN scans ON scans.scan_id = cases.scan_id "
    )
    params: list = []
    if status is not None:
        query += "WHERE cases.status = ? "
        params.append(status.value)
    query += "ORDER BY cases.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def update_case_status(
    conn: sqlite3.Connection,
    case_id: str,
    new_status: CaseStatus,
    actor_id: str,
    reason_to_believe_note: str | None = None,
    assigned_inspector_id: str | None = None,
) -> dict:
    existing = get_case(conn, case_id)
    if existing is None:
        raise KeyError(f"case not found: {case_id}")

    ensure_inspector(conn, actor_id)
    if assigned_inspector_id:
        ensure_inspector(conn, assigned_inspector_id)

    effective_note = reason_to_believe_note or existing.get("reason_to_believe_note")
    if new_status in REASON_TO_BELIEVE_GATED_STATUSES and not effective_note:
        raise ReasonToBelieveRequired(
            f"case {case_id} cannot move to {new_status.value} without a recorded "
            "reason-to-believe note (Section 15(4), Legal Metrology Act 2009)."
        )

    now = datetime.now(timezone.utc).isoformat()
    verified_at = now if new_status in REASON_TO_BELIEVE_GATED_STATUSES else existing.get("verified_at")
    closed_at = now if new_status == CaseStatus.CLOSED else existing.get("closed_at")

    try:
        conn.execute(
            """UPDATE cases SET status = ?, reason_to_believe_note = ?, assigned_inspector_id = ?,
                                 verified_at = ?, closed_at = ? WHERE case_id = ?""",
            (
                new_status.value,
                effective_note,
                assigned_inspector_id or existing.get("assigned_inspector_id"),
                verified_at,
                closed_at,
                case_id,
            ),
        )
    except sqlite3.IntegrityError as exc:
        # The DB-level CHECK constraint is the second gate (CLAUDE.md invariant
        # 12: "Enforced in the database CHECK constraint *and* the API"). If
        # the Python-level check above somehow missed a case, the DB refuses too.
        raise ReasonToBelieveRequired(str(exc)) from exc

    conn.commit()
    audit.append(conn, actor_id=actor_id, action=f"status -> {new_status.value}", case_id=case_id)
    return get_case(conn, case_id)


def insert_certificate(conn: sqlite3.Connection, cert) -> None:
    conn.execute(
        """INSERT INTO evidence_certificates
           (certificate_id, device_identification, production_process_description,
            certifying_officer, generated_at, integrity_hash)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            cert.certificate_id,
            cert.device_identification,
            cert.production_process_description,
            cert.certifying_officer,
            cert.generated_at,
            cert.record_sha256,
        ),
    )
    conn.commit()


def insert_evidence(
    conn: sqlite3.Connection,
    case_id: str,
    evidence_type: str,
    file_path: str,
    sha256_hash: str,
    captured_by: str,
    bsa_s63_certificate_id: str | None = None,
) -> str:
    evidence_id = str(uuid.uuid4())
    capture_timestamp = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO evidence (evidence_id, case_id, evidence_type, file_path, sha256_hash,
                                  capture_timestamp, captured_by, bsa_s63_certificate_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (evidence_id, case_id, evidence_type, file_path, sha256_hash, capture_timestamp, captured_by, bsa_s63_certificate_id),
    )
    conn.commit()
    return evidence_id


def list_evidence(conn: sqlite3.Connection, case_id: str) -> list[dict]:
    rows = conn.execute("SELECT * FROM evidence WHERE case_id = ?", (case_id,)).fetchall()
    return [dict(r) for r in rows]


def dashboard_counters(conn: sqlite3.Connection) -> dict:
    """The single counters page (CLAUDE.md section 1: 'a single counters page
    is the only dashboard'). No state/district/platform breakdown -- that
    tiering is explicitly out of scope."""
    total_scans = conn.execute("SELECT COUNT(*) AS n FROM scans").fetchone()["n"]
    by_verdict = {
        row["overall_verdict"]: row["n"]
        for row in conn.execute(
            "SELECT overall_verdict, COUNT(*) AS n FROM scans GROUP BY overall_verdict"
        ).fetchall()
    }
    by_case_status = {
        row["status"]: row["n"]
        for row in conn.execute("SELECT status, COUNT(*) AS n FROM cases GROUP BY status").fetchall()
    }
    return {
        "total_scans": total_scans,
        "scans_by_verdict": by_verdict,
        "cases_by_status": by_case_status,
    }
