"""The whitelisted function table the DSL evaluator may call.

Every callable here is pure: it takes already-resolved Python values and
returns a Python value. No callable here does file I/O, network I/O, or
touches the evaluator/AST machinery. `get_standard_sizes` reads a small
static JSON data file loaded once at import time -- not per-call I/O.

Ports and fixes research/NotebookLM/rule_engine.py defects (CLAUDE.md section 5):
- to_base_unit no longer lower()-cases before the ['l','L'] check (defect #3).
- to_base_unit returns a dimension-tagged Quantity, so 500 g and 500 ml can
  never compare equal (defect #4). Cross-dimension arithmetic raises UnknownValue.
- round_mrp_paise is preserved verbatim (math is correct) but LM-M03 is wired
  as a DIAGNOSTIC-severity rule at the rules-JSON level, per CLAUDE.md 4.2 --
  this function is never used to fail a rule, only to annotate.
"""
from __future__ import annotations

import datetime
import difflib
import json
import re
from pathlib import Path
from typing import Any

from .errors import UnknownValue

_SECOND_SCHEDULE_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "rules" / "second_schedule_sizes.json"
)
with _SECOND_SCHEDULE_PATH.open("r", encoding="utf-8") as _f:
    _SECOND_SCHEDULE = json.load(_f)

_UNIT_DIMENSION: dict[str, tuple[str, float]] = {
    "mg": ("mass", 0.001),
    "g": ("mass", 1.0),
    "kg": ("mass", 1000.0),
    "ml": ("volume", 1.0),
    "l": ("volume", 1000.0),
    "L": ("volume", 1000.0),
    "mm": ("length", 1.0),
    "cm": ("length", 10.0),
    "m": ("length", 1000.0),
    "N": ("count", 1.0),
    "pcs": ("count", 1.0),
    "units": ("count", 1.0),
    "pair": ("count", 1.0),
    "sets": ("count", 1.0),
}


class Quantity:
    """A unit value tagged with its physical dimension.

    Arithmetic between two Quantity objects of different dimension raises
    UnknownValue instead of silently producing a wrong number (CLAUDE.md
    defect #4: 500 g must never compare equal to 500 ml).
    """

    __slots__ = ("dimension", "magnitude")

    def __init__(self, dimension: str, magnitude: float):
        self.dimension = dimension
        self.magnitude = magnitude

    def _same_dim(self, other: Quantity) -> None:
        if not isinstance(other, Quantity) or other.dimension != self.dimension:
            raise UnknownValue(f"dimension_mismatch:{self.dimension}")

    def __sub__(self, other: Quantity) -> Quantity:
        self._same_dim(other)
        return Quantity(self.dimension, self.magnitude - other.magnitude)

    def __abs__(self) -> Quantity:
        return Quantity(self.dimension, abs(self.magnitude))

    def __mul__(self, scalar: float) -> Quantity:
        return Quantity(self.dimension, self.magnitude * scalar)

    __rmul__ = __mul__

    def __rtruediv__(self, scalar: float) -> float:
        # e.g. mrp.value / to_base_unit(net_quantity.value, net_quantity.unit)
        if self.magnitude == 0:
            raise UnknownValue("division_by_zero")
        return scalar / self.magnitude

    def __le__(self, other: Any) -> bool:
        if isinstance(other, Quantity):
            self._same_dim(other)
            return self.magnitude <= other.magnitude
        return self.magnitude <= other

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Quantity):
            return self.dimension == other.dimension and self.magnitude == other.magnitude
        return NotImplemented

    def __repr__(self) -> str:
        return f"Quantity({self.dimension}, {self.magnitude})"


def to_base_unit(value: float, unit: str) -> Quantity:
    if value is None or unit is None:
        raise UnknownValue(f"unit:{unit}")
    entry = _UNIT_DIMENSION.get(unit)
    if entry is None:
        raise UnknownValue(f"unit:{unit}")
    dimension, factor = entry
    return Quantity(dimension, value * factor)


