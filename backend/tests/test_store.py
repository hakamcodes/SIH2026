"""Store layer: Firestore-backed scan/case persistence, the reason-to-believe
hard gate (CLAUDE.md invariant 12), and the hash-chained audit log.

Runs against tests.fakes.fake_firestore.FakeFirestoreClient rather than a
live Firestore project or the Firestore emulator -- this machine has neither
a service account nor a JRE to run the emulator (CLAUDE.md section 2). The
fake implements the exact subset of the Firestore client API repository.py
and audit.py call, so these tests exercise the real query shapes.
"""
from pathlib import Path

import pytest
from lmd.engine.engine import RuleEngine
from lmd.engine.loader import load_rules
from lmd.store import audit, repository
from lmd.store.models import CaseStatus
from lmd.store.repository import ReasonToBelieveRequired

from .fakes.fake_firestore import FakeFirestoreClient
from .fixtures.compliance_test_cases import TEST_CASES

RULES_PATH = Path(__file__).resolve().parents[2] / "packages" / "rules" / "lmd_rules.v1.json"


@pytest.fixture
def conn():
    return FakeFirestoreClient()


@pytest.fixture(scope="module")
def engine():
    return RuleEngine(load_rules(RULES_PATH))


def _make_scan(conn, engine):
    case = TEST_CASES[0]
    scan_date = case.get("scan_date", "2026-09-06")
    result = engine.evaluate(case["input_data"], scan_date=scan_date)
    return repository.create_scan(
        conn,
        scan_date=scan_date,
        scan_source="package_image",
        ruleset_version="v1",
        result=result,
        extraction_envelope=case["input_data"],
        images_base64={},
    )


def test_create_and_get_scan_round_trips_rule_results(conn, engine):
    scan_id = _make_scan(conn, engine)
    scan = repository.get_scan(conn, scan_id)
    assert scan is not None
    assert scan["overall_verdict"] in {"COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW"}
    assert len(scan["rule_results"]) > 0
    assert scan["extraction_envelope"] == TEST_CASES[0]["input_data"]


def test_case_created_in_queued_status(conn, engine):
    scan_id = _make_scan(conn, engine)
    case_id = repository.create_case(conn, scan_id, actor_id="inspector-1")
    case = repository.get_case(conn, case_id)
    assert case["status"] == CaseStatus.QUEUED.value
    assert case["reason_to_believe_note"] is None


def test_confirming_violation_without_note_is_rejected(conn, engine):
    scan_id = _make_scan(conn, engine)
    case_id = repository.create_case(conn, scan_id, actor_id="inspector-1")
    with pytest.raises(ReasonToBelieveRequired):
        repository.update_case_status(
            conn, case_id, CaseStatus.CONFIRMED_VIOLATION, actor_id="inspector-1"
        )
    # confirm no partial write happened
    case = repository.get_case(conn, case_id)
    assert case["status"] == CaseStatus.QUEUED.value


def test_confirming_violation_with_note_succeeds(conn, engine):
    scan_id = _make_scan(conn, engine)
    case_id = repository.create_case(conn, scan_id, actor_id="inspector-1")
    case = repository.update_case_status(
        conn,
        case_id,
        CaseStatus.CONFIRMED_VIOLATION,
        actor_id="inspector-1",
        reason_to_believe_note="Physical label confirms missing country of origin. Section 15(4) recorded.",
    )
    assert case["status"] == CaseStatus.CONFIRMED_VIOLATION.value
    assert case["verified_at"] is not None


def test_audit_log_chain_verifies(conn, engine):
    scan_id = _make_scan(conn, engine)
    case_id = repository.create_case(conn, scan_id, actor_id="inspector-1")
    repository.update_case_status(
        conn, case_id, CaseStatus.UNDER_REVIEW, actor_id="inspector-1"
    )
    repository.update_case_status(
        conn,
        case_id,
        CaseStatus.CLOSED,
        actor_id="inspector-1",
        reason_to_believe_note="Confirmed and closed after review.",
    )
    assert audit.verify(conn) is True


def test_audit_log_tamper_detected(conn, engine):
    scan_id = _make_scan(conn, engine)
    case_id = repository.create_case(conn, scan_id, actor_id="inspector-1")
    for entry in conn.collection("audit_log").where("case_id", "==", case_id).stream():
        conn.collection("audit_log").document(entry.id).update({"action": "TAMPERED"})
    assert audit.verify(conn) is False


def test_dashboard_counters_reflect_scans_and_cases(conn, engine):
    scan_id = _make_scan(conn, engine)
    repository.create_case(conn, scan_id, actor_id="inspector-1")
    counters = repository.dashboard_counters(conn)
    assert counters["total_scans"] == 1
    assert sum(counters["cases_by_status"].values()) == 1
