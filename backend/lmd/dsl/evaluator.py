"""Hand-written recursive AST walker. Never calls eval, exec, or compile.

Only the node types whitelisted by compiler.py can ever reach here, so this
module trusts its input completely -- the safety boundary is the load-time
validation, not this walker.
"""
from __future__ import annotations

import ast
from typing import Any

from . import registry
from .errors import UnknownValue

_COMPARE_OPS = {
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}

_BIN_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
}


class DslContext:
    """Resolves dotted paths against the product envelope + system/ruleset globals."""

    def __init__(
        self,
        product: dict[str, Any],
        system: dict[str, Any] | None = None,
        ruleset: dict[str, Any] | None = None,
        blocker_confidences: list[float] | None = None,
    ):
        self.product = product
        self.system = system or {}
        self.ruleset = ruleset or {}
        self.blocker_confidences = blocker_confidences or []

    def resolve(self, path: str) -> Any:
        parts = path.split(".")
        if parts[0] == "system":
            node: Any = self.system
            for part in parts[1:]:
                if not isinstance(node, dict) or part not in node:
                    raise UnknownValue(path)
                node = node[part]
            return node
        if parts[0] == "ruleset":
            node = self.ruleset
            for part in parts[1:]:
                if not isinstance(node, dict) or part not in node:
                    raise UnknownValue(path)
                node = node[part]
            return node

        node = self.product
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                raise UnknownValue(path)
            node = node[part]
        return node


def evaluate(node: ast.AST, ctx: DslContext) -> Any:
    if isinstance(node, ast.Expression):
        return evaluate(node.body, ctx)

    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.List):
        return [evaluate(e, ctx) for e in node.elts]

    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            result = True
            for value_node in node.values:
                result = evaluate(value_node, ctx)
                if not result:
                    return result
            return result
        else:  # ast.Or
            result = False
            for value_node in node.values:
                result = evaluate(value_node, ctx)
                if result:
                    return result
            return result

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return not evaluate(node.operand, ctx)
        if isinstance(node.op, ast.USub):
            return -evaluate(node.operand, ctx)
        raise UnknownValue("unsupported_unary_op")

    if isinstance(node, ast.Compare):
        left = evaluate(node.left, ctx)
        for op, comparator_node in zip(node.ops, node.comparators):
            right = evaluate(comparator_node, ctx)
            op_fn = _COMPARE_OPS[type(op)]
            if not op_fn(left, right):
                return False
            left = right
        return True

    if isinstance(node, ast.BinOp):
        left = evaluate(node.left, ctx)
        right = evaluate(node.right, ctx)
        return _BIN_OPS[type(node.op)](left, right)

    if isinstance(node, ast.Call):
        name = node.func.id  # type: ignore[union-attr]

        if name == "field":
            path = node.args[0].value  # type: ignore[attr-defined]
            return ctx.resolve(path)

        if name == "exists":
            try:
                value = evaluate(node.args[0], ctx)
            except UnknownValue:
                return False
            return value is not None

        if name == "is_null":
            try:
                value = evaluate(node.args[0], ctx)
            except UnknownValue:
                return True
            return value is None

        if name == "coalesce":
            for arg_node in node.args:
                try:
                    value = evaluate(arg_node, ctx)
                except UnknownValue:
                    continue
                if value is not None:
                    return value
            return None

        if name == "get_fields_for_blockers":
            return ctx.blocker_confidences

        args = [evaluate(a, ctx) for a in node.args]
        fn = registry.FUNCTIONS[name]
        return fn(*args)

    raise UnknownValue(f"unsupported_node:{type(node).__name__}")


def referenced_field_paths(node: ast.AST) -> list[str]:
    """Collect every dotted path passed to a field() call inside a compiled condition.

    Used by the engine to look up per-field extraction confidence for the
    min_field_confidence gate (CLAUDE.md section 5, defect: "min_field_confidence
    is present on all 28 rules but read by nothing").
    """
    paths: list[str] = []
    for child in ast.walk(node):
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == "field"
            and child.args
            and isinstance(child.args[0], ast.Constant)
        ):
            paths.append(child.args[0].value)
    return paths
