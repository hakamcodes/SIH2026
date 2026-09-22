"""Persistence-layer dataclasses. Deliberately narrower than the schema in
research/NotebookLM/database-api-data-model.md -- that document models a
multi-state e-commerce crawler platform (sellers_manufacturers, platforms,
listings, GSTIN lookup, notices, orders_penalties). Per CLAUDE.md section 1,
marketplace scraping, notice dispatch, and eMaap integration are roadmap-only
with zero code. Only the in-scope vertical slice is persisted here: a case
opened from a single inspector-captured scan, its evidence chain, and the
reason-to-believe-gated review workflow.

Severity/status/verdict vocabulary is the CLAUDE.md section 4.3 canonical set
(lmd.engine.models), not the research doc's Low/Medium/High/Critical variant.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CaseStatus(str, Enum):
    QUEUED = "QUEUED"
    UNDER_REVIEW = "UNDER_REVIEW"
    CONFIRMED_VIOLATION = "CONFIRMED_VIOLATION"
    REJECTED_FALSE_POSITIVE = "REJECTED_FALSE_POSITIVE"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


# Per CLAUDE.md invariant 12: advancing into any of these statuses without a
# recorded reason_to_believe_note is a hard gate violation (422, Section 15(4)).
REASON_TO_BELIEVE_GATED_STATUSES = frozenset(
    {CaseStatus.CONFIRMED_VIOLATION, CaseStatus.ESCALATED, CaseStatus.CLOSED}
)


class EvidenceType(str, Enum):
    PACKAGE_PHOTO = "PACKAGE_PHOTO"
    CALIBRATION_FRAME = "CALIBRATION_FRAME"
    ANNOTATED_OVERLAY = "ANNOTATED_OVERLAY"


@dataclass
class Inspector:
    inspector_id: str
    name: str
    designation: str
    active: bool = True


@dataclass
class Scan:
    scan_id: str
    scan_date: str
    scan_source: str
    ruleset_version: str
    overall_verdict: str
    extraction_envelope: dict = field(default_factory=dict)
    images_base64: dict[str, str] = field(default_factory=dict)
    created_at: str = ""
    panel_sources: dict[str, str] = field(default_factory=dict)


@dataclass
class RuleResultRow:
    scan_id: str
    rule_id: str
    category: str
    severity: str
    status: str
    on_fail_code: str | None
    message: str
    legal_basis: str
    citation_verified: bool


@dataclass
class Case:
    case_id: str
    scan_id: str
    status: CaseStatus
    created_at: str
    assigned_inspector_id: str | None = None
    reason_to_believe_note: str | None = None
    verified_at: str | None = None
    closed_at: str | None = None


@dataclass
class EvidenceCertificate:
    certificate_id: str
    device_identification: str
    production_process_description: str
    certifying_officer: str
    generated_at: str
    integrity_hash: str


@dataclass
class Evidence:
    evidence_id: str
    case_id: str
    evidence_type: EvidenceType
    file_base64: str
    sha256_hash: str
    capture_timestamp: str
    captured_by: str
    bsa_s63_certificate_id: str | None = None


@dataclass
class AuditLogEntry:
    log_id: str
    case_id: str | None
    actor_id: str
    action: str
    timestamp: str
    prev_hash: str
    entry_hash: str
