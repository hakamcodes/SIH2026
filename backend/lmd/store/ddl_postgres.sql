-- Production (Postgres) target schema. Semantically identical to the sqlite
-- schema in db.py -- same tables, same columns, same CHECK constraints.
-- This file is NOT executed by this prototype (no Postgres server on this
-- machine, CLAUDE.md section 2); it documents the deployment target.
--
-- Deliberately narrower than research/NotebookLM/database-api-data-model.md's
-- proposed schema: that document models a multi-state e-commerce crawler
-- platform (sellers_manufacturers with GSTIN lookup, platforms, listings,
-- notices, orders_penalties). Per CLAUDE.md section 1, marketplace scraping,
-- notice dispatch, and eMaap cross-state lookup are roadmap-only with zero
-- code, so those tables are not defined here. Only the in-scope vertical
-- slice is modeled: an inspector-captured scan -> a case -> its evidence
-- chain -> the reason-to-believe-gated review workflow.
--
-- Severity/status/verdict vocabulary is CLAUDE.md section 4.3's canonical
-- set, not the research doc's Low/Medium/High/Critical variant.

CREATE TYPE verdict_enum AS ENUM ('COMPLIANT', 'NON_COMPLIANT', 'NEEDS_REVIEW');
CREATE TYPE severity_enum AS ENUM ('BLOCKER', 'MAJOR', 'MINOR', 'DIAGNOSTIC');
CREATE TYPE rule_status_enum AS ENUM ('PASS', 'FAIL', 'REVIEW', 'NOT_APPLICABLE', 'NOT_IN_FORCE', 'NOT_EVALUABLE');
CREATE TYPE case_status_enum AS ENUM (
    'QUEUED', 'UNDER_REVIEW', 'CONFIRMED_VIOLATION', 'REJECTED_FALSE_POSITIVE', 'ESCALATED', 'CLOSED'
);
CREATE TYPE evidence_type_enum AS ENUM ('PACKAGE_PHOTO', 'CALIBRATION_FRAME', 'ANNOTATED_OVERLAY');

CREATE TABLE inspectors (
    inspector_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    designation TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE scans (
    scan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_date DATE NOT NULL,
    scan_source TEXT NOT NULL,
    ruleset_version TEXT NOT NULL,
    overall_verdict verdict_enum NOT NULL,
    extraction_envelope_json JSONB NOT NULL,
    image_paths_json JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE rule_results (
    scan_id UUID NOT NULL REFERENCES scans(scan_id) ON DELETE CASCADE,
    rule_id VARCHAR(20) NOT NULL,
    category TEXT NOT NULL,
    severity severity_enum NOT NULL,
    status rule_status_enum NOT NULL,
    on_fail_code TEXT,
    message TEXT NOT NULL,
    legal_basis TEXT NOT NULL,
    citation_verified BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (scan_id, rule_id)
);

CREATE TABLE cases (
    case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(scan_id) ON DELETE RESTRICT,
    status case_status_enum NOT NULL DEFAULT 'QUEUED',
    assigned_inspector_id UUID REFERENCES inspectors(inspector_id) ON DELETE SET NULL,
    reason_to_believe_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    verified_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    -- CLAUDE.md invariant 12: the reason-to-believe gate is a hard gate,
    -- enforced in the database CHECK constraint *and* the API.
    CONSTRAINT chk_verified_reason CHECK (
        (status IN ('CONFIRMED_VIOLATION', 'ESCALATED', 'CLOSED')
            AND reason_to_believe_note IS NOT NULL AND reason_to_believe_note != '')
        OR status IN ('QUEUED', 'UNDER_REVIEW', 'REJECTED_FALSE_POSITIVE')
    )
);

CREATE TABLE evidence_certificates (
    certificate_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_identification TEXT NOT NULL,
    production_process_description TEXT NOT NULL,
    certifying_officer TEXT NOT NULL DEFAULT 'SYSTEM-GENERATED',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    integrity_hash CHAR(64) NOT NULL
);

CREATE TABLE evidence (
    evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    evidence_type evidence_type_enum NOT NULL,
    file_path TEXT NOT NULL,
    sha256_hash CHAR(64) NOT NULL,
    capture_timestamp TIMESTAMPTZ NOT NULL,
    captured_by TEXT NOT NULL,
    bsa_s63_certificate_id UUID REFERENCES evidence_certificates(certificate_id) ON DELETE SET NULL
);

-- Immutable (application-enforced: never UPDATE or DELETE a row). The
-- prev_hash/entry_hash pair forms a tamper-evident chain -- see
-- lmd.evidence.hashing.chain_next / lmd.store.audit.
CREATE TABLE audit_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(case_id) ON DELETE SET NULL,
    actor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    prev_hash CHAR(64) NOT NULL,
    entry_hash CHAR(64) NOT NULL
);
