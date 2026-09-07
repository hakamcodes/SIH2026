"""CLI smoke tests for `scan` and `report` -- these used to refuse loudly
(cv/ and evidence/ were out of scope); now they must actually work.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_IMG_PATH = _BACKEND_ROOT.parent / "research" / "mainResearch" / "02_flat_box_clean.jpg"

pytestmark = pytest.mark.slow


def test_cli_scan_produces_json_verdict():
    result = subprocess.run(
        [
            sys.executable, "-m", "lmd.cli", "scan", str(_IMG_PATH), "--json",
            "--commodity-category", "personal_care", "--commodity-subtype", "toothpaste",
        ],
        cwd=str(_BACKEND_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["overall_verdict"] in {"COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW"}


def test_cli_scan_without_image_path_exits_with_usage_error():
    result = subprocess.run(
        [sys.executable, "-m", "lmd.cli", "scan"],
        cwd=str(_BACKEND_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "usage" in result.stderr.lower() or "usage" in result.stdout.lower()
