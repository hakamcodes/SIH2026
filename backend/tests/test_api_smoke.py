"""End-to-end API smoke test: upload a real research image, get a scan
verdict, open a case, hit the reason-to-believe gate, confirm it properly,
attach evidence, and generate a certified report. No mocked steps -- this
exercises the real pipeline_a + rule engine + sqlite store + PDF generation.
"""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("LMD_INSPECTOR_API_TOKEN", "test-token")

_IMG_PATH = Path(__file__).resolve().parents[2] / "research" / "mainResearch" / "02_flat_box_clean.jpg"

AUTH_HEADERS = {"Authorization": "Bearer test-token", "X-Inspector-Id": "inspector-1"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    from lmd import config

    monkeypatch.setattr(config, "DB_PATH", tmp_path / "lmd.db")
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")

    from lmd.api import scan as scan_module
    from lmd.api import cases as cases_module
    from lmd.api import reports as reports_module

    monkeypatch.setattr(scan_module, "config", config)
    monkeypatch.setattr(cases_module, "config", config)
    monkeypatch.setattr(reports_module, "config", config)

    from lmd.api.main import app

    return TestClient(app)


pytestmark = pytest.mark.slow


def test_full_scan_to_report_flow(client):
    with _IMG_PATH.open("rb") as f:
        resp = client.post(
            "/api/v1/scans",
            files={"image": ("box.jpg", f, "image/jpeg")},
            data={
                "scan_source": "package_image",
                "commodity_category": "personal_care",
                "commodity_subtype": "toothpaste",
                "commodity_is_imported": "false",
                "commodity_is_exempt": "false",
            },
        )
    assert resp.status_code == 200, resp.text
    scan_body = resp.json()
    assert scan_body["overall_verdict"] in {"COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW"}
    scan_id = scan_body["scan_id"]

    resp = client.post("/api/v1/cases", json={"scan_id": scan_id}, headers=AUTH_HEADERS)
    assert resp.status_code == 200, resp.text
    case_id = resp.json()["case_id"]
    assert resp.json()["status"] == "QUEUED"

    # Hard gate: confirming without a reason-to-believe note must 422.
    resp = client.put(
        f"/api/v1/cases/{case_id}",
        json={"status": "CONFIRMED_VIOLATION"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 422
    assert "Section 15(4)" in resp.json()["legal_basis"]

    resp = client.put(
        f"/api/v1/cases/{case_id}",
        json={"status": "CONFIRMED_VIOLATION", "reason_to_believe_note": "Physical inspection confirms missing declarations."},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CONFIRMED_VIOLATION"

    resp = client.get("/api/v1/rules")
    assert resp.status_code == 200
    assert resp.json()["rule_count"] > 20

    resp = client.post(f"/api/v1/cases/{case_id}/report", headers=AUTH_HEADERS)
    assert resp.status_code == 200, resp.text
    cert = resp.json()["certificate"]
    assert len(cert["record_sha256"]) == 64

    resp = client.get(f"/api/v1/cases/{case_id}/report")
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF-")

    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    assert resp.json()["total_scans"] == 1


def test_unauthenticated_case_update_is_rejected(client):
    resp = client.put("/api/v1/cases/nonexistent", json={"status": "QUEUED"})
    assert resp.status_code == 401
