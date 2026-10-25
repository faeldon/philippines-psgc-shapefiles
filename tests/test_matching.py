#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Each adm4 matching pass matches a row the passes before it left unmatched."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from ph_psgc_shape import matching
from ph_psgc_shape.release import Recode, load_release

RELEASE = load_release(Path(__file__).parent.parent / "releases" / "2023-4q.toml", check_paths=False)
SOURCE_COLUMNS = ["adm2_en", "adm1_pcode", "adm1_en", "adm0_pcode", "adm0_en", "shape_len", "shape_area"]


def shapes(*rows):
    """A source adm4 frame from (psgc_code, adm4_en, adm3_en) rows."""
    df = pd.DataFrame(rows, columns=["psgc_code", "adm4_en", "adm3_en"])
    df["adm4_pcode"] = "PH" + df["psgc_code"].astype(str).str.zfill(10)
    df["adm3_pcode"] = df["adm4_pcode"].str[:9]
    df["adm2_pcode"] = df["adm4_pcode"].str[:7]
    for col in SOURCE_COLUMNS + ["shape_sqkm"]:
        df[col] = None
    df["geometry"] = None
    return df


def table(*rows):
    """A barangay table from (psgc_code, name, corr_code, bgy_adm3_en) rows."""
    df = pd.DataFrame(rows, columns=["psgc_code", "name", "corr_code", "bgy_adm3_en"])
    df["corr_code"] = df["corr_code"].astype(float)
    df["geo_level"] = None
    df["bgy_adm3_pcode"] = df["bgy_adm2_pcode"] = df["bgy_adm2_en"] = None
    return df


def unmatched(gdf, psgc_df):
    """The unmatched PSGC rows and shapes after joining on code, as each pass receives them."""
    _, unmatched_psgc, unmatched_shape = matching.match_report(gdf, psgc_df, RELEASE)
    return unmatched_psgc, unmatched_shape


def codes(gdf):
    return list(gdf["psgc_code"])


def test_exact_code_and_name_needs_both():
    gdf = shapes((102801001, "Adams", "Adams"), (102801002, "Wrong", "Adams"))
    psgc_df = table((102801001, "Adams", np.nan, "Adams"), (102801002, "Right", np.nan, "Adams"))
    joined = matching.exact_code_and_name(gdf, psgc_df)
    matched = joined.dropna(subset=["name", "adm4_en"])
    assert list(matched["psgc_code"]) == [102801001]
    assert list(joined.columns) == matching.JOINED_COLUMNS


def test_match_old_code_moves_the_shape_with_the_old_code():
    # corr_code 12801005 is the old 9-digit code 102801005 (012801005).
    gdf = shapes((102801005, "Lydia", "Adams"))
    psgc_df = table((102801009, "Lydia", 12801005, "Adams"))
    matching.match_old_code(gdf, *unmatched(gdf, psgc_df), RELEASE)
    assert codes(gdf) == [102801009]


def test_match_old_code_recodes_the_old_code_as_the_source_was():
    # Bacolod's Alangilan: OCHA's 0604501001 (under Negros Occidental), recoded to NIR's 1804501001; PSA's
    # 1830200001 carries corr_code 64501001, the old 0604501001, which the 06045 recode also moves.
    release = replace(RELEASE, recodes=(Recode("06045", "18045"),))
    gdf = shapes((1804501001, "Alangilan", "Bacolod City"))
    psgc_df = table((1830200001, "Alangilan", 64501001, "City of Bacolod"))
    matching.match_old_code(gdf, *unmatched(gdf, psgc_df), release)
    assert codes(gdf) == [1830200001]


def test_match_old_code_skips_old_manila():
    gdf = shapes((1303901005, "Barangay 5", "Tondo I/II"))
    psgc_df = table((1380601005, "Barangay 5", 133901005, "Tondo I/II"))
    matching.match_old_code(gdf, *unmatched(gdf, psgc_df), RELEASE)
    assert codes(gdf) == [1303901005]


def test_match_psgc_rows_by_muni_name():
    gdf = shapes((102801077, "Poblacion", "Adams"))
    psgc_df = table((102801009, "Poblacion", np.nan, "Adams"))
    unmatched_psgc, _ = unmatched(gdf, psgc_df)
    matching.match_psgc_rows_by_muni_name(gdf, unmatched_psgc, RELEASE)
    assert codes(gdf) == [102801009]


def test_match_shapes_by_muni_name_ignores_a_dash():
    gdf = shapes((1908712077, "Bacsil", "Sultan-Kudarat"))
    psgc_df = table((1908710009, "Bacsil", np.nan, "Sultan Kudarat"))
    _, unmatched_shape = unmatched(gdf, psgc_df)
    matching.match_shapes_by_muni_name(gdf, psgc_df, unmatched_shape)
    assert codes(gdf) == [1908710009]


def test_remap_sga():
    gdf = shapes((1909901001, "Kibayao", "Carmen Cluster"))
    psgc_df = table((1999901001, "Kibayao", np.nan, "Carmen Cluster"))
    _, unmatched_shape = unmatched(gdf, psgc_df)
    matching.remap_sga(gdf, unmatched_shape, RELEASE)
    assert codes(gdf) == [1999901001]


def test_match_adm3_en_in_the_same_municipality():
    gdf = shapes((102801077, "Lydia", "Adams"))
    psgc_df = table((102801009, "Lydia", np.nan, None))
    unmatched_psgc, _ = unmatched(gdf, psgc_df)
    matching.match_adm3_en(gdf, unmatched_psgc, RELEASE)
    assert codes(gdf) == [102801009]


def test_match_adm3_en_finds_a_city_of_manila_barangay_under_old_manila():
    gdf = shapes((1303901001, "Barangay 1", "Tondo I/II"))
    psgc_df = table((1380601001, "Barangay 1", np.nan, None))
    unmatched_psgc, _ = unmatched(gdf, psgc_df)
    matching.match_adm3_en(gdf, unmatched_psgc, RELEASE)
    assert codes(gdf) == [1380601001]


def test_run_passes_reports_after_every_stage(capsys):
    gdf = shapes((102801001, "Adams", "Adams"), (1909901001, "Kibayao", "Carmen Cluster"))
    psgc_df = table((102801001, "Adams", np.nan, "Adams"), (1999901001, "Kibayao", np.nan, "Carmen Cluster"))
    joined = matching.run_passes(gdf, psgc_df, RELEASE)
    out = capsys.readouterr().out
    assert [f"==== STAGE {n}:" in out for n in range(6)] == [True] * 6
    assert out.rstrip().count("MATCH REPORT") >= 6
    assert "MATCH REPORT: All rows matched!" in out.split("==== STAGE 5:")[1]
    assert sorted(joined["psgc_code"]) == [102801001, 1999901001]
