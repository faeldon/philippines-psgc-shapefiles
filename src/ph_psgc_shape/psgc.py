#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""The PSGC table every level joins to, read from a publication's committed psgc.csv (see psgc_data)."""
from __future__ import annotations

import pandas as pd

from .psgc_data import PSGC_REQUIRED_COLUMNS, load_manifest

# The PSGC table's columns kept through each level's join: the ones the levels read.
PSGC_COLUMNS = list(PSGC_REQUIRED_COLUMNS)


class PsgcTableError(ValueError):
    """A PSGC datafile that doesn't fit its publication's layout."""


def load_psgc_table(release):
    """The PSGC table of the publication the release names, with the release's name corrections (see load_table)."""
    return load_table(load_manifest(release.psgc.publication), release.psgc.names)


def read_csv(path):
    """A publication CSV as text: empty cells are NaN, and nothing else is read as missing."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def load_table(manifest, names=()):
    """Read the publication's psgc.csv: columns named by position, NCR district codes set, codes as ints.

    Drops PSA's blank and footnote rows (no name), sets each district_codes row's code, appends the
    layout's add_rows, then gives each code in names (a release's NameFix list) its corrected name.
    corr_code is read as a float, as the matching passes expect. Raises PsgcTableError if the
    datafile doesn't fit its layout: a column count that differs, a district name that isn't exactly
    one row, an added code already present, a row left without a numeric code, or a name correction
    for a code the table doesn't have.
    """
    psgc = manifest.layout
    df = read_csv(manifest.folder / "psgc.csv")

    def fail(problem):
        raise PsgcTableError(f"publication {manifest.id}: {manifest.folder / 'psgc.csv'}: {problem}")

    if len(df.columns) != len(psgc.columns):
        fail(f"the sheet has {len(df.columns)} columns, the layout names {len(psgc.columns)}")
    df.columns = list(psgc.columns)
    df = df.drop(columns=list(psgc.drop))
    df = df[df["name"].notna()].copy()

    for name, code in psgc.district_codes:
        mask = df["name"] == name
        if mask.sum() != 1:
            fail(f"district_codes: {name!r} matches {mask.sum()} rows, not 1")
        df.loc[mask, "psgc_code"] = str(code)

    codes = df["psgc_code"].map(_as_code)
    bad = codes.isna()
    if bad.any():
        first = df[bad].iloc[0]
        fail(f"{bad.sum()} rows have no numeric code, first {first['name']!r} with {first['psgc_code']!r}")
    df["psgc_code"] = codes.astype(int)
    df["corr_code"] = pd.to_numeric(df["corr_code"]).astype(float)

    for row in psgc.add_rows:
        if (df["psgc_code"] == row.code).any():
            fail(f"add_rows: {row.code} is already in the datafile")
    if psgc.add_rows:
        added = pd.DataFrame([{"psgc_code": r.code, "name": r.name, "geo_level": r.geo_level} for r in psgc.add_rows])
        df = pd.concat([df, added], ignore_index=True)
    for fix in names:
        mask = df["psgc_code"] == fix.code
        if mask.sum() != 1:
            fail(f"names: {fix.code} matches {mask.sum()} rows, not 1")
        df.loc[mask, "name"] = fix.name
    return df


def _as_code(value):
    """A PSGC code as an int, from an int, an integral float or a 9- or 10-digit string; else None."""
    if isinstance(value, str):
        return int(value) if value.isdigit() and len(value) in (9, 10) else None
    if pd.isna(value) or float(value) != int(value):
        return None
    return int(value)


def barangay_table(df):
    """The barangays and sub-municipalities of the PSGC table, each with its adm3 and adm2 code and name."""
    adm2_df = df[(df["geo_level"] == "Prov") | (df["geo_level"] == "Dist")].copy()
    adm2_df = adm2_df[["psgc_code", "name"]]
    adm2_df.columns = ["adm2_pcode", "adm2_en"]
    adm3_df = df[(df["geo_level"] == "Mun") | (df["geo_level"] == "City") | (df["geo_level"] == "SGU")].copy()
    adm3_df = adm3_df[["psgc_code", "name"]]
    adm3_df.columns = ["adm3_pcode", "adm3_en"]

    adm4_df = df[(df["geo_level"] == "Bgy") | (df["geo_level"] == "SubMun")].copy()
    adm4_df["adm3_pcode"] = adm4_df["psgc_code"].apply(lambda x: str(x).zfill(10)[:7] + "000").astype(int)
    adm4_df["adm2_pcode"] = adm4_df["psgc_code"].apply(lambda x: str(x).zfill(10)[:5] + "00000").astype(int)
    adm4_w3_df = adm4_df.merge(adm3_df, on="adm3_pcode", how="left")
    return adm4_w3_df.merge(adm2_df, on="adm2_pcode", how="left")
