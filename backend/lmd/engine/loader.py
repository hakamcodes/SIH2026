"""Rule file loading. No default path, no bare except.

Per CLAUDE.md invariant #3: a missing or invalid rules file is a fatal
startup error. It must be impossible to run against an empty ruleset.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from lmd.dsl.compiler import compile_condition
from lmd.dsl.errors import DslLoadError
from lmd.dsl.normalize import normalize

_REQUIRED_KEYS = {
    "rule_id",
    "category",
    "description",
    "legal_basis",
    "effective_from",
    "effective_to",
    "applicable_when",
    "condition",
    "severity",
    "on_fail_code",
    "min_field_confidence",
}


@dataclass
class CompiledRule:
    rule_id: str
    category: str
    description: str
    legal_basis: str
    effective_from: str
    effective_to: str | None
    severity: str
    on_fail_code: str | None
    min_field_confidence: float
    confidence_policy: str
    citation_verified: bool
    applicable_when_ast: object
    condition_ast: object
    exempt_from_effective_gate: bool = False


class RuleLoadError(Exception):
    """Fatal at startup. There is no fallback ruleset."""


def load_rules(rules_path: str | Path) -> list[CompiledRule]:
    path = Path(rules_path)
    if not path.is_file():
        raise RuleLoadError(f"rules file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw_rules = json.load(f)

    if not isinstance(raw_rules, list) or not raw_rules:
        raise RuleLoadError(f"rules file {path} contains no rules")

    compiled: list[CompiledRule] = []
    seen_ids: set[str] = set()
    for entry in raw_rules:
        missing = _REQUIRED_KEYS - entry.keys()
        if missing:
            raise RuleLoadError(
                f"rule {entry.get('rule_id', '<unknown>')} missing required keys: {missing}"
            )
        rule_id = entry["rule_id"]
        if rule_id in seen_ids:
            raise RuleLoadError(f"duplicate rule_id: {rule_id}")
        seen_ids.add(rule_id)

        try:
            applicable_ast = compile_condition(normalize(entry["applicable_when"]))
            condition_ast = compile_condition(normalize(entry["condition"]))
        except DslLoadError as exc:
            raise RuleLoadError(f"rule {rule_id} failed to load: {exc}") from exc

        compiled.append(
            CompiledRule(
                rule_id=rule_id,
                category=entry["category"],
                description=entry["description"],
                legal_basis=entry["legal_basis"],
                effective_from=entry["effective_from"],
                effective_to=entry["effective_to"],
                severity=entry["severity"],
                on_fail_code=entry["on_fail_code"],
                min_field_confidence=entry["min_field_confidence"],
                confidence_policy=entry.get("confidence_policy", "standard"),
                citation_verified=entry.get("citation_verified", True),
                applicable_when_ast=applicable_ast,
                condition_ast=condition_ast,
                exempt_from_effective_gate=entry.get("exempt_from_effective_gate", False),
            )
        )

    return compiled
