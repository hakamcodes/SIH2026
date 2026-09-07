"""The compliance rule engine. Rules are always evaluated through the DSL
interpreter (CLAUDE.md invariant #1) -- there is no `if rule_id == ...`
branch anywhere in this file.
"""
from __future__ import annotations

import ast
from typing import Any

from lmd.dsl.errors import UnknownValue
from lmd.dsl.evaluator import DslContext, evaluate, referenced_field_paths
from lmd.dsl.registry import get_second_schedule_categories

from .loader import CompiledRule
from .models import RuleResult, RuleStatus, ScanResult, Severity
from .verdict import aggregate


def _has_call(node: ast.AST, func_name: str) -> bool:
    return any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == func_name
        for n in ast.walk(node)
    )


def _field_confidence(product: dict[str, Any], path: str) -> float:
    top_field = path.split(".")[0]
    confidences = product.get("field_confidences", {}) or {}
    return confidences.get(top_field, 1.0)


class RuleEngine:
    def __init__(self, rules: list[CompiledRule]):
        self.rules = rules

    def evaluate(
        self,
        product: dict[str, Any],
        scan_date: str,
        system: dict[str, Any] | None = None,
        ruleset_meta: dict[str, Any] | None = None,
    ) -> ScanResult:
        system = dict(system or {})
        system.setdefault("current_date", scan_date)
        system.setdefault("scan_date", scan_date)
        system.setdefault(
            "valid_country_list",
            [
                "India", "Vietnam", "China", "USA", "Japan", "Germany",
                "Bangladesh", "Thailand", "Malaysia", "Sri Lanka", "Indonesia",
            ],
        )
        system.setdefault("second_schedule_list", get_second_schedule_categories())
        ruleset_meta = ruleset_meta or {"effective_from": "2011-04-01", "effective_to": None}

        deferred: list[CompiledRule] = []
        results: dict[str, RuleResult] = {}

        for rule in self.rules:
            if _has_call(rule.condition_ast, "get_fields_for_blockers"):
                deferred.append(rule)
                continue
            results[rule.rule_id] = self._evaluate_one(rule, product, scan_date, system, ruleset_meta, [])

        blocker_confidences = self._collect_blocker_confidences(results, product)

        for rule in deferred:
            results[rule.rule_id] = self._evaluate_one(
                rule, product, scan_date, system, ruleset_meta, blocker_confidences
            )

        verdict = aggregate(results)
        return ScanResult(overall_verdict=verdict, scan_date=scan_date, rule_results=results)

    def _collect_blocker_confidences(
        self, results: dict[str, RuleResult], product: dict[str, Any]
    ) -> list[float]:
        confidences: list[float] = []
        for rule in self.rules:
            result = results.get(rule.rule_id)
            if result is None:
                continue
            if result.severity != Severity.BLOCKER:
                continue
            if result.status in (RuleStatus.NOT_APPLICABLE, RuleStatus.NOT_IN_FORCE):
                continue
            for path in referenced_field_paths(rule.condition_ast):
                confidences.append(_field_confidence(product, path))
        return confidences

    def _evaluate_one(
        self,
        rule: CompiledRule,
        product: dict[str, Any],
        scan_date: str,
        system: dict[str, Any],
        ruleset_meta: dict[str, Any],
        blocker_confidences: list[float],
    ) -> RuleResult:
        severity = Severity(rule.severity)

        if not rule.exempt_from_effective_gate and not (
            rule.effective_from <= scan_date and (rule.effective_to is None or scan_date <= rule.effective_to)
        ):
            return RuleResult(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=severity,
                status=RuleStatus.NOT_IN_FORCE,
                on_fail_code=None,
                message=f"Rule not in force on {scan_date} (effective {rule.effective_from} to {rule.effective_to or 'present'}).",
                legal_basis=rule.legal_basis,
                citation_verified=rule.citation_verified,
            )

        ctx = DslContext(product, system, ruleset_meta, blocker_confidences=blocker_confidences)

        try:
            applicable = evaluate(rule.applicable_when_ast, ctx)
        except UnknownValue:
            # A field the applicability gate needs (e.g. sticker_detected,
            # commodity.is_exempt) is absent -- treated as "gate condition not
            # met" (NOT_APPLICABLE), matching how a CV pipeline that runs
            # commodity classification on every scan represents "no, this
            # doesn't apply" rather than "unknown." A product with literally
            # zero commodity classification is outside the pipeline's realistic
            # output space; see the TC-M009/TC-M015 fixture notes.
            applicable = False

        if not applicable:
            return RuleResult(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=severity,
                status=RuleStatus.NOT_APPLICABLE,
                on_fail_code=None,
                message="Rule is not applicable to this product.",
                legal_basis=rule.legal_basis,
                citation_verified=rule.citation_verified,
            )

        try:
            passed = evaluate(rule.condition_ast, ctx)
            if passed:
                status = RuleStatus.PASS
                message = f"{rule.description} -- condition satisfied."
            elif rule.on_fail_code == "NEEDS_REVIEW":
                # UNCERTAINTY-category trust gates (LM-U01/LM-U02) never assert
                # non-compliance themselves -- a failed gate means "uncertain,"
                # not "violation." Driven entirely by the rule's own on_fail_code.
                status = RuleStatus.REVIEW
                message = f"{rule.description} -- condition failed, routed to review."
            else:
                status = RuleStatus.FAIL
                message = f"{rule.description} -- condition failed."
        except UnknownValue as exc:
            status = RuleStatus.REVIEW
            message = f"{rule.description} -- could not evaluate, unknown value at {exc.path!r}."
            return RuleResult(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=severity,
                status=status,
                on_fail_code="NEEDS_REVIEW",
                message=message,
                legal_basis=rule.legal_basis,
                citation_verified=rule.citation_verified,
            )

        if rule.confidence_policy != "structural" and status in (RuleStatus.PASS, RuleStatus.FAIL):
            paths = referenced_field_paths(rule.condition_ast)
            confidences = [_field_confidence(product, p) for p in paths]
            if confidences and min(confidences) < rule.min_field_confidence:
                status = RuleStatus.REVIEW
                message = (
                    f"{rule.description} -- field confidence "
                    f"{min(confidences):.2f} below required {rule.min_field_confidence:.2f}."
                )

        return RuleResult(
            rule_id=rule.rule_id,
            category=rule.category,
            severity=severity,
            status=status,
            on_fail_code=rule.on_fail_code if status in (RuleStatus.FAIL, RuleStatus.REVIEW) else None,
            message=message,
            legal_basis=rule.legal_basis,
            citation_verified=rule.citation_verified,
        )
