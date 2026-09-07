"""Turn a rules-JSON condition string into a Python-ast-parseable expression.

Input grammar (as written in packages/rules/lmd_rules.v1.json), e.g.:

    "exists(net_quantity.value) AND exists(net_quantity.unit)"
    "net_quantity.unit IN ['g', 'kg', ...]"
    "commodity.subtype IN system.second_schedule_list AND net_quantity NOT IN get_standard_sizes(commodity.subtype)"
    "mrp.raw_text CONTAINS_PHRASE('inclusive of all taxes') OR mrp.raw_text MATCHES 'MRP.*incl'"

Output: a string parseable by ast.parse(..., mode="eval") containing only
Name/Call/Constant/List/BoolOp/UnaryOp/Compare/BinOp nodes -- every bare
field reference (dotted or not) becomes a `field('the.path')` Call, so the
compiled tree never contains an ast.Attribute node (CLAUDE.md invariant #2).
"""
from __future__ import annotations

import re

from .errors import DslLoadError

# Functions that are legitimately called in condition strings. Any bare
# identifier immediately followed by '(' that is NOT in this set is a bug
# in the source rule (typo, or a function we haven't registered) and must
# fail to load rather than silently become a field lookup.
_KNOWN_CALL_NAMES = {
    "exists",
    "is_null",
    "coalesce",
    "field",
    "get_fields_for_blockers",
    "to_base_unit",
    "round_mrp_paise",
    "is_numeric",
    "is_valid_calendar_date",
    "count_distinct",
    "min_confidence",
    "matches_regex",
    "contains_phrase",
    "get_standard_sizes",
    "abs",
    "max",
    "min",
}

_RESERVED_BARE = {"True", "False", "and", "or", "not", "in", "true", "false"}

_STRING_LITERAL_RE = re.compile(r"'(?:[^'\\]|\\.)*'")

_INFIX_CONTAINS_PHRASE_RE = re.compile(r"(\S+)\s+CONTAINS_PHRASE\((__STR\d+__)\)")
_INFIX_MATCHES_RE = re.compile(r"(\S+)\s+MATCHES\s+(__STR\d+__)")

_KEYWORD_REPLACEMENTS = [
    (re.compile(r"\bNOT IN\b"), "not in"),
    (re.compile(r"\bIN\b"), "in"),
    (re.compile(r"\bAND\b"), "and"),
    (re.compile(r"\bOR\b"), "or"),
    (re.compile(r"\bNOT\b"), "not"),
    (re.compile(r"\btrue\b"), "True"),
    (re.compile(r"\bfalse\b"), "False"),
]

_IDENT_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\b(\s*\()?"
)


def _protect_strings(source: str) -> tuple[str, list[str]]:
    literals: list[str] = []

    def _stash(m: re.Match) -> str:
        literals.append(m.group(0))
        return f"__STR{len(literals) - 1}__"

    return _STRING_LITERAL_RE.sub(_stash, source), literals


def _restore_strings(source: str, literals: list[str]) -> str:
    for i, lit in enumerate(literals):
        source = source.replace(f"__STR{i}__", lit)
    return source


_PLACEHOLDER_RE = re.compile(r"^__STR\d+__$")


def _wrap_field(m: re.Match) -> str:
    ident, trailing_paren = m.group(1), m.group(2)
    if _PLACEHOLDER_RE.match(ident):
        return ident + (trailing_paren or "")
    if ident in _RESERVED_BARE:
        # e.g. "... and (" -- the '(' here is a grouping paren, not a call.
        return ident + (trailing_paren or "")
    if trailing_paren is not None:
        if ident not in _KNOWN_CALL_NAMES:
            raise DslLoadError(
                f"unknown function {ident!r} in condition -- refusing to load"
            )
        return ident + trailing_paren
    if ident.replace(".", "").isdigit():
        return ident
    return f"field('{ident}')"


def normalize(raw: str) -> str:
    protected, literals = _protect_strings(raw)

    protected = _INFIX_CONTAINS_PHRASE_RE.sub(r"contains_phrase(\1, \2)", protected)
    protected = _INFIX_MATCHES_RE.sub(r"matches_regex(\1, \2)", protected)

    for pattern, replacement in _KEYWORD_REPLACEMENTS:
        protected = pattern.sub(replacement, protected)

    protected = _IDENT_RE.sub(_wrap_field, protected)

    return _restore_strings(protected, literals)