def round_mrp_paise(x: float) -> float:
    if x is None:
        raise UnknownValue("mrp.computed_value")
    rupees = int(x)
    paise = round((x - rupees) * 100)
    if paise < 50:
        return float(rupees)
    if paise <= 95:
        return float(rupees) + 0.50
    return float(rupees + 1)


def is_numeric(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def is_valid_calendar_date(x: Any) -> bool:
    if not isinstance(x, str):
        return False
    try:
        datetime.datetime.strptime(x, "%Y-%m-%d")  # noqa: DTZ007 -- calendar date only, tz is meaningless here
        return True
    except ValueError:
        return False


def count_distinct(values: list) -> int:
    if values is None:
        raise UnknownValue("count_distinct:list")
    return len(set(values))


def min_confidence(values: list) -> float:
    if values is None:
        raise UnknownValue("min_confidence:list")
    if not values:
        return 1.0
    return min(values)


def matches_regex(text: Any, pattern: str) -> bool:
    if not isinstance(text, str):
        return False
    return re.match(pattern, text) is not None


_FUZZY_PHRASE_THRESHOLD = 0.85


def contains_phrase(text: Any, phrase: str) -> bool:
    """Return True if `phrase` is a substring of `text` (case-insensitive).

    Falls back to a sliding-window fuzzy match (difflib.SequenceMatcher,
    threshold=0.85) so that common real-world OCR/print typos on physical
    packaging -- e.g. "inclusive of all texes" vs "inclusive of all taxes" --
    do not cause a false FAIL.
    """
    if not isinstance(text, str):
        return False
    text_lower = text.lower()
    phrase_lower = phrase.lower()
    if phrase_lower in text_lower:
        return True
    # Sliding-window fuzzy match: compare phrase against every same-length
    # window in the text; accept on the first window that meets the threshold.
    plen = len(phrase_lower)
    if plen == 0:
        return True
    for start in range(len(text_lower) - plen + 1):
        window = text_lower[start : start + plen]
        ratio = difflib.SequenceMatcher(None, phrase_lower, window, autojunk=False).ratio()
        if ratio >= _FUZZY_PHRASE_THRESHOLD:
            return True
    return False


def get_standard_sizes(subtype: str) -> list:
    """Return the list of standard sizes (in grams or ml) for a given commodity
    subtype, or [] if the subtype is not in the Second Schedule data.

    Handles both the legacy flat-list format (biscuits pre-expansion) and the
    current nested-dict format {_verified, _source, values: [...]}.
    """
    entry = _SECOND_SCHEDULE.get("sizes_g", {}).get(subtype)
    if entry is None:
        return []
    if isinstance(entry, list):
        return entry  # legacy flat-list format (should not appear post-expansion)
    if isinstance(entry, dict):
        return entry.get("values", [])
    return []


def get_second_schedule_categories() -> list[str]:
    """The commodity subtypes for which second_schedule_sizes.json encodes a
    *gazette-verified* standard-sizes list -- used by lmd.engine.engine to
    build system.second_schedule_list so that adding a verified category to
    the JSON activates LM-M04a/LM-M04b (BLOCKER/MAJOR) for it with no code
    change.

    Subtypes marked _verified: false (paraphrased secondary-source sizes,
    not the actual gazette text) are deliberately excluded here, so
    LM-M04a/LM-M04b evaluate to NOT_APPLICABLE for them instead of firing a
    BLOCKER off unverified data -- per second_schedule_sizes.json's own
    _note and CLAUDE.md invariant 10 (never fabricate a legal threshold).
    """
    sizes = _SECOND_SCHEDULE.get("sizes_g", {})
    return [
        subtype
        for subtype, entry in sizes.items()
        if isinstance(entry, list) or entry.get("_verified") is True
    ]


FUNCTIONS: dict[str, Any] = {
    "to_base_unit": to_base_unit,
    "round_mrp_paise": round_mrp_paise,
    "is_numeric": is_numeric,
    "is_valid_calendar_date": is_valid_calendar_date,
    "count_distinct": count_distinct,
    "min_confidence": min_confidence,
    "matches_regex": matches_regex,
    "contains_phrase": contains_phrase,
    "get_standard_sizes": get_standard_sizes,
    "abs": abs,
    "max": max,
    "min": min,
}
