"""CLI entry point: evaluate a fixture, scan a real image end-to-end, or
generate a violation report PDF for a case already in the sqlite store."""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_ROOT.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from lmd.engine.engine import RuleEngine
from lmd.engine.loader import load_rules

DEFAULT_RULES_PATH = _REPO_ROOT / "packages" / "rules" / "lmd_rules.v1.json"


def _load_test_case(case_id: str) -> dict:
    sys.path.insert(0, str(_BACKEND_ROOT / "tests"))
    from fixtures.compliance_test_cases import (
        TEST_CASES,
    )

    for case in TEST_CASES:
        if case["test_case_id"] == case_id:
            return case
    known = ", ".join(c["test_case_id"] for c in TEST_CASES)
    raise SystemExit(f"unknown test case {case_id!r}. Known cases: {known}")


def cmd_evaluate(args: argparse.Namespace) -> None:
    case = _load_test_case(args.case)
    scan_date = args.as_of or case.get("scan_date", "2026-09-06")

    engine = RuleEngine(load_rules(args.rules or DEFAULT_RULES_PATH))
    result = engine.evaluate(case["input_data"], scan_date=scan_date)

    output = {
        "test_case_id": case["test_case_id"],
        "scenario_name": case["scenario_name"],
        "scan_date": scan_date,
        "overall_verdict": result.overall_verdict.value,
        "failed_rules": result.failed_rule_ids,
        "review_rules": result.review_rule_ids,
        "diagnostic_rules": result.diagnostic_rule_ids,
        "applicable_count": result.applicable_count,
        "rule_results": {
            rid: {
                "status": r.status.value,
                "severity": r.severity.value,
                "category": r.category,
                "on_fail_code": r.on_fail_code,
                "message": r.message,
                "legal_basis": r.legal_basis,
            }
            for rid, r in result.rule_results.items()
        },
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


def cmd_scan(args: argparse.Namespace) -> None:
    if not args.image_path:
        raise SystemExit("usage: lmd scan IMAGE_PATH [--json] [--commodity-category X] [--as-of YYYY-MM-DD]")

    import cv2

    from lmd import config
    from lmd.cv.pipeline_a import run_pipeline_a
    from lmd.cv.reconcile import reconcile

    image = cv2.imread(args.image_path)
    if image is None:
        raise SystemExit(f"could not decode image: {args.image_path}")

    pipeline_a_result = run_pipeline_a(image)

    vision_fields: dict = {}
    if args.use_vision:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("--use-vision requires ANTHROPIC_API_KEY to be set (see .env.example).")
        from lmd.cv.pipeline_b import extract_with_vision

        vision_fields = extract_with_vision(Path(args.image_path).read_bytes())

    envelope = reconcile(pipeline_a_result, vision_fields, scan_source="package_image")
    envelope["commodity"] = {
        "category": args.commodity_category,
        "subtype": args.commodity_subtype,
        "is_imported": args.commodity_is_imported,
        "is_exempt": args.commodity_is_exempt,
    }

    scan_date = args.as_of or datetime.date.today().isoformat()
    engine = RuleEngine(load_rules(args.rules or config.RULES_PATH))
    result = engine.evaluate(envelope, scan_date=scan_date)

    output = {
        "image_path": args.image_path,
        "scan_date": scan_date,
        "overall_verdict": result.overall_verdict.value,
        "extraction_envelope": envelope,
        "failed_rules": result.failed_rule_ids,
        "review_rules": result.review_rule_ids,
        "diagnostic_rules": result.diagnostic_rule_ids,
        "rule_results": {
            rid: {"status": r.status.value, "severity": r.severity.value, "message": r.message}
            for rid, r in result.rule_results.items()
        },
    }
    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"Verdict: {output['overall_verdict']}")
        print(f"Failed rules: {output['failed_rules']}")
        print(f"Review rules: {output['review_rules']}")


def cmd_report(args: argparse.Namespace) -> None:
    if not args.case:
        raise SystemExit("usage: lmd report --case CASE_ID")

    from lmd import config
    from lmd.evidence import report_pdf
    from lmd.evidence.bsa63 import generate_certificate
    from lmd.evidence.hashing import sha256_bytes
    from lmd.store import db, repository

    conn = db.connect(config.DB_PATH)
    try:
        case = repository.get_case(conn, args.case)
        if case is None:
            raise SystemExit(f"case not found: {args.case}")
        scan = repository.get_scan(conn, case["scan_id"])
        evidence_list = repository.list_evidence(conn, args.case)

        pdf_bytes = report_pdf.generate_report(case, scan, evidence_list, inspector=None)
        doc_hash = sha256_bytes(pdf_bytes)
        cert = generate_certificate(
            device_identification="lmd-cli",
            production_process_description="lmd report --case (CLI-generated)",
            record_sha256=doc_hash,
        )
        repository.insert_certificate(conn, cert)

        out_path = _REPO_ROOT / "data" / "uploads" / "reports" / f"{args.case}.pdf"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(pdf_bytes)
        print(f"Report written to {out_path}")
        print(f"Document SHA-256: {doc_hash}")
        print(f"Certificate ID: {cert.certificate_id}")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="lmd", description="Legal Metrology compliance engine CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_evaluate = subparsers.add_parser("evaluate", help="Evaluate a fixture test case through the rule engine")
    p_evaluate.add_argument("--case", required=True, help="Test case ID, e.g. TC-002")
    p_evaluate.add_argument("--as-of", default=None, help="Override scan date (YYYY-MM-DD) for point-in-time evaluation")
    p_evaluate.add_argument("--rules", default=None, help="Path to rules JSON (default: packages/rules/lmd_rules.v1.json)")
    p_evaluate.set_defaults(func=cmd_evaluate)

    p_scan = subparsers.add_parser("scan", help="Run the CV/OCR pipeline on an image and evaluate it")
    p_scan.add_argument("image_path", nargs="?")
    p_scan.add_argument("--json", action="store_true")
    p_scan.add_argument("--as-of", default=None, help="Override scan date (YYYY-MM-DD)")
    p_scan.add_argument("--rules", default=None, help="Path to rules JSON (default: packages/rules/lmd_rules.v1.json)")
    p_scan.add_argument("--use-vision", action="store_true", help="Also run pipeline B (requires ANTHROPIC_API_KEY)")
    p_scan.add_argument("--commodity-category", default=None)
    p_scan.add_argument("--commodity-subtype", default=None)
    p_scan.add_argument("--commodity-is-imported", action="store_true")
    p_scan.add_argument("--commodity-is-exempt", action="store_true")
    p_scan.set_defaults(func=cmd_scan)

    p_report = subparsers.add_parser("report", help="Generate a violation report PDF for a case in the sqlite store")
    p_report.add_argument("--case", required=False)
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
