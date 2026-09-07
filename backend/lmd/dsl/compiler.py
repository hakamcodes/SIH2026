"""Load-time AST validation. Never calls eval, exec, or compile.

Per CLAUDE.md invariant #2: validation happens via ast.parse(mode="eval")
plus a node whitelist. No attribute access, no subscripts, no comprehensions,
no lambdas, no dunder access. A rule file that violates this refuses to load.
"""
from __future__ import annotations

import ast

from .errors import DslLoadError
from .normalize import _KNOWN_CALL_NAMES

_ALLOWED_NODE_TYPES = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.USub,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Call,
    ast.Load,
    ast.Constant,
    ast.List,
    ast.Name,
)


def _validate(node: ast.AST) -> None:
    if not isinstance(node, _ALLOWED_NODE_TYPES):
        raise DslLoadError(
            f"disallowed syntax node {type(node).__name__} -- refusing to load"
        )

    if isinstance(node, ast.Name):
        parent_is_call_func = getattr(node, "_is_call_func", False)
        if not parent_is_call_func:
            raise DslLoadError(
                f"bare identifier {node.id!r} outside a function call -- refusing to load"
            )
        if node.id not in _KNOWN_CALL_NAMES:
            raise DslLoadError(f"unknown function {node.id!r} -- refusing to load")

    if isinstance(node, ast.Constant) and not isinstance(node.value, (str, int, float, bool)) and node.value is not None:
        raise DslLoadError("only str/int/float/bool/None constants are allowed")

    if isinstance(node, ast.Call):
        if node.keywords:
            raise DslLoadError("keyword arguments are not allowed in DSL calls")
        node.func._is_call_func = True  # type: ignore[attr-defined]

    for child in ast.iter_child_nodes(node):
        _validate(child)


def compile_condition(normalized_source: str) -> ast.Expression:
    try:
        tree = ast.parse(normalized_source, mode="eval")
    except SyntaxError as exc:
        raise DslLoadError(f"syntax error in condition: {exc}") from exc
    _validate(tree)
    return tree
