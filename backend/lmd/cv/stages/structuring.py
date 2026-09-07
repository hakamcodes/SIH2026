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
    r"(?:MRP|M\.?R\.?P\.?)[^\d₹]{0,15}(?:Rs\.?|₹)?\s*[:\-]?\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE
)
_CURRENCY_MARKER_RE = re.compile(r"₹|Rs\.?")
_PHONE_RE = re.compile(r"\+?91?[-\s]?\d{10}\b|\b1800[-\s]?\d{6}\b")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_MFG_DATE_LABEL_RE = re.compile(r"(?:MFD|MFG|MANUFACTURED)[^\d]{0,10}(\d{1,2})[/\-.](\d{4})", re.IGNORECASE)

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


def parse_net_quantity(lines: list[str]) -> dict | None:
    # Prefer a line with an explicit NET WT/QTY marker over an unmarked
    # number, which may belong to an ingredient or a dimension elsewhere
    # on the panel.
    for line in lines:
        m = _NET_QTY_MARKER_RE.search(line)
        if m:
            value, unit = m.groups()
            return {"value": float(value), "unit": unit}
    # OCR sometimes splits the marker and the value into adjacent boxes
    # (e.g. "NET WT." / "120g" as two separate lines).
    for i, line in enumerate(lines):
        if _NET_QTY_MARKER_ONLY_RE.search(line) and i + 1 < len(lines):
            m = _NET_QTY_RE.search(lines[i + 1])
            if m:
                value, unit = m.groups()
                return {"value": float(value), "unit": unit}
    for line in lines:
        m = _NET_QTY_RE.search(line)
        if m:
            value, unit = m.groups()
            return {"value": float(value), "unit": unit}
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
    for line in lines:
        m = _MFG_DATE_LABEL_RE.search(line)
        if m:
            month, year = m.groups()
            month_int = int(month)
            if 1 <= month_int <= 12:
                return f"{year}-{month_int:02d}-01"
    return None


def parse_best_before(lines: list[str]) -> str | None:
    for line in lines:
        m = _BEST_BEFORE_DMY_RE.search(line)
        if m:
            day, month, year = m.groups()
            day_int, month_int = int(day), int(month)
            if 1 <= month_int <= 12 and 1 <= day_int <= 31:
                return f"{year}-{month_int:02d}-{day_int:02d}"
    for line in lines:
        m = _BEST_BEFORE_MY_RE.search(line)
        if m:
            month, year = m.groups()
            month_int = int(month)
            if 1 <= month_int <= 12:
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
    raw OCR text lines. Only includes keys it found something for."""
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
    return None
