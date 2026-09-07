"""Ported from research/NotebookLM/compliance-test-cases.json.

Per CLAUDE.md section 8: comparing the reference engine's real overall_verdict
(not just expected_triggered_rules membership) against expected_verdict surfaces
six self-contradictory fixtures, not four -- TC-001, TC-006, TC-009 and TC-013
claim COMPLIANT/expected but omit mandatory declarations, and TC-011/TC-015
claim NEEDS_REVIEW but omit mandatory declarations too. That second pair only
surfaces once verdict precedence is fixed (CLAUDE.md defect #8: NON_COMPLIANT
must outrank NEEDS_REVIEW), which is exactly what this engine does -- under the
original buggy engine the missing-field BLOCKER fails were masked by the
review flag, so the mismatch never showed up in the "18/22" count.

Each of those six is completed here (mandatory fields added, `_fixture_notes`
records what and why) and ALSO kept as a stripped TC-M0xx minimal-field
fixture with expected_verdict corrected to NON_COMPLIANT, so both directions
are covered per CLAUDE.md's test-discipline rules.
"""

DEFAULT_SCAN_DATE = "2026-09-06"

TEST_CASES = [
    {
        "test_case_id": "TC-001",
        "scenario_name": "Standard Compliant Biscuit Pack (Standard Size)",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "food", "subtype": "biscuits", "is_imported": False, "is_exempt": False},
            "net_quantity": {"value": 500.0, "unit": "g"},
            "mrp": {"value": 100.0, "currency_marker": "₹", "raw_text": "MRP Rs. 100.00 incl. of all taxes"},
            "usp_declared": 0.2,
            "mfg_date": "2026-08-01",
            "best_before_date": "2027-02-01",
            "manufacturer_or_packer_or_importer": {
                "name": "Suryoday Foods Pvt. Ltd.",
                "address": "Plot 42, Hinjewadi Phase 3, Pune, MH, 411057",
            },
            "common_or_generic_name": "Masala Biscuits",
            "brand_name": "Suryoday Premium",
            "consumer_care": {"phone": "+91-20-12345678", "email": "care@suryodayfoods.com"},
        },
        "expected_verdict": "COMPLIANT",
        "_fixture_notes": "Added best_before_date -- food category requires it under Rule 6(1)(da) (LM-C08). Original omitted it while claiming COMPLIANT.",
    },
    {
        "test_case_id": "TC-M001",
        "scenario_name": "Standard Compliant Biscuit Pack -- stripped (minimal-field class)",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "food", "subtype": "biscuits", "is_imported": False, "is_exempt": False},
            "net_quantity": {"value": 500.0, "unit": "g"},
            "mrp": {"value": 100.0, "currency_marker": "₹", "raw_text": "MRP Rs. 100.00 incl. of all taxes"},
            "usp_declared": 0.2,
            "mfg_date": "2026-08-01",
            "manufacturer_or_packer_or_importer": {
                "name": "Suryoday Foods Pvt. Ltd.",
                "address": "Plot 42, Hinjewadi Phase 3, Pune, MH, 411057",
            },
            "common_or_generic_name": "Masala Biscuits",
            "brand_name": "Suryoday Premium",
            "consumer_care": {"phone": "+91-20-12345678", "email": "care@suryodayfoods.com"},
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-002",
        "scenario_name": "Missing Maximum Retail Price (MRP)",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "food", "subtype": "biscuits", "is_imported": False, "is_exempt": False},
            "net_quantity": {"value": 500.0, "unit": "g"},
            "mfg_date": "2026-08-01",
            "manufacturer_or_packer_or_importer": {"name": "Suryoday Foods Pvt. Ltd.", "address": "Pune, MH, 411057"},
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-003",
        "scenario_name": "Missing Net Quantity",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "food", "subtype": "biscuits", "is_imported": False, "is_exempt": False},
            "mrp": {"value": 100.0, "currency_marker": "₹", "raw_text": "MRP Rs. 100.00 incl."},
            "mfg_date": "2026-08-01",
            "manufacturer_or_packer_or_importer": {"name": "Suryoday Foods Pvt. Ltd.", "address": "Pune, MH, 411057"},
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-004",
        "scenario_name": "Non-Standard Net Quantity Unit",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "food", "subtype": "biscuits", "is_imported": False, "is_exempt": False},
            "net_quantity": {"value": 1.1, "unit": "lbs"},
            "mrp": {"value": 100.0, "currency_marker": "₹", "raw_text": "MRP Rs. 100.00 incl. of all taxes"},
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-005",
        "scenario_name": "Unit Sale Price (USP) Mathematical Mismatch",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "food", "subtype": "biscuits", "is_imported": False, "is_exempt": False},
            "net_quantity": {"value": 250.0, "unit": "g"},
            "mrp": {"value": 50.0, "currency_marker": "₹", "raw_text": "MRP Rs. 50.00 incl."},
            "usp_declared": 0.25,
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-006",
        "scenario_name": "Correct MRP Price Rounding (Down)",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "hardware", "subtype": "fastener", "is_imported": False, "is_exempt": False},
            "net_quantity": {"value": 200.0, "unit": "g"},
            "mrp": {"value": 47.0, "computed_value": 47.3, "currency_marker": "₹", "raw_text": "MRP Rs. 47.00 incl. of all taxes"},
            "mfg_date": "2026-08-01",
            "manufacturer_or_packer_or_importer": {"name": "Acme Hardware", "address": "Nashik, MH"},
            "common_or_generic_name": "Steel Bolts",
            "brand_name": "Acme Fasteners",
            "consumer_care": {"phone": "+919876543210"},
        },
        "expected_verdict": "COMPLIANT",
        "_fixture_notes": "Added net_quantity, manufacturer, common_name, consumer_care, mfg_date -- all mandatory. Original had only the mrp block while claiming COMPLIANT. Category chosen as 'hardware' (not food/textile) to avoid pulling in best-before/dimension requirements unrelated to the MRP-rounding scenario under test.",
    },
    {
        "test_case_id": "TC-M006",
        "scenario_name": "Correct MRP Price Rounding -- stripped (minimal-field class)",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "hardware", "subtype": "fastener", "is_imported": False, "is_exempt": False},
            "mrp": {"value": 47.0, "computed_value": 47.3, "currency_marker": "₹"},
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-007",
        "scenario_name": "Invalid MRP Price Rounding",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "food", "subtype": "biscuits", "is_imported": False, "is_exempt": False},
            "mrp": {"value": 48.0, "computed_value": 47.7, "currency_marker": "₹"},
        },
        "expected_verdict": "NON_COMPLIANT",
        "_fixture_notes": "LM-M03 is DIAGNOSTIC severity per CLAUDE.md 4.2 (statutory paise rounding is not real Indian law) so it cannot be the cause of NON_COMPLIANT here -- this scenario is NON_COMPLIANT because the minimal fixture is missing every other mandatory declaration too, same as the other stripped fixtures.",
    },
    {
        "test_case_id": "TC-008",
        "scenario_name": "Multi-MRP Dual Pricing Detected",
        "input_data": {
            "scan_source": "package_image",
            "mrp_candidates": [120.0, 150.0],
            "sticker_detected": False,
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-009",
        "scenario_name": "Valid Stickered MRP Reduction",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "hardware", "subtype": "tool", "is_imported": False, "is_exempt": False},
            "net_quantity": {"value": 1.0, "unit": "pcs"},
            "mrp": {"value": 95.0, "currency_marker": "₹", "raw_text": "MRP Rs. 95.00 incl. of all taxes"},
            "mfg_date": "2026-08-01",
            "manufacturer_or_packer_or_importer": {"name": "Acme Hardware", "address": "Nashik, MH"},
            "common_or_generic_name": "Hand Trowel",
            "brand_name": "Acme Garden",
            "consumer_care": {"phone": "+919876543210"},
            "sticker_detected": True,
            "original_mrp": {"value": 100.0, "is_visible": True},
            "sticker": {"mrp_value": 95.0, "reason": "Festive season discount"},
        },
        "expected_verdict": "COMPLIANT",
        "_fixture_notes": "Added net_quantity, manufacturer, common_name, consumer_care, mfg_date -- all mandatory. Original had only sticker/original_mrp fields while claiming COMPLIANT. mrp.value set equal to the post-sticker price (95), since that's what's currently payable.",
    },
    {
        "test_case_id": "TC-M009",
        "scenario_name": "Valid Stickered MRP Reduction -- stripped (minimal-field class)",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "hardware", "subtype": "tool", "is_imported": False, "is_exempt": False},
            "sticker_detected": True,
            "original_mrp": {"value": 100.0, "is_visible": True},
            "sticker": {"mrp_value": 95.0, "reason": "Festive season discount"},
        },
        "expected_verdict": "NON_COMPLIANT",
        "_fixture_notes": "Added a bare commodity classification (a real CV pipeline always attempts this) so the COMPLETENESS rules' applicable_when gates resolve at all. Missing net_quantity/mrp/manufacturer/etc. then genuinely fail.",
    },
    {
        "test_case_id": "TC-010",
        "scenario_name": "Invalid Stickered MRP Revision (Original Obscured)",
        "input_data": {
            "scan_source": "package_image",
            "sticker_detected": True,
            "original_mrp": {"value": 100.0, "is_visible": False},
            "sticker": {"mrp_value": 105.0, "reason": "GST Revision"},
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-011",
        "scenario_name": "Low OCR Field Confidence",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "hardware", "subtype": "tool", "is_imported": False, "is_exempt": False},
            "net_quantity": {"value": 500.0, "unit": "g"},
            "mrp": {"value": 100.0, "currency_marker": "₹", "raw_text": "MRP Rs. 100.00 incl. of all taxes"},
            "mfg_date": "2026-08-01",
            "manufacturer_or_packer_or_importer": {"name": "Acme Hardware", "address": "Nashik, MH"},
            "common_or_generic_name": "Steel Wire",
            "brand_name": "Acme Industrial",
            "consumer_care": {"phone": "+919876543210"},
            "field_confidences": {"net_quantity": 0.41},
        },
        "expected_verdict": "NEEDS_REVIEW",
        "_fixture_notes": "Added mrp, manufacturer, common_name, consumer_care, mfg_date -- all mandatory. Original had only commodity/net_quantity/field_confidences while claiming NEEDS_REVIEW; under the corrected verdict precedence (CLAUDE.md defect #8: NON_COMPLIANT outranks NEEDS_REVIEW) those missing fields would have produced a masked BLOCKER fail, silently flipping the verdict to NON_COMPLIANT for the wrong reason.",
    },
    {
        "test_case_id": "TC-M011",
        "scenario_name": "Low OCR Field Confidence -- stripped (minimal-field class)",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "hardware", "subtype": "tool", "is_imported": False, "is_exempt": False},
            "net_quantity": {"value": 500.0, "unit": "g"},
            "field_confidences": {"net_quantity": 0.41},
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-012",
        "scenario_name": "Cross-Panel Quantity Mismatch",
        "input_data": {
            "scan_source": "package_image",
            "panel_a": {"net_quantity": {"value": 500.0, "unit": "g"}},
            "panel_b": {"net_quantity": {"value": 0.6, "unit": "kg"}},
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-013",
        "scenario_name": "Valid Imported Product with Origin Displayed",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "electronics", "subtype": "earbuds", "is_imported": True, "is_exempt": False},
            "net_quantity": {"value": 1.0, "unit": "N"},
            "mrp": {"value": 1999.0, "currency_marker": "₹"},
            "country_of_origin": "Vietnam",
            "mfg_date": "2026-08-01",
            "manufacturer_or_packer_or_importer": {"name": "SoundWave Imports Pvt. Ltd.", "address": "Andheri East, Mumbai, MH"},
            "common_or_generic_name": "Wireless Earbuds",
            "brand_name": "SoundWave Pulse",
            "consumer_care": {"phone": "+91-22-98765432", "email": "care@soundwave.example"},
        },
        "expected_verdict": "COMPLIANT",
        "_fixture_notes": "Added manufacturer, common_name, consumer_care, mfg_date -- all mandatory. Original had only commodity/net_quantity/mrp/country_of_origin while claiming COMPLIANT.",
    },
    {
        "test_case_id": "TC-M013",
        "scenario_name": "Valid Imported Product -- stripped (minimal-field class)",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "electronics", "subtype": "earbuds", "is_imported": True, "is_exempt": False},
            "net_quantity": {"value": 1.0, "unit": "N"},
            "mrp": {"value": 1999.0, "currency_marker": "₹"},
            "country_of_origin": "Vietnam",
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-014",
        "scenario_name": "Missing Country of Origin on Imported Product",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "electronics", "subtype": "earbuds", "is_imported": True, "is_exempt": False},
            "net_quantity": {"value": 1.0, "unit": "N"},
            "mrp": {"value": 1999.0, "currency_marker": "₹"},
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-015",
        "scenario_name": "OCR vs. Text-Parse Extractor Disagreement",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "hardware", "subtype": "tool", "is_imported": False, "is_exempt": False},
            "net_quantity": {"value": 500.0, "unit": "g"},
            "mrp": {"value": 100.0, "currency_marker": "₹", "raw_text": "MRP Rs. 100.00 incl. of all taxes"},
            "mfg_date": "2026-08-01",
            "manufacturer_or_packer_or_importer": {"name": "Acme Hardware", "address": "Nashik, MH"},
            "common_or_generic_name": "Steel Wire",
            "brand_name": "Acme Industrial",
            "consumer_care": {"phone": "+919876543210"},
            "ocr_pipeline": {"numeric_val": 299.0},
            "llm_pipeline": {"numeric_val": 290.0},
        },
        "expected_verdict": "NEEDS_REVIEW",
        "_fixture_notes": "Added mrp, manufacturer, common_name, consumer_care, mfg_date, net_quantity -- all mandatory. Same rationale as TC-011: under corrected verdict precedence, missing mandatory fields would mask the intended LM-U02 review signal behind a real BLOCKER fail.",
    },
    {
        "test_case_id": "TC-M015",
        "scenario_name": "OCR vs. Text-Parse Extractor Disagreement -- stripped (minimal-field class)",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "hardware", "subtype": "tool", "is_imported": False, "is_exempt": False},
            "ocr_pipeline": {"numeric_val": 299.0},
            "llm_pipeline": {"numeric_val": 290.0},
        },
        "expected_verdict": "NON_COMPLIANT",
        "_fixture_notes": "Same rationale as TC-M009: added a bare commodity classification so COMPLETENESS rules apply and genuinely fail on the missing mandatory fields, outranking the LM-U02 review per CLAUDE.md invariant #5.",
    },
    {
        "test_case_id": "TC-016",
        "scenario_name": "Perishable Yogurt Cup Missing Expiry Date",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "food", "subtype": "yogurt", "is_imported": False, "is_exempt": False},
            "net_quantity": {"value": 150.0, "unit": "g"},
            "mrp": {"value": 25.0, "currency_marker": "₹", "raw_text": "MRP ₹ 25.00 incl. of all taxes"},
            "mfg_date": "2026-08-01",
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-017",
        "scenario_name": "Packaged Textile Bed-Sheet Missing Dimensions",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "textile", "subtype": "bedsheet", "is_imported": False, "is_exempt": False},
            "net_quantity": {"value": 1.0, "unit": "pcs"},
            "mrp": {"value": 1299.0, "currency_marker": "₹", "raw_text": "MRP ₹ 1299.00 incl. of all taxes"},
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-018",
        "scenario_name": "Non-Standard Biscuit Pack Size Without USP",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "food", "subtype": "biscuits", "is_imported": False, "is_exempt": False},
            "net_quantity": {"value": 120.0, "unit": "g"},
            "mrp": {"value": 30.0, "currency_marker": "₹"},
        },
        "expected_verdict": "NON_COMPLIANT",
        "_fixture_notes": "Now triggers LM-M04a (Rule 5 BLOCKER, unconditional) and LM-M04b (Rule 6(11) USP MAJOR) per the CLAUDE.md 4.2 split, instead of the single legally-wrong LM-M04.",
    },
    {
        "test_case_id": "TC-019",
        "scenario_name": "Stale Ruleset Scan Pre-2011 Act",
        "scan_date": "2010-05-15",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "food", "subtype": "biscuits", "is_imported": False, "is_exempt": False},
            "net_quantity": {"value": 100.0, "unit": "g"},
            "mrp": {"value": 20.0, "currency_marker": "₹"},
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-020",
        "scenario_name": "Invalid Temporal Order (Mfg Date After Best Before)",
        "input_data": {
            "scan_source": "package_image",
            "commodity": {"category": "food", "subtype": "biscuits", "is_imported": False, "is_exempt": False},
            "mfg_date": "2026-09-01",
            "best_before_date": "2026-06-01",
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-021",
        "scenario_name": "Listing vs Package Country of Origin Discrepancy",
        "input_data": {
            "scan_source": "package_image",
            "listing_data": {"net_quantity": "250 g", "country_of_origin": "India", "manufacturer_name": "Suryoday Foods"},
            "package_ocr_data": {"net_quantity": "250 g", "country_of_origin": "Vietnam", "manufacturer_name": "Suryoday Foods"},
        },
        "expected_verdict": "NON_COMPLIANT",
    },
    {
        "test_case_id": "TC-022",
        "scenario_name": "E-Commerce Checkout Price Exceeds MRP",
        "input_data": {
            "scan_source": "package_image",
            "mrp": {"value": 150.0, "currency_marker": "₹"},
            "listing_data": {"price": 160.0},
        },
        "expected_verdict": "NON_COMPLIANT",
    },
]
