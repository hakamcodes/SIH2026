"""PDF report generation: must produce a real, parseable PDF (not a stub),
and the certificate-alongside-report hash must actually match the PDF bytes.
"""
from pathlib import Path

from lmd.engine.engine import RuleEngine
from lmd.engine.loader import load_rules
from lmd.evidence import bsa63, hashing, report_pdf
from lmd.store import repository
from lmd.store.models import CaseStatus

from .fakes.fake_firestore import FakeFirestoreClient
from .fixtures.compliance_test_cases import TEST_CASES

RULES_PATH = Path(__file__).resolve().parents[2] / "packages" / "rules" / "lmd_rules.v1.json"


def test_generate_report_produces_valid_pdf_bytes():
    engine = RuleEngine(load_rules(RULES_PATH))
    conn = FakeFirestoreClient()
    case_data = TEST_CASES[0]
    scan_date = case_data.get("scan_date", "2026-09-06")
    result = engine.evaluate(case_data["input_data"], scan_date=scan_date)
    scan_id = repository.create_scan(
        conn, scan_date, "package_image", "v1", result, case_data["input_data"], images_base64={}
    )
    case_id = repository.create_case(conn, scan_id, actor_id="inspector-1")
    repository.update_case_status(
        conn, case_id, CaseStatus.CONFIRMED_VIOLATION, actor_id="inspector-1",
        reason_to_believe_note="Confirmed missing declarations on physical inspection.",
    )

    scan = repository.get_scan(conn, scan_id)
    case = repository.get_case(conn, case_id)
    evidence_list = repository.list_evidence(conn, case_id)

    pdf_bytes = report_pdf.generate_report(case, scan, evidence_list, inspector={"name": "A. Officer", "inspector_id": "insp-1"})

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000

    doc_hash = hashing.sha256_bytes(pdf_bytes)
    cert = bsa63.generate_certificate(
        device_identification="test-harness",
        production_process_description="pytest-generated report",
        record_sha256=doc_hash,
    )
    assert bsa63.verify_certificate(cert) is True
    assert cert.record_sha256 == doc_hash
