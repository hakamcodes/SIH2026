"""Error types for the rule DSL. No exception here ever wraps eval/exec/compile output."""


class DslLoadError(Exception):
    """Raised at rule-load time when a condition string fails the AST whitelist."""


class UnknownValue(Exception):
    """Raised during evaluation when a comparison or computation touches a MISSING field.

    Per CLAUDE.md invariant #6: an absent field must never silently look like a
    passing or failing condition. Any rule that raises this maps to REVIEW.
    """

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"unknown value at path {path!r}")
