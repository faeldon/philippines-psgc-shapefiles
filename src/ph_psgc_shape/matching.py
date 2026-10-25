#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""The adm4 matching passes: each moves more source barangays onto the PSGC code PSA gives them.

run_passes runs them in order, printing a stage header before each pass and a match report after it.
Each pass works from the rows the report before it left unmatched, and changes bgysubmuns_gdf's
psgc_code (and parent pcodes) in place.
"""
from __future__ import annotations

import numpy as np

from .debug import debug_bgy_log, report_nulls
from .overrides import apply_bgysubmuns_overrides, recoded, update_bgysubmuns_psgc_code
from .psgc import PSGC_COLUMNS

# The columns of the joined frame, in the order the match reports and adm4's output read them.
JOINED_COLUMNS = PSGC_COLUMNS + [
    "adm4_pcode",
    "adm4_en",
    "adm3_pcode",
    "adm3_en",
    "bgy_adm3_pcode",
    "bgy_adm3_en",
    "adm2_pcode",
    "adm2_en",
    "bgy_adm2_pcode",
    "bgy_adm2_en",
    "adm1_pcode",
    "adm1_en",
    "adm0_pcode",
    "adm0_en",
    "shape_len",
    "shape_area",
    "shape_sqkm",
    "geometry",
]


def _prefix(code):
    """The first five digits of a 10-digit PSGC code: region, province or district."""
    return str(code).zfill(10)[:5]


def debug_log(release, psgc_df, bgysubmuns_gdf, unmatched_psgc_df=None, unmatched_shape_df=None):
    """Log the release's debug barangay, if it names one."""
    if release.debug is not None:
        debug_bgy_log(release.debug.barangay, psgc_df, bgysubmuns_gdf, unmatched_psgc_df, unmatched_shape_df)


def report(joined, bgysubmuns_gdf, psgc_df, release, report_table=False):
    """Print the match report for a joined frame; return its unmatched PSGC rows and unmatched shapes."""
    report_nulls(
        joined, column_name="adm4_en", report_table=report_table, explained=release.bgysubmuns.shapeless.keys()
    )
    unmatched_psgc_df = joined[joined["adm4_en"].isnull()]
    unmatched_shape_df = joined[joined["name"].isnull()]
    debug_log(release, psgc_df, bgysubmuns_gdf, unmatched_psgc_df, unmatched_shape_df)
    return unmatched_psgc_df, unmatched_shape_df


def match_report(bgysubmuns_gdf, psgc_df, release, report_table=False):
    """Join on PSGC code and report; return the joined frame and its unmatched PSGC rows and shapes."""
    joined = bgysubmuns_gdf.merge(psgc_df, on="psgc_code", how="outer")
    return (joined, *report(joined, bgysubmuns_gdf, psgc_df, release, report_table))


def exact_code_and_name(bgysubmuns_gdf, psgc_df):
    """Stage 0: the rows whose PSGC code and name both match, as a joined frame."""
    joined = bgysubmuns_gdf.merge(
        psgc_df, left_on=["psgc_code", "adm4_en"], right_on=["psgc_code", "name"], how="outer"
    )
    return joined[JOINED_COLUMNS]


