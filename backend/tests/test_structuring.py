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


# ---------------------------------------------------------------------------
# New tests: squished OCR date handling
# ---------------------------------------------------------------------------

def test_parse_mfg_date_month_name_form():
    """'Mfg. Date May 2023' (well-formed) should parse as 2023-05-01."""
    assert structuring.parse_mfg_date(["Mfg. Date May 2023"]) == "2023-05-01"


def test_parse_mfg_date_squished_month_name():
    """'Mfg. DateMay 2023' (squished OCR) should be normalised to '2023-05-01'."""
    assert structuring.parse_mfg_date(["Mfg. DateMay 2023"]) == "2023-05-01"


def test_parse_best_before_month_name_form():
    """'Exp. Date Jan 2025' (well-formed) should parse as 2025-01-01."""
    assert structuring.parse_best_before(["Exp. Date Jan 2025"]) == "2025-01-01"


def test_parse_best_before_squished_month_name():
    """'Exp. DateJan 2025' (squished OCR) should be normalised to '2025-01-01'."""
    assert structuring.parse_best_before(["Exp. DateJan 2025"]) == "2025-01-01"


# ---------------------------------------------------------------------------
# New tests: unit normalization
# ---------------------------------------------------------------------------

def test_parse_net_quantity_no_space_ml():
    """'500ml' (no space) should be parsed as value=500.0, unit='ml'."""
    result = structuring.parse_net_quantity(["500ml"])
    assert result == {"value": 500.0, "unit": "ml"}


def test_parse_net_quantity_uppercase_ml():
    """'500ML' should be normalised to unit='ml'."""
    result = structuring.parse_net_quantity(["Net Wt 500ML"])
    assert result is not None
    assert result["unit"] == "ml"


def test_parse_net_quantity_mixed_case_ml():
    """'500mL' should be normalised to unit='ml'."""
    result = structuring.parse_net_quantity(["500mL"])
    assert result is not None
    assert result["unit"] == "ml"


# ---------------------------------------------------------------------------
# New tests: fuzzy phrase matching in DSL registry
# ---------------------------------------------------------------------------

def test_contains_phrase_exact_match():
    from lmd.dsl.registry import contains_phrase
    assert contains_phrase("MRP Rs. 144/- (inclusive of all taxes)", "inclusive of all taxes") is True


def test_contains_phrase_typo_texes():
    """The real label has 'texes' instead of 'taxes'; fuzzy match must return True."""
    from lmd.dsl.registry import contains_phrase
    assert contains_phrase("MRP: Rs. 144/- (inclusive of all texes)", "inclusive of all taxes") is True


def test_contains_phrase_completely_wrong_string():
    """A totally different string must not fuzzy-match."""
    from lmd.dsl.registry import contains_phrase
    assert contains_phrase("MRP: Rs. 144/-", "inclusive of all taxes") is False

