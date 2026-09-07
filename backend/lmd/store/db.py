"""SQLite persistence for local/offline dev and the hackathon prototype.

Uses stdlib sqlite3 rather than SQLAlchemy or a Postgres driver -- this machine
has no Docker and no Postgres server (CLAUDE.md section 2). The schema here is
semantically identical to store/ddl_postgres.sql (same tables, same columns,
same CHECK constraints) so porting to Postgres later is a mechanical DDL swap,
not a data-model change.

The reason-to-believe hard gate (CLAUDE.md invariant 12) is enforced twice:
once here via a CHECK constraint (`chk_verified_reason`), and again in
backend/lmd/api/cases.py before the UPDATE ever reaches this layer, so the
422 has a chance to carry the Section 15(4) message instead of surfacing a
raw sqlite3.IntegrityError to a caller.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS inspectors (
    inspector_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    designation TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS scans (
    scan_id TEXT PRIMARY KEY,
    scan_date TEXT NOT NULL,
    scan_source TEXT NOT NULL,
    ruleset_version TEXT NOT NULL,
    overall_verdict TEXT NOT NULL CHECK (overall_verdict IN ('COMPLIANT', 'NON_COMPLIANT', 'NEEDS_REVIEW')),
    extraction_envelope_json TEXT NOT NULL,
    image_paths_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rule_results (
    scan_id TEXT NOT NULL REFERENCES scans(scan_id) ON DELETE CASCADE,
    rule_id TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('BLOCKER', 'MAJOR', 'MINOR', 'DIAGNOSTIC')),
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'REVIEW', 'NOT_APPLICABLE', 'NOT_IN_FORCE', 'NOT_EVALUABLE')),
    on_fail_code TEXT,
    message TEXT NOT NULL,
    legal_basis TEXT NOT NULL,
    citation_verified INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (scan_id, rule_id)
);

CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL REFERENCES scans(scan_id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (
        status IN ('QUEUED', 'UNDER_REVIEW', 'CONFIRMED_VIOLATION', 'REJECTED_FALSE_POSITIVE', 'ESCALATED', 'CLOSED')
    ) DEFAULT 'QUEUED',
    assigned_inspector_id TEXT REFERENCES inspectors(inspector_id) ON DELETE SET NULL,
    reason_to_believe_note TEXT,
    created_at TEXT NOT NULL,
    verified_at TEXT,
    closed_at TEXT,
    CONSTRAINT chk_verified_reason CHECK (
        (status IN ('CONFIRMED_VIOLATION', 'ESCALATED', 'CLOSED')
            AND reason_to_believe_note IS NOT NULL AND reason_to_believe_note != '')
        OR status IN ('QUEUED', 'UNDER_REVIEW', 'REJECTED_FALSE_POSITIVE')
    )
);

CREATE TABLE IF NOT EXISTS evidence_certificates (
    certificate_id TEXT PRIMARY KEY,
    device_identification TEXT NOT NULL,
    production_process_description TEXT NOT NULL,
    certifying_officer TEXT NOT NULL DEFAULT 'SYSTEM-GENERATED',
    generated_at TEXT NOT NULL,
    integrity_hash TEXT NOT NULL CHECK (length(integrity_hash) = 64)
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL CHECK (evidence_type IN ('PACKAGE_PHOTO', 'CALIBRATION_FRAME', 'ANNOTATED_OVERLAY')),
    file_path TEXT NOT NULL,
    sha256_hash TEXT NOT NULL CHECK (length(sha256_hash) = 64),
    capture_timestamp TEXT NOT NULL,
    captured_by TEXT NOT NULL,
    bsa_s63_certificate_id TEXT REFERENCES evidence_certificates(certificate_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id TEXT PRIMARY KEY,
    case_id TEXT REFERENCES cases(case_id) ON DELETE SET NULL,
    actor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL CHECK (length(entry_hash) = 64)
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    conn.commit()


def connect(db_path: str | Path) -> sqlite3.Connection:
    # check_same_thread=False: a single request's connection is opened and
    # closed within one FastAPI dependency scope, but ASGI test clients (and
    # some ASGI servers) dispatch that scope onto a worker thread different
    # from the one that will eventually garbage-collect/close it. There is
    # never concurrent multi-thread access to the same connection object.
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    ensure_schema(conn)
    return conn


def connect_memory() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    ensure_schema(conn)
    return conn