def match_old_code(bgysubmuns_gdf, unmatched_psgc_df, unmatched_shape_df, release):
    """Stage 2: move a shape onto an unmatched PSGC row whose old code (corr_code) it carries.

    The old code is recoded as the source's codes were (apply_recodes), so a barangay of a transferred
    province still finds its shape. Skips old Manila, whose barangays are matched by name in stage 5.
    """
    manila_old = release.bgysubmuns.manila.old // 100_000
    for _, row in unmatched_psgc_df.iterrows():
        if np.isnan(row["corr_code"]):
            print(f"{row['name']} skipped because corr_code is nan")
            continue
        corr_code = int(row["corr_code"])
        new_psgc_code = row["psgc_code"]
        old_psgc_code = recoded(((corr_code // 10_000_000) * 100_000_000) + corr_code % 10_000_000, release.recodes)
        with_old_psgc_code = unmatched_shape_df[unmatched_shape_df["psgc_code"] == old_psgc_code]
        if with_old_psgc_code.shape[0] == 1:
            if old_psgc_code // 100_000 != manila_old:
                update_bgysubmuns_psgc_code(bgysubmuns_gdf, old_psgc_code, new_psgc_code)
        elif with_old_psgc_code.shape[0] > 1:
            print(f"{row['name']} skipped because multiple match found for old PSGC code {old_psgc_code}")
            print(with_old_psgc_code.head())


def _name_matches(series, name):
    """Rows of series equal to name, containing it, or contained in it."""
    return (series == name) | series.str.contains(name, regex=False) | series.apply(lambda x: x in name)


def match_psgc_rows_by_muni_name(bgysubmuns_gdf, unmatched_psgc_df, release):
    """Stage 3a: move the one shape whose barangay and municipality names fit an unmatched PSGC row."""
    debug_psgc = release.debug.psgc if release.debug is not None else None
    for _, row in unmatched_psgc_df.dropna(subset=["bgy_adm3_en"]).iterrows():
        bgy_name = row["name"].strip()
        bgy_adm3_en = row["bgy_adm3_en"].strip()
        new_psgc_code = row["psgc_code"]
        exact_muni = bgysubmuns_gdf[
            _name_matches(bgysubmuns_gdf["adm4_en"], bgy_name) & _name_matches(bgysubmuns_gdf["adm3_en"], bgy_adm3_en)
        ]
        if exact_muni.shape[0] == 1:
            old_psgc_code = exact_muni.iloc[0]["psgc_code"]
            if old_psgc_code == debug_psgc:
                print("Change here 1!")
                print(new_psgc_code)
                print(bgy_name, exact_muni.iloc[0]["adm4_en"])
                print(bgy_adm3_en, exact_muni.iloc[0]["adm3_en"])
            update_bgysubmuns_psgc_code(bgysubmuns_gdf, old_psgc_code, new_psgc_code, exact_muni.iloc[0]["adm4_en"])
        elif exact_muni.shape[0] > 1:
            print(f"{row['name']} skipped because multiple match found")


def match_shapes_by_muni_name(bgysubmuns_gdf, psgc_df, unmatched_shape_df):
    """Stage 3b: move an unmatched shape onto the one PSGC row with its barangay name and municipality."""
    psgc_df_with_adm3_en = psgc_df.dropna(subset=["bgy_adm3_en"])
    for _, row in unmatched_shape_df.iterrows():
        bgy_name = row["adm4_en"].strip()
        mun_name = row["adm3_en"].replace("-", " ").strip()  # Sultan Kudarat has a dash
        exact_muni = psgc_df_with_adm3_en[
            (psgc_df_with_adm3_en["name"] == bgy_name) & _name_matches(psgc_df_with_adm3_en["bgy_adm3_en"], mun_name)
        ]
        if exact_muni.shape[0] == 1:
            update_bgysubmuns_psgc_code(bgysubmuns_gdf, row["psgc_code"], exact_muni.iloc[0]["psgc_code"])
        elif exact_muni.shape[0] > 1:
            print(f"{bgy_name} skipped because multiple match found")


def remap_sga(bgysubmuns_gdf, unmatched_shape_df, release):
    """Stage 4: move unmatched Special Geographic Area shapes from the source's prefix to PSGC's."""
    from_prefix, to_prefix = release.bgysubmuns.sga_from_prefix, release.bgysubmuns.sga_to_prefix
    for _, row in unmatched_shape_df.iterrows():
        if str(row["psgc_code"]).startswith(from_prefix):
            old_psgc_code = row["psgc_code"]
            new_psgc_code = int(to_prefix + str(row["psgc_code"])[len(from_prefix) :])
            update_bgysubmuns_psgc_code(bgysubmuns_gdf, old_psgc_code, new_psgc_code)


def match_adm3_en(bgysubmuns_gdf, unmatched_psgc_df, release):
    """Stage 5: move the one shape with an unmatched PSGC row's name in its municipality, or in old Manila."""
    manila = _prefix(release.bgysubmuns.manila.city)
    manila_old = _prefix(release.bgysubmuns.manila.old)
    for _, row in unmatched_psgc_df.iterrows():
        new_psgc_code = row["psgc_code"]
        new_psgc_code_str = str(new_psgc_code).zfill(10)
        name = row["name"]
        codes = bgysubmuns_gdf["psgc_code"].astype(str).str.zfill(10)
        same_name = bgysubmuns_gdf["adm4_en"] == name
        match_df = bgysubmuns_gdf[
            # Municipality match and same name
            (codes.str.startswith(new_psgc_code_str[:7]) & same_name)
            # Region match and same name in NCR: a City of Manila barangay found under old Manila
            | (new_psgc_code_str.startswith(manila) & codes.str.startswith(manila_old) & same_name)
        ]
        if match_df.shape[0] > 1:
            print(f"Skipping due to multiple matches for {name} [{new_psgc_code}]")
            print(match_df[["psgc_code", "adm4_pcode", "adm4_en", "adm3_en", "adm2_en", "adm1_en"]].head())
            continue
        if match_df.shape[0] == 1:  # Match found
            update_bgysubmuns_psgc_code(bgysubmuns_gdf, match_df.iloc[0]["psgc_code"], new_psgc_code, name)


def run_passes(bgysubmuns_gdf, psgc_df, release):
    """Run the matching passes in order, reporting after each; return the final joined frame."""
    debug_log(release, psgc_df, bgysubmuns_gdf)

    print("==== STAGE 0: PSGC code and name exact match =====")
    report(exact_code_and_name(bgysubmuns_gdf, psgc_df), bgysubmuns_gdf, psgc_df, release)

    print("==== STAGE 1: PSGC code match with correction =====")
    apply_bgysubmuns_overrides(bgysubmuns_gdf, release.bgysubmuns.overrides)
    _, unmatched_psgc_df, unmatched_shape_df = match_report(bgysubmuns_gdf, psgc_df, release)

    print("==== STAGE 2: Corresponce code and name exact match =====")
    match_old_code(bgysubmuns_gdf, unmatched_psgc_df, unmatched_shape_df, release)
    _, unmatched_psgc_df, unmatched_shape_df = match_report(bgysubmuns_gdf, psgc_df, release)

    print("==== STAGE 3: Municipality name exact match =====")
    match_psgc_rows_by_muni_name(bgysubmuns_gdf, unmatched_psgc_df, release)
    match_shapes_by_muni_name(bgysubmuns_gdf, psgc_df, unmatched_shape_df)
    _, unmatched_psgc_df, unmatched_shape_df = match_report(bgysubmuns_gdf, psgc_df, release)

    print("==== STAGE 4: Special Geographic Areas =====")
    remap_sga(bgysubmuns_gdf, unmatched_shape_df, release)
    _, unmatched_psgc_df, unmatched_shape_df = match_report(bgysubmuns_gdf, psgc_df, release)

    print("==== STAGE 5: Municipality/Province/Metro Manila exact and name exact match =====")
    match_adm3_en(bgysubmuns_gdf, unmatched_psgc_df, release)
    joined, _, _ = match_report(bgysubmuns_gdf, psgc_df, release, report_table=True)
    return joined
