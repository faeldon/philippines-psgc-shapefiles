#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""fix_adm4_parents: every adm4 parent code points at a row that exists in the level above."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ph_psgc_shape.levels import fix_adm4_parents
from ph_psgc_shape.release import load_release

RELEASE = load_release(Path(__file__).parent.parent / "releases" / "2023-4q.toml", check_paths=False)

ROWS = [
    # psgc_code, name, geo_level, adm1, adm2, adm3
    (1380601000, "Tondo I/II", "SubMun", 0, 0, 0),
    (1380601001, "Barangay 1", "Bgy", 1300000000, 1380600000, 1380601000),
    (1303901900, "Barangay 900", "Bgy", 1300000000, 1303900000, 1303901000),
    (1303901906, None, None, 1300000000, 1303900000, 1303901000),
    (330101001, "Agapito del Rosario", "Bgy", 300000000, 330100000, 330100000),
    (1381701001, "Aguho", "Bgy", 1300000000, 1381700000, 1381701000),
    (102801001, "Adams", "Bgy", 100000000, 102800000, 102801000),
]


def frame():
    return pd.DataFrame(ROWS, columns=["psgc_code", "name", "geo_level", "adm1_psgc", "adm2_psgc", "adm3_psgc"])


def row(df, code):
    return df[df["psgc_code"] == code].iloc[0]


def test_sub_municipality_goes_under_manila():
    df = frame()
    fix_adm4_parents(df, RELEASE)
    r = row(df, 1380601000)
    assert (r["adm1_psgc"], r["adm2_psgc"], r["adm3_psgc"]) == (1300000000, 1303900000, 1380600000)


def test_barangays_of_a_sub_municipality_or_old_manila_go_under_manila():
    df = frame()
    fix_adm4_parents(df, RELEASE)
    for code in (1380601001, 1303901900, 1303901906):
        assert (row(df, code)["adm2_psgc"], row(df, code)["adm3_psgc"]) == (1303900000, 1380600000)


def test_city_barangays_get_the_citys_province_or_district():
    df = frame()
    fix_adm4_parents(df, RELEASE)
    assert row(df, 330101001)["adm2_psgc"] == 305400000  # Angeles → Pampanga
    assert row(df, 1381701001)["adm2_psgc"] == 1307600000  # Pateros → NCR Fourth District


def test_non_barangay_areas_get_their_source_names():
    df = frame()
    fix_adm4_parents(df, RELEASE)
    assert row(df, 1303901906)["name"] == "Manila North Cemetery"


def test_a_barangay_without_a_shape_takes_its_parents_from_its_code():
    # Angoyao (Marawi, 2024): a PSGC row with no source shape, so the join gave it no parents.
    df = pd.concat([frame(), pd.DataFrame([(1903617146, "Angoyao", "Bgy", 0, 0, 0)], columns=frame().columns)])
    fix_adm4_parents(df, RELEASE)
    assert row(df, 1903617146)[["adm1_psgc", "adm2_psgc", "adm3_psgc"]].tolist() == [
        1900000000,
        1903600000,
        1903617000,
    ]


def test_ordinary_barangay_is_untouched():
    df = frame()
    before = row(df, 102801001).copy()
    fix_adm4_parents(df, RELEASE)
    assert row(df, 102801001).equals(before)
