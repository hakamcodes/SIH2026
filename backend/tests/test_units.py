"""Unit conversion table -- covers CLAUDE.md defects #3 and #4.

Defect #3: the source engine's to_base_unit lower()-cased before testing
['l', 'L'], making the 'L' branch unreachable.
Defect #4: g/ml/cm all mapped to magnitude 1, so 500 g compared equal to
500 ml. to_base_unit now returns a dimension-tagged Quantity instead.
"""
from lmd.dsl.errors import UnknownValue
from lmd.dsl.registry import Quantity, to_base_unit
import pytest


def test_uppercase_l_is_reachable():
    assert to_base_unit(1, "L").dimension == "volume"
    assert to_base_unit(1, "L").magnitude == 1000.0


def test_lowercase_l_matches_uppercase():
    assert to_base_unit(1, "l").magnitude == to_base_unit(1, "L").magnitude


def test_unknown_unit_raises_instead_of_passthrough():
    with pytest.raises(UnknownValue):
        to_base_unit(500, "furlong")


def test_none_unit_raises():
    with pytest.raises(UnknownValue):
        to_base_unit(500, None)


def test_500_g_never_equals_500_ml():
    mass = to_base_unit(500, "g")
    volume = to_base_unit(500, "ml")
    assert mass != volume
    with pytest.raises(UnknownValue):
        mass <= volume


def test_cross_dimension_subtraction_raises():
    with pytest.raises(UnknownValue):
        to_base_unit(500, "g") - to_base_unit(500, "ml")


def test_same_dimension_comparison_works():
    assert to_base_unit(1, "kg") <= to_base_unit(1200, "g")
    assert not (to_base_unit(1, "kg") <= to_base_unit(500, "g"))


def test_quantity_division_by_zero_raises():
    with pytest.raises(UnknownValue):
        100 / Quantity("mass", 0)
