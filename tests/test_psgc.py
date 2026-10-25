#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""load_table: a datafile that doesn't fit its layout fails loudly, rather than losing rows."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from ph_psgc_shape import psgc
from ph_psgc_shape.psgc_data import AddedRow, Layout
from ph_psgc_shape.release import NameFix

COLUMNS = ("psgc_code", "name", "corr_code", "geo_level")
DISTRICT = "NCR, Second District (Not a Province)"


def release(district_codes=(), add_rows=()):
    """A publication with the four required columns and these corrections (named release, as before)."""
    layout = Layout(columns=COLUMNS, district_codes=tuple(district_codes), add_rows=tuple(add_rows))
    return SimpleNamespace(id="t", folder=Path("t"), layout=layout)


def load(monkeypatch, rows, rel=None, ncols=4):
    """load_table over these rows, as psgc.csv would give them: text, and NaN for an empty cell."""
    text = [[None if v is None else str(v) for v in row] for row in rows]
    raw = pd.DataFrame(text, columns=[str(i) for i in range(ncols)], dtype="str")
    monkeypatch.setattr(psgc, "read_csv", lambda *_: raw)
    return psgc.load_table(rel or release())


def fails(monkeypatch, rows, match, **kwargs):
    with pytest.raises(psgc.PsgcTableError, match=match):
        load(monkeypatch, rows, **kwargs)


def test_a_column_count_that_differs_fails(monkeypatch):
    fails(monkeypatch, [[1300000000, "NCR", None, "Reg", None]], "5 columns, the layout names 4", ncols=5)


def test_blank_and_footnote_rows_are_dropped(monkeypatch):
    rows = [
        [1300000000, "NCR", None, "Reg"],
        [None, None, None, None],
        ["As noted by the PSA Board, …", None, None, None],
    ]
    assert load(monkeypatch, rows)["psgc_code"].tolist() == [1300000000]


def test_zero_padded_codes_become_ints(monkeypatch):
    df = load(monkeypatch, [[1300000000, "NCR", None, "Reg"], ["0990100000", "City of Isabela", "099700000", None]])
    assert df["psgc_code"].tolist() == [1300000000, 990100000]


def test_corr_code_is_a_float_as_the_matching_passes_expect(monkeypatch):
    df = load(monkeypatch, [[1300000000, "NCR", "130000000", "Reg"], [1999908008, "Tapodoc", None, "Bgy"]])
    assert df["corr_code"].dtype == "float64" and df["corr_code"].iloc[0] == 130000000.0
    assert pd.isna(df["corr_code"].iloc[1])


@pytest.mark.parametrize("code", [None, "PH13", 13.5])
def test_a_named_row_without_a_numeric_code_fails(monkeypatch, code):
    fails(monkeypatch, [[1300000000, "NCR", None, "Reg"], [code, "Somewhere", None, "Bgy"]], "no numeric code")


def test_district_codes_set_the_code_of_the_named_row(monkeypatch):
    df = load(monkeypatch, [[None, DISTRICT, 137400000, "Dist"]], rel=release(district_codes=[(DISTRICT, 1307400000)]))
    assert df["psgc_code"].tolist() == [1307400000]


@pytest.mark.parametrize("copies", [0, 2])
def test_a_district_name_that_isnt_exactly_one_row_fails(monkeypatch, copies):
    rows = [[1300000000, "NCR", None, "Reg"]] + [[None, DISTRICT, None, "Dist"]] * copies
    fails(monkeypatch, rows, f"matches {copies} rows", rel=release(district_codes=[(DISTRICT, 1307400000)]))


def test_add_rows_appends_the_rows(monkeypatch):
    rel = release(add_rows=[AddedRow(code=1307400000, name=DISTRICT, geo_level="Dist")])
    df = load(monkeypatch, [[1300000000, "NCR", None, "Reg"]], rel=rel)
    assert df[["psgc_code", "geo_level"]].values.tolist() == [[1300000000, "Reg"], [1307400000, "Dist"]]


def test_an_added_code_already_in_the_datafile_fails(monkeypatch):
    rel = release(add_rows=[AddedRow(code=1300000000, name="NCR", geo_level="Reg")])
    fails(monkeypatch, [[1300000000, "NCR", None, "Reg"]], "already in the datafile", rel=rel)


LUCENA = [[431200000, "City of Lucenaa/", "045624000", "City"], [400000000, "Region IV-A", None, "Reg"]]


def test_a_name_correction_replaces_psas_name(monkeypatch):
    raw = pd.DataFrame([[str(v) if v is not None else None for v in r] for r in LUCENA], columns=["0", "1", "2", "3"])
    monkeypatch.setattr(psgc, "read_csv", lambda *_: raw)
    df = psgc.load_table(release(), [NameFix(431200000, "City of Lucena")])
    assert df.set_index("psgc_code").loc[431200000, "name"] == "City of Lucena"
    assert df.set_index("psgc_code").loc[400000000, "name"] == "Region IV-A"


def test_a_name_correction_for_a_code_not_in_the_table_fails(monkeypatch):
    raw = pd.DataFrame([[str(v) if v is not None else None for v in r] for r in LUCENA], columns=["0", "1", "2", "3"])
    monkeypatch.setattr(psgc, "read_csv", lambda *_: raw)
    with pytest.raises(psgc.PsgcTableError, match="names: 431200001 matches 0 rows"):
        psgc.load_table(release(), [NameFix(431200001, "City of Lucena")])
