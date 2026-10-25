#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""A new quarter is a new release file and publication: its layout and its overrides take effect with no code change."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ph_psgc_shape import psgc, psgc_data
from ph_psgc_shape.overrides import apply_municities_overrides
from ph_psgc_shape.release import load_release

FIXTURES = Path(__file__).parent / "fixtures"
NEXT = load_release(FIXTURES / "releases" / "next.toml", check_paths=False)


@pytest.fixture
def next_publication(monkeypatch):
    monkeypatch.setattr(psgc_data, "DATA_PSGC", FIXTURES / "psgc")


def test_datafile_layout_comes_from_the_publication(next_publication):
    # The next publication's datafile has a blank first column; 2023-4q's 13 names would be one off.
    df = psgc.load_psgc_table(NEXT)
    assert (df["psgc_code"].iloc[0], df["name"].iloc[0]) == (102801000, "Adams")
    assert len(df) == 5  # Adams and the four added districts; the empty row is dropped
    assert "_blank" not in df.columns


def test_the_added_override_moves_its_row():
    gdf = pd.DataFrame({"psgc_code": [102801000], "adm3_pcode": "P0102801", "adm2_pcode": "P01028"})
    apply_municities_overrides(gdf, NEXT.municities.overrides)
    assert gdf["psgc_code"].tolist() == [102899000]


def test_the_publication_adds_the_rows_its_datafile_lacks(next_publication):
    df = psgc.load_psgc_table(NEXT)
    assert df.loc[df["geo_level"] == "Dist", "psgc_code"].tolist() == [1303900000, 1307400000, 1307500000, 1307600000]
