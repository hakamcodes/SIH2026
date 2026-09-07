"""Proves the DSL cannot execute arbitrary code and refuses unsafe syntax at load time.

Per CLAUDE.md invariant #2: no eval/exec/compile, no attribute access, no
subscripts, no comprehensions, no lambdas, no dunder access. A rule that
violates this must refuse to load, not degrade silently.
"""
from pathlib import Path

import pytest
from lmd.dsl.compiler import compile_condition
from lmd.dsl.errors import DslLoadError
from lmd.dsl.normalize import normalize


def _refuses(raw: str):
    with pytest.raises(DslLoadError):
        compile_condition(normalize(raw))


def test_refuses_dunder_attribute_access():
    _refuses("field('x').__class__.__bases__")


def test_refuses_subscript():
    _refuses("field('x')[0] == 1")


def test_refuses_lambda():
    with pytest.raises(DslLoadError):
        compile_condition("(lambda: True)()")


def test_refuses_list_comprehension():
    with pytest.raises(DslLoadError):
        compile_condition("[x for x in [1,2,3]]")


def test_refuses_import_statement_smuggled_as_expr():
    with pytest.raises(DslLoadError):
        compile_condition("__import__('os').system('echo pwned')")


def test_refuses_unknown_function_name():
    _refuses("nonexistent_function(net_quantity.value)")


def test_refuses_bare_identifier_outside_call():
    with pytest.raises(DslLoadError):
        compile_condition("some_bare_name")


def test_refuses_keyword_arguments_in_call():
    with pytest.raises(DslLoadError):
        compile_condition("exists(x=field('net_quantity.value'))")


def test_accepts_all_24_real_rule_conditions():
    import json

    rules_path = (
        Path(__file__).resolve().parents[2]
        / "research"
        / "NotebookLM"
        / "machine-readable-compliance-rules.json"
    )
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    assert len(rules) == 28
    for rule in rules:
        for key in ("applicable_when", "condition"):
            compile_condition(normalize(rule[key]))  # must not raise


def test_reachable_callable_set_is_exactly_sixteen_names():
    """CLAUDE.md invariant #2: the reachable set is twelve names in
    dsl.registry.FUNCTIONS plus four evaluator-level special forms that
    need lazy/context-bound semantics a plain table entry can't express
    (exists, is_null, coalesce, get_fields_for_blockers). Pinning the exact
    set here means a fifteenth (or seventeenth) name added anywhere is a
    deliberate, reviewed change to this test, not a silent expansion of
    what a rule file can call.
    """
    from lmd.dsl.registry import FUNCTIONS

    assert set(FUNCTIONS.keys()) == {
        "to_base_unit", "round_mrp_paise", "is_numeric", "is_valid_calendar_date",
        "count_distinct", "min_confidence", "matches_regex", "contains_phrase",
        "get_standard_sizes", "abs", "max", "min",
    }
    evaluator_source = (
        Path(__file__).resolve().parents[1] / "lmd" / "dsl" / "evaluator.py"
    ).read_text(encoding="utf-8")
    for special_form in ("exists", "is_null", "coalesce", "get_fields_for_blockers"):
        assert f'"{special_form}"' in evaluator_source
