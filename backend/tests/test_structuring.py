from lmd.cv.stages import structuring


def test_parse_net_quantity_finds_value_and_unit():
    assert structuring.parse_net_quantity(["Net Wt. 200 g", "some other line"]) == {"value": 200.0, "unit": "g"}


def test_parse_net_quantity_absent_when_no_match():
    assert structuring.parse_net_quantity(["no quantity here"]) is None


def test_parse_mrp_with_rupee_symbol():
    result = structuring.parse_mrp(["MRP ₹150.00 incl. of all taxes"])
    assert result == {"value": 150.0, "currency_marker": "₹", "raw_text": "MRP ₹150.00 incl. of all taxes"}


def test_parse_mrp_with_rs_prefix():
    result = structuring.parse_mrp(["M.R.P. Rs. 99"])
    assert result["value"] == 99.0
    assert result["currency_marker"] == "Rs."


def test_parse_mrp_with_long_tax_disclaimer_between_marker_and_value():
    # A disclaimer longer than the old 15-char gap cap must still parse.
    result = structuring.parse_mrp(["MRP (Incl. of all Taxes) Rs. 45.00"])
    assert result["value"] == 45.0


def test_parse_mrp_recovers_when_rapidocr_splits_marker_and_value_across_lines():
    result = structuring.parse_mrp(["MRP", "₹45.00"])
    assert result["value"] == 45.0
    assert result["currency_marker"] == "₹"


def test_parse_mrp_recovers_split_marker_with_tax_disclaimer_on_marker_line():
    result = structuring.parse_mrp(["MRP (Incl. of all Taxes)", "Rs. 45.00"])
    assert result["value"] == 45.0


def test_parse_mrp_ignores_unrelated_number_after_bare_marker_line():
    # A line that just says "MRP" followed by an unrelated line with no
    # currency marker or decimal must not be mis-parsed as the price.
    result = structuring.parse_mrp(["MRP", "Batch 12"])
    assert result is None


def test_parse_consumer_care_phone_and_email():
    result = structuring.parse_consumer_care(["Call 1800-225599 or write to consumer@example.com"])
    assert result["phone"] is not None
    assert result["email"] == "consumer@example.com"


def test_parse_country_of_origin_labelled():
    assert structuring.parse_country_of_origin(["Country of Origin: India"]) == "India"


def test_parse_country_of_origin_made_in():
    assert structuring.parse_country_of_origin(["Made in China"]) == "China"


def test_parse_mfg_date():
    assert structuring.parse_mfg_date(["MFD 08/2026"]) == "2026-08-01"


def test_structure_fields_only_includes_found_keys():
    lines = ["Net Wt. 100 g", "MRP Rs. 45", "unrelated line"]
    out = structuring.structure_fields(lines)
    assert out["net_quantity"] == {"value": 100.0, "unit": "g"}
    assert out["mrp"]["value"] == 45.0
    assert "country_of_origin" not in out
    assert "consumer_care" not in out


def test_structure_fields_empty_when_nothing_found():
    assert structuring.structure_fields(["random text with nothing useful"]) == {}
