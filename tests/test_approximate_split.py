#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""approximate_split: one straight cut, on the side the rule names, sized to its target."""
from __future__ import annotations

import pytest
from shapely.geometry import Point, box

import approximate_split as ap

MOTHER = box(0, 0, 400, 100)  # long axis east–west


def test_a_cut_meets_its_target_and_stays_inside_its_mother():
    part = ap.cut(MOTHER, (1.0, 0.0), 10_000.0)
    assert part.area == pytest.approx(10_000.0, rel=ap.AREA_TOLERANCE)
    assert part.difference(MOTHER).area == pytest.approx(0.0)
    assert part.bounds[0] == pytest.approx(300.0, abs=0.01)  # the east end, beyond x = 300


def test_the_long_axis_points_away_from_the_city():
    assert ap.long_axis(MOTHER, Point(-1000, 50)) == pytest.approx((1.0, 0.0))
    assert ap.long_axis(MOTHER, Point(5000, 50)) == pytest.approx((-1.0, 0.0))


def test_a_cut_is_the_same_every_time():
    assert ap.cut(MOTHER, ap.unit(1, 1), 7_500.0).equals_exact(ap.cut(MOTHER, ap.unit(1, 1), 7_500.0), 0.0)
