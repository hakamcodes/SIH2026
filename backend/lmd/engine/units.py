"""Thin re-export of the dimension-safe unit machinery for non-DSL callers
(e.g. a future CV pipeline stage that needs to convert a raw OCR unit
without going through a rule condition)."""
from lmd.dsl.registry import Quantity, to_base_unit

__all__ = ["Quantity", "to_base_unit"]
