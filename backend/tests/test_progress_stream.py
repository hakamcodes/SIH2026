"""NDJSON stage-progress streaming (lmd.api.progress). A caller opts in with
Accept: application/x-ndjson; anything else must still get the pre-streaming
plain JSON body, byte-for-byte, which is what keeps test_api_smoke.py and
lmd.cli working with zero changes.
"""
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from .fakes.fake_firestore import FakeFirestoreClient

os.environ.setdefault("LMD_INSPECTOR_API_TOKEN", "test-token")

_IMG_PATH = Path(__file__).resolve().parents[2] / "research" / "mainResearch" / "02_flat_box_clean.jpg"

pytestmark = pytest.mark.slow


@pytest.fixture
def client():
    from lmd.api.deps import get_db
    from lmd.api.main import app

    fake_client = FakeFirestoreClient()
    app.dependency_overrides[get_db] = lambda: fake_client
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _read_ndjson_lines(client, method, url, **kwargs):
    events = []
    with client.stream(method, url, **kwargs) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/x-ndjson")
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            events.append(json.loads(raw_line))
    return events


def test_single_scan_stream_reaches_total_and_ends_in_result(client):
    with _IMG_PATH.open("rb") as f:
        events = _read_ndjson_lines(
            client,
            "POST",
            "/api/v1/scans",
            headers={"Accept": "application/x-ndjson"},
            files={"image": ("box.jpg", f, "image/jpeg")},
            data={"scan_source": "package_image"},
        )

    stage_events = [e for e in events if e["event"] == "stage"]
    assert stage_events, "expected at least one stage event"

    total = stage_events[0]["total"]
    assert total == 12  # decode, barcode, calibration, glare, ocr, roi_retry,
    # vision, reconcile, rules, overlay, compress, persist
    assert [e["index"] for e in stage_events] == list(range(1, len(stage_events) + 1))
    assert stage_events[-1]["index"] == total

    stage_keys = [e["stage"] for e in stage_events]
    assert stage_keys == [
        "decode", "barcode", "calibration", "glare", "ocr", "roi_retry",
        "vision", "reconcile", "rules", "overlay", "compress", "persist",
    ]

    assert events[-1]["event"] == "result"
    assert events[-1]["overall_verdict"] in {"COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW"}
    assert "scan_id" in events[-1]


def test_single_scan_plain_json_unchanged_when_not_requesting_ndjson(client):
    with _IMG_PATH.open("rb") as f:
        resp = client.post(
            "/api/v1/scans",
            files={"image": ("box.jpg", f, "image/jpeg")},
            data={"scan_source": "package_image"},
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    body = resp.json()
    assert body["overall_verdict"] in {"COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW"}
    assert "scan_id" in body


def test_undecodable_image_becomes_error_event_on_stream(client):
    events = _read_ndjson_lines(
        client,
        "POST",
        "/api/v1/scans",
        headers={"Accept": "application/x-ndjson"},
        files={"image": ("not-an-image.jpg", b"not actually an image", "image/jpeg")},
        data={"scan_source": "package_image"},
    )
    assert events[-1] == {
        "event": "error",
        "status": 400,
        "detail": "uploaded file is not a decodable image",
    }
    # a 200 was already committed for the stream itself -- the failure must
    # be signalled in-band, never as a hung or truncated connection
    assert not any(e["event"] == "result" for e in events)


def test_undecodable_image_still_400_when_not_streaming(client):
    resp = client.post(
        "/api/v1/scans",
        files={"image": ("not-an-image.jpg", b"not actually an image", "image/jpeg")},
        data={"scan_source": "package_image"},
    )
    assert resp.status_code == 400


def test_multi_scan_stream_reaches_total_and_covers_all_panels(client):
    with _IMG_PATH.open("rb") as front, _IMG_PATH.open("rb") as back:
        events = _read_ndjson_lines(
            client,
            "POST",
            "/api/v1/scans/multi",
            headers={"Accept": "application/x-ndjson"},
            files={
                "image_front": ("front.jpg", front, "image/jpeg"),
                "image_back": ("back.jpg", back, "image/jpeg"),
            },
        )

    stage_events = [e for e in events if e["event"] == "stage"]
    total = stage_events[0]["total"]
    assert total == 9 + 7 + 4  # front panel (9) + back panel (7) + shared (4)
    assert stage_events[-1]["index"] == total

    panels_seen = {e["panel"] for e in stage_events if "panel" in e}
    assert panels_seen == {"front", "back"}

    panel_done_events = [e for e in events if e["event"] == "panel_done"]
    assert {e["panel"] for e in panel_done_events} == {"front", "back"}

    assert events[-1]["event"] == "result"
    assert events[-1]["panels_processed"] == ["front", "back"]


def test_multi_scan_too_many_panels_rejected_before_stream_opens(client):
    with _IMG_PATH.open("rb") as f:
        data = f.read()
    from lmd import config

    files = {
        f"image_{slot}": (f"{slot}.jpg", data, "image/jpeg")
        for slot in ["front", "back", "side", "other"]
    }
    # LMD_MAX_PANELS defaults to 4, so this must already be rejected once we
    # pretend the cap is lower -- confirms the check runs before any stream
    # or pipeline work starts (a real 400, not an in-band error event).
    original = config.LMD_MAX_PANELS
    config.LMD_MAX_PANELS = 1
    try:
        resp = client.post(
            "/api/v1/scans/multi",
            headers={"Accept": "application/x-ndjson"},
            files=files,
        )
    finally:
        config.LMD_MAX_PANELS = original
    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
