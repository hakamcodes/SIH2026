"""Stage 7 (Structuring & Measurement): turn pipeline A's flat list of OCR
text lines into the structured, dotted-path fields the rule engine consumes.
Regex-based, deliberately conservative -- a field this cannot confidently
parse is left absent (never guessed), per CLAUDE.md's "absence, never
invented" rule for the extraction contract.

This is a real, working parser, not a placeholder: it is unit-tested against
synthetic well-formed label text. Its accuracy on arbitrary real photographs
is NOT claimed or asserted anywhere -- per CLAUDE.md section 11, no accuracy
percentage may be claimed without a labelled-set run, and none exists yet.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Devanagari digit normalization
# Applied to every OCR line BEFORE any regex matching so that Hindi-script
# digits on real Indian package labels (e.g. "MRP ₹३०.००") are handled
# by the existing English-path patterns without modification.
# TESTED: digit substitution (०-९ → 0-9) is a pure string transform; it
# cannot produce a false match where none existed before.
# UNTESTED on real Hindi-label images: the Hindi keyword patterns below
# (मूल्य etc.) -- they are added as *alternatives* to English patterns only.
# A comment in each pattern marks its test status.
# ---------------------------------------------------------------------------
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def _normalize_devanagari(line: str) -> str:
    """Translate Devanagari digits to ASCII digits.  All other characters,
    including Devanagari script letters, are left unchanged."""
    return line.translate(_DEVANAGARI_DIGITS)


_NET_QTY_RE = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)\s*(kg|g|mg|ml|l|L|cm|mm|m)\b", re.IGNORECASE
)
_NET_QTY_MARKER_RE = re.compile(
    r"NET\s*(?:WT|WEIGHT|QTY|QUANTITY|CONTENTS)\.?\s*[:\-]?\s*"
    r"(\d+(?:\.\d+)?)\s*(kg|g|mg|ml|l|L|cm|mm|m)\b",
    re.IGNORECASE,
)
_NET_QTY_MARKER_ONLY_RE = re.compile(
    r"NET\s*(?:WT|WEIGHT|QTY|QUANTITY|CONTENTS)\.?\s*[:\-]?\s*$", re.IGNORECASE
)
_MRP_RE = re.compile(
    # English: MRP / M.R.P. (tested, verified on English-label OCR output)
    # Hindi synonyms: मूल्य (mulya), कीमत (keemat), एम.आर.पी (M.R.P. in Devanagari)
    # UNTESTED on real Hindi-label images -- added as alternatives only;
    # if a Hindi label is printed in Devanagari script, RapidOCR must first
    # produce the Devanagari text before these patterns can match.
    r"(?:MRP|M\.?R\.?P\.?|मूल्य|कीमत|एम\.?आर\.?पी\.?)[^\d₹]{0,40}(?:Rs\.?|₹)?\s*[:\-]?\s*(\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
# RapidOCR sometimes splits a dense small-print MRP line into two boxes --
# "MRP" (or "MRP (Incl. of all Taxes)") alone, then the "₹45.00" value on the
# next box/line -- the same failure mode _NET_QTY_MARKER_ONLY_RE exists to
# handle for net quantity. A line matching this has the marker but no digits
# of its own, so parse_mrp knows to look at the following line.
_MRP_MARKER_ONLY_RE = re.compile(
    r"^\s*(?:MRP|M\.?R\.?P\.?|मूल्य|कीमत|एम\.?आर\.?पी\.?)\b[^\d₹]*$",
    re.IGNORECASE,
)
_CURRENCY_MARKER_RE = re.compile(r"₹|Rs\.?")
_PHONE_RE = re.compile(r"\+?91?[-\s]?\d{10}\b|\b1800[-\s]?\d{6}\b")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_MONTH_NAMES_TUPLE = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)
_MONTH_ABBRS_TUPLE = (
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
)
# All recognised month-name tokens (full names + 3-letter abbreviations),
# deduplicated and sorted longest-first so the regex alternation is greedy-safe.
_ALL_MONTH_TOKENS = tuple(sorted(
    set(_MONTH_NAMES_TUPLE) | set(_MONTH_ABBRS_TUPLE),
    key=len,
    reverse=True,
))
# Map every recognised month token (lower-case) to its 1-based integer month.
_MONTH_NAME_TO_INT: dict[str, int] = {
    **{name: i + 1 for i, name in enumerate(_MONTH_NAMES_TUPLE)},
    **{abbr: i + 1 for i, abbr in enumerate(_MONTH_ABBRS_TUPLE)},
}
_MONTH_NAME_SQUISH_RE = re.compile(
    r"([A-Za-z])(" + "|".join(re.escape(t) for t in _ALL_MONTH_TOKENS) + r")\b",
    re.IGNORECASE,
)


def _insert_space_before_month_names(line: str) -> str:
    """Insert a space before a month name/abbreviation that is squished directly
    after another letter -- the OCR output 'Mfg. DateMay 2023' becomes
    'Mfg. Date May 2023', and 'Exp. DateJan 2025' becomes 'Exp. Date Jan 2025'.
    Only inserts when the preceding character is a letter (not a space or digit)
    so already-well-formed text is unchanged.
    """
    return _MONTH_NAME_SQUISH_RE.sub(lambda m: m.group(1) + " " + m.group(2), line)


_MFG_DATE_LABEL_RE = re.compile(
    # Numeric month form: MFD/MFG 08/2026 or 08-2026
    r"(?:MFD|MFG|MANUFACTURED)[^\d]{0,10}(\d{1,2})[/\-.](\d{4})"
    r"|"
    # Month-name/abbr form: 'Mfg. Date May 2023' or squished 'Mfg.DateMay 2023'
    # (after _insert_space_before_month_names preprocessing normalises it)
    r"(?:Mf[gd]\.?\s*(?:Date)?|Manufactured\s*(?:Date)?)"
    r"\s*(" + "|".join(re.escape(t) for t in _ALL_MONTH_TOKENS) + r")\s+(\d{4})",
    re.IGNORECASE,
)

# Real Indian labels declare the manufacturer/packer/importer behind one of
# these markers (verified against actual RapidOCR output on
# research/mainResearch/{01,02}*.jpg -- "Mfd. by Colgate-Palmolive (India)
# Ltd." and "MFG.By: ... By Netle Ida Limited," both appear verbatim). The
# address is terminated by an Indian PIN code, which is as reliable a
# boundary as the currency marker is for MRP.
_MANUFACTURER_MARKER_RE = re.compile(
    r"(?:Mfd|Mfg|Manufactured|Marketed|Packed|Imported)\.?\s*by\b\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)
_PIN_CODE_RE = re.compile(r"\b\d{3}\s?\d{3}\b")

# Explicit MM/YYYY or DD/MM/YYYY only -- deliberately no relative-form
# support ("24 Months From MFD.") since computing a date from an unread
# manufacturing date would fabricate a legal date, not read one.
_BEST_BEFORE_DMY_RE = re.compile(
    r"(?:Best\s*Before(?:\s*Use)?|Use\s*By|Expiry|Exp\.?)\D{0,10}"
    r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})",
    re.IGNORECASE,
)
_BEST_BEFORE_MY_RE = re.compile(
    r"(?:Best\s*Before(?:\s*Use)?|Use\s*By|Expiry|Exp\.?)\D{0,10}(\d{1,2})[/\-.](\d{4})",
    re.IGNORECASE,
)
# Month-name/abbr form: 'Exp. Date Jan 2025' or squished 'Exp. DateJan 2025'
_BEST_BEFORE_MONTH_NAME_RE = re.compile(
    r"(?:Best\s*Before(?:\s*Use)?|Use\s*By|Expiry|Exp\.?)\s*(?:Date)?\s*"
    r"(" + "|".join(re.escape(t) for t in _ALL_MONTH_TOKENS) + r")\s+(\d{4})",
    re.IGNORECASE,
)
_BEST_BEFORE_ANY_RE = re.compile(r"Best\s*Before(?:\s*Use)?|Use\s*By|Expiry|Exp\.?", re.IGNORECASE)

# Common/generic name: only an explicit declared label is trusted here.
# There is no reliable lexical marker for "this is the generic descriptor"
# the way there is for MRP or a manufacturer "by" clause -- a guess here
# (e.g. matching a closed vocabulary of product words) risks a false PASS
# on LM-C07 from an unrelated word (an ingredient, a slogan). Left to the
# vision cross-check in lmd.cv.reconcile for the unlabelled case.
_GENERIC_NAME_LABEL_RE = re.compile(r"(?:Generic\s*Name|Common\s*Name)\s*[:\-]?\s*(.+)", re.IGNORECASE)

_KNOWN_COUNTRIES = [
    "India", "Vietnam", "China", "USA", "Japan", "Germany",
    "Bangladesh", "Thailand", "Malaysia", "Sri Lanka", "Indonesia",
]
_COUNTRY_OF_ORIGIN_RE = re.compile(
    r"(?:COUNTRY OF ORIGIN|MADE IN|PRODUCT OF)\s*[:\-]?\s*([A-Za-z ]{3,20})", re.IGNORECASE
)


# Canonical unit forms accepted by registry._UNIT_DIMENSION.  OCR output
# may return 'ML', 'mL', 'Kg', etc.; normalise before handing to the rule engine.
_UNIT_CANONICAL: dict[str, str] = {
    "mg": "mg",
    "g": "g",
    "kg": "kg",
    "ml": "ml",
    "ml": "ml",
    "l": "l",
    "L": "L",
    "cm": "cm",
    "mm": "mm",
    "m": "m",
    "n": "N",
    "pcs": "pcs",
    "units": "units",
    "pair": "pair",
    "sets": "sets",
}


def _normalize_unit(unit: str) -> str:
    """Return the canonical unit string for `unit`, case-insensitively.

    The litre abbreviation is special: lowercase 'l' is kept as 'l' and
    uppercase 'L' is kept as 'L' since both are in _UNIT_DIMENSION. All
    other units collapse to lowercase (e.g. 'ML' → 'ml', 'KG' → 'kg').
    """
    if unit in ("l", "L"):
        return unit  # preserve case for litre
    return _UNIT_CANONICAL.get(unit.lower(), unit.lower())


def parse_net_quantity(lines: list[str]) -> dict | None:
    # Prefer a line with an explicit NET WT/QTY marker over an unmarked
    # number, which may belong to an ingredient or a dimension elsewhere
    # on the panel.
    for line in lines:
        m = _NET_QTY_MARKER_RE.search(line)
        if m:
            value, unit = m.groups()
            return {"value": float(value), "unit": _normalize_unit(unit)}
    # OCR sometimes splits the marker and the value into adjacent boxes
    # (e.g. "NET WT." / "120g" as two separate lines).
    for i, line in enumerate(lines):
        if _NET_QTY_MARKER_ONLY_RE.search(line) and i + 1 < len(lines):
            m = _NET_QTY_RE.search(lines[i + 1])
            if m:
                value, unit = m.groups()
                return {"value": float(value), "unit": _normalize_unit(unit)}
    for line in lines:
        m = _NET_QTY_RE.search(line)
        if m:
            value, unit = m.groups()
            return {"value": float(value), "unit": _normalize_unit(unit)}
    return None


def _clean_manufacturer_name(text: str) -> str:
    text = text.strip().strip(":-,. ")
    # OCR sometimes splits the marker itself across lines, leaking a
    # stray "By " onto the next line (e.g. "MFG.By:" / "By Netle Ida
    # Limited,").
    text = re.sub(r"^by\s+", "", text, flags=re.IGNORECASE)
    return text.strip(":-,. ")


def parse_manufacturer(lines: list[str]) -> dict | None:
    for i, line in enumerate(lines):
        m = _MANUFACTURER_MARKER_RE.search(line)
        if not m:
            continue
        name = _clean_manufacturer_name(m.group(1))
        name_index = i
        if len(name) < 3 and i + 1 < len(lines):
            # The marker line carried no usable name text (OCR split the
            # marker from its content); the next line is the name instead.
            name = _clean_manufacturer_name(lines[i + 1])
            name_index = i + 1
        if len(name) < 3:
            continue
        if _PIN_CODE_RE.search(lines[name_index]):
            return {"name": name, "address": lines[name_index].strip()}
        # RapidOCR's box detection order does not follow visual reading
        # order on a busy label -- the address line may sit either before
        # or after the marker line. Search both directions, nearest first.
        # A hit behind the marker is a self-contained address line already
        # (e.g. "Regd. Off.: ... Gardens, Powai, Mumbai-400076"); a hit
        # ahead of it may be wrapped across several boxes, so join through
        # the PIN-bearing line.
        for offset in range(1, 6):
            behind = name_index - offset
            if behind >= 0 and _PIN_CODE_RE.search(lines[behind]):
                return {"name": name, "address": lines[behind].strip()}
            ahead = name_index + offset
            if ahead < len(lines) and _PIN_CODE_RE.search(lines[ahead]):
                address_parts = [lines[k].strip() for k in range(name_index + 1, ahead + 1)]
                return {"name": name, "address": " ".join(address_parts)}
        return {"name": name, "address": None}
    return None


def parse_mrp(lines: list[str]) -> dict | None:
    for line in lines:
        m = _MRP_RE.search(line)
        if m:
            value = float(m.group(1).replace(",", ""))
            currency = "₹" if "₹" in line else ("Rs." if _CURRENCY_MARKER_RE.search(line) else None)
            return {"value": value, "currency_marker": currency, "raw_text": line.strip()}
    # OCR split the marker and the value across adjacent boxes -- join them
    # and retry the same regex rather than accepting an unmarked number.
    # Require a currency marker or a decimal value on the join: the marker
    # line alone gives no gap-content guarantee the way a single OCR line
    # does, so an unmarked whole number (e.g. a batch code on the next line)
    # must not be mistaken for a price.
    for i, line in enumerate(lines):
        if _MRP_MARKER_ONLY_RE.search(line) and i + 1 < len(lines):
            joined = f"{line.strip()} {lines[i + 1].strip()}"
            m = _MRP_RE.search(joined)
            if m:
                raw_value = m.group(1)
                has_currency = "₹" in joined or bool(_CURRENCY_MARKER_RE.search(joined))
                has_decimal = "." in raw_value or "," in raw_value
                if not (has_currency or has_decimal):
                    continue
                value = float(raw_value.replace(",", ""))
                currency = "₹" if "₹" in joined else ("Rs." if _CURRENCY_MARKER_RE.search(joined) else None)
                return {"value": value, "currency_marker": currency, "raw_text": joined}
    return None


def parse_consumer_care(lines: list[str]) -> dict | None:
    phone = email = None
    for line in lines:
        if phone is None:
            m = _PHONE_RE.search(line)
            if m:
                phone = m.group(0)
        if email is None:
            m = _EMAIL_RE.search(line)
            if m:
                email = m.group(0)
    if phone is None and email is None:
        return None
    return {"phone": phone, "email": email}


def parse_country_of_origin(lines: list[str]) -> str | None:
    for line in lines:
        m = _COUNTRY_OF_ORIGIN_RE.search(line)
        if m:
            candidate = m.group(1).strip()
            for country in _KNOWN_COUNTRIES:
                if country.lower() in candidate.lower():
                    return country
    for line in lines:
        for country in _KNOWN_COUNTRIES:
            if re.search(rf"\b{re.escape(country)}\b", line, re.IGNORECASE):
                return country
    return None


def parse_mfg_date(lines: list[str]) -> str | None:
    for raw_line in lines:
        # Normalise squished OCR text like 'Mfg. DateMay 2023' before matching.
        line = _insert_space_before_month_names(raw_line)
        m = _MFG_DATE_LABEL_RE.search(line)
        if m:
            month_num, year_num, month_name, year_name = m.groups()
            if month_num is not None:
                # Arm 1: numeric form  e.g. MFG 08/2026
                month_int = int(month_num)
                if 1 <= month_int <= 12:
                    return f"{year_num}-{month_int:02d}-01"
            elif month_name is not None:
                # Arm 2: month-name/abbr form  e.g. Mfg. Date May 2023 or Mfg. Date Jan 2023
                month_int = _MONTH_NAME_TO_INT.get(month_name.lower())
                if month_int is not None:
                    return f"{year_name}-{month_int:02d}-01"
    return None


def parse_best_before(lines: list[str]) -> str | None:
    for raw_line in lines:
        line = _insert_space_before_month_names(raw_line)
        m = _BEST_BEFORE_DMY_RE.search(line)
        if m:
            day, month, year = m.groups()
            day_int, month_int = int(day), int(month)
            if 1 <= month_int <= 12 and 1 <= day_int <= 31:
                return f"{year}-{month_int:02d}-{day_int:02d}"
    for raw_line in lines:
        line = _insert_space_before_month_names(raw_line)
        m = _BEST_BEFORE_MY_RE.search(line)
        if m:
            month, year = m.groups()
            month_int = int(month)
            if 1 <= month_int <= 12:
                return f"{year}-{month_int:02d}-01"
    # Month-name/abbr form: 'Exp. Date Jan 2025' or squished 'Exp. DateJan 2025'
    for raw_line in lines:
        line = _insert_space_before_month_names(raw_line)
        m = _BEST_BEFORE_MONTH_NAME_RE.search(line)
        if m:
            month_name, year = m.groups()
            month_int = _MONTH_NAME_TO_INT.get(month_name.lower())
            if month_int is not None:
                return f"{year}-{month_int:02d}-01"
    return None


def parse_common_or_generic_name(lines: list[str]) -> str | None:
    for line in lines:
        m = _GENERIC_NAME_LABEL_RE.search(line)
        if m:
            value = m.group(1).strip().rstrip(".")
            if value:
                return value
    return None


def structure_fields(lines: list[str]) -> dict:
    """Best-effort structured subset of ExtractionEnvelope fields parsed from
    raw OCR text lines. Only includes keys it found something for.

    Devanagari digits are normalised to ASCII before any regex matching so that
    Hindi-script numerals on real Indian labels (e.g. ₹३०.०० for MRP) are
    handled by the existing English-path patterns.  All other Devanagari
    characters are left unchanged.
    """
    # Normalize Devanagari digits across all lines before any parsing.
    # This is the ONLY global preprocessing step; per CLAUDE.md invariant 11,
    # no other global image or text preprocessing is applied.
    lines = [_normalize_devanagari(line) for line in lines]
    out: dict = {}
    if (nq := parse_net_quantity(lines)) is not None:
        out["net_quantity"] = nq
    if (mrp := parse_mrp(lines)) is not None:
        out["mrp"] = mrp
    if (cc := parse_consumer_care(lines)) is not None:
        out["consumer_care"] = cc
    if (coo := parse_country_of_origin(lines)) is not None:
        out["country_of_origin"] = coo
    if (mfg := parse_mfg_date(lines)) is not None:
        out["mfg_date"] = mfg
    if (mfr := parse_manufacturer(lines)) is not None:
        out["manufacturer_or_packer_or_importer"] = mfr
    if (bb := parse_best_before(lines)) is not None:
        out["best_before_date"] = bb
    if (gen := parse_common_or_generic_name(lines)) is not None:
        out["common_or_generic_name"] = gen
    return out


_KEY_PATTERNS = {
    "net_quantity": _NET_QTY_RE,
    "mrp": _MRP_RE,
    "consumer_care": _PHONE_RE,
    "country_of_origin": _COUNTRY_OF_ORIGIN_RE,
    "mfg_date": _MFG_DATE_LABEL_RE,
    "manufacturer_or_packer_or_importer": _MANUFACTURER_MARKER_RE,
    "best_before_date": _BEST_BEFORE_ANY_RE,
    "common_or_generic_name": _GENERIC_NAME_LABEL_RE,
}


def source_line_for(lines: list[str], key: str) -> str | None:
    """Return the first raw OCR line that produced `key` in structure_fields(),
    so a caller (lmd.cv.reconcile) can attach that line's OCR confidence to
    the structured field instead of silently defaulting to full confidence.
    """
    pattern = _KEY_PATTERNS.get(key)
    if pattern is None:
        return None
    for line in lines:
        if pattern.search(line):
            return line
    if key == "mrp" and parse_mrp(lines) is not None:
        # parse_mrp accepted a split-line (marker + value on adjacent boxes)
        # read; mirror the same guard so the returned line matches what was
        # actually accepted, and attach the marker line's own confidence.
        for i, line in enumerate(lines):
            if _MRP_MARKER_ONLY_RE.search(line) and i + 1 < len(lines):
                joined = f"{line.strip()} {lines[i + 1].strip()}"
                m = _MRP_RE.search(joined)
                if m:
                    raw_value = m.group(1)
                    has_currency = "₹" in joined or bool(_CURRENCY_MARKER_RE.search(joined))
                    has_decimal = "." in raw_value or "," in raw_value
                    if has_currency or has_decimal:
                        return line
    return None
