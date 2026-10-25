#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""plot_traverse: bearings read as the laws write them, traverses close, and a fit finds a placed shape."""
from __future__ import annotations

import pytest
from shapely.geometry import Polygon, box

import plot_traverse as pt


@pytest.mark.parametrize(
    ("bearing", "azimuth"),
    [
        ("N 00°00' E", 0.0),
        ("N 45°30' E", 45.5),
        ("S 46°01' W", 226.0 + 1 / 60),
        ("N 89°24' W", 270.6),
        ("Due South", 180.0),
    ],
)
def test_bearings_are_read_as_azimuths(bearing, azimuth):
    assert pt.azimuth(bearing) == pytest.approx(azimuth)


def test_a_bearing_not_in_the_canonical_form_fails():
    with pytest.raises(ValueError, match="not a bearing"):
        pt.azimuth("S 67 04 E")


SQUARE = [("Due East", 100.0), ("Due South", 100.0), ("Due West", 100.0), ("Due North", 100.0)]


def test_a_square_traverse_closes_with_its_area():
    corners, closure = pt.plot(("Due North", 50.0), SQUARE)
    assert closure == pytest.approx(0.0, abs=1e-9)
    assert corners[0] == pytest.approx((0.0, 50.0))
    assert Polygon(corners).area == pytest.approx(10_000.0)


def test_an_open_traverse_reports_its_closure_error():
    _, closure = pt.plot(("Due North", 50.0), SQUARE[:3] + [("Due North", 90.0)])
    assert closure == pytest.approx(10.0)


def test_the_iou_fit_finds_a_shifted_and_rotated_shape():
    shape = Polygon([(0, 0), (300, 0), (300, 100), (120, 100), (120, 250), (0, 250)])
    mothers = pt.place(shape, 1.0, 5000.0, 7000.0)
    (theta, dx, dy), _ = pt.fit_iou(shape, mothers)
    assert theta == pytest.approx(1.0, abs=0.05)
    assert (dx, dy) == pytest.approx((5000.0, 7000.0), abs=3.0)


def test_clipping_gives_overlaps_to_the_first_and_leftovers_to_a_neighbour():
    mothers = box(0, 0, 100, 10)
    a, b = box(-5, 0, 60, 10), box(50, 0, 95, 10)  # they overlap on 50–60, and leave 95–100 uncovered
    clipped = pt.clip_group([a, b], mothers)
    assert clipped[0].equals(box(0, 0, 60, 10))
    assert clipped[1].area == pytest.approx(400.0)
    assert clipped[0].union(clipped[1]).symmetric_difference(mothers).area < pt.COVER_TOLERANCE
