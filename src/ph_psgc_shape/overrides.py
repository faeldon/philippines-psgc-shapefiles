#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""PSGC code overrides: move source rows from the code they carry to the code PSA gives them."""
from __future__ import annotations


def update_municities_psgc_code(municities_gdf, old_psgc_code, new_psgc_code, adm3_pcode=None, adm2_pcode=None):
    """Move every row whose psgc_code is old_psgc_code to new_psgc_code.

    Its adm3_pcode and adm2_pcode are derived from the new code unless adm3_pcode or adm2_pcode is given.
    """
    if adm3_pcode is None:
        new_adm3_pcode = f"P{str(new_psgc_code).zfill(10)[:7]}"
    else:
        new_adm3_pcode = f"P{str(adm3_pcode).zfill(10)[:7]}"
    municities_gdf.loc[municities_gdf["psgc_code"] == old_psgc_code, "adm3_pcode"] = new_adm3_pcode
    if adm2_pcode is None:
        new_adm2_pcode = f"P{str(new_psgc_code).zfill(10)[:5]}"
    else:
        new_adm2_pcode = f"P{str(adm2_pcode).zfill(10)[:5]}"
    municities_gdf.loc[municities_gdf["psgc_code"] == old_psgc_code, "adm2_pcode"] = new_adm2_pcode
    municities_gdf.loc[municities_gdf["psgc_code"] == old_psgc_code, "psgc_code"] = new_psgc_code


def update_bgysubmuns_psgc_code(bgysubmuns_gdf, old_psgc_code, new_psgc_code, adm4_en=None):
    """Move every row whose psgc_code is old_psgc_code (and adm4_en, if given) to new_psgc_code.

    Its adm4_pcode, adm3_pcode and adm2_pcode are all derived from the new code.
    """
    if adm4_en is None:
        bgysubmuns_gdf.loc[bgysubmuns_gdf["psgc_code"] == old_psgc_code, "adm4_pcode"] = (
            f"P{str(new_psgc_code).zfill(10)}"
        )
        bgysubmuns_gdf.loc[bgysubmuns_gdf["psgc_code"] == old_psgc_code, "adm3_pcode"] = (
            f"P{str(new_psgc_code).zfill(10)[:7]}"
        )
        bgysubmuns_gdf.loc[bgysubmuns_gdf["psgc_code"] == old_psgc_code, "adm2_pcode"] = (
            f"P{str(new_psgc_code).zfill(10)[:5]}"
        )
        bgysubmuns_gdf.loc[bgysubmuns_gdf["psgc_code"] == old_psgc_code, "psgc_code"] = new_psgc_code
    else:
        bgysubmuns_gdf.loc[
            (bgysubmuns_gdf["psgc_code"] == old_psgc_code) & (bgysubmuns_gdf["adm4_en"] == adm4_en), "adm4_pcode"
        ] = f"P{str(new_psgc_code).zfill(10)}"
        bgysubmuns_gdf.loc[
            (bgysubmuns_gdf["psgc_code"] == old_psgc_code) & (bgysubmuns_gdf["adm4_en"] == adm4_en), "adm3_pcode"
        ] = f"P{str(new_psgc_code).zfill(10)[:7]}"
        bgysubmuns_gdf.loc[
            (bgysubmuns_gdf["psgc_code"] == old_psgc_code) & (bgysubmuns_gdf["adm4_en"] == adm4_en), "adm2_pcode"
        ] = f"P{str(new_psgc_code).zfill(10)[:5]}"
        bgysubmuns_gdf.loc[
            (bgysubmuns_gdf["psgc_code"] == old_psgc_code) & (bgysubmuns_gdf["adm4_en"] == adm4_en), "psgc_code"
        ] = new_psgc_code


# The parent pcode columns each level's source carries, and how many digits of the code each keeps.
PARENT_DIGITS = {"adm1_pcode": 2, "adm2_pcode": 5, "adm3_pcode": 7, "adm4_pcode": 10}


def recoded(code, recodes):
    """A code as the release's recodes move it (the first recode whose from_prefix it starts with), else itself."""
    text = str(code).zfill(10)
    for r in recodes:
        if text.startswith(r.from_prefix):
            return int(r.to_prefix + text[5:])
    return code


def apply_recodes(gdf, recodes, pcode_columns):
    """Move every row whose psgc_code starts with a recode's from_prefix onto its to_prefix, in place.

    The row's pcode columns named in pcode_columns (its own and its parents') are derived from the new
    code, as update_municities_psgc_code derives them, so a transferred province's units follow it to
    its new region.
    """
    codes = gdf["psgc_code"].astype("int64").astype(str).str.zfill(10)
    for r in recodes:
        mask = codes.str.startswith(r.from_prefix)
        new = r.to_prefix + codes[mask].str[5:]
        gdf.loc[mask, "psgc_code"] = new.astype("int64")
        for col in pcode_columns:
            gdf.loc[mask, col] = "P" + new.str[: PARENT_DIGITS[col]]


def apply_municities_overrides(municities_gdf, overrides):
    """Apply each adm3 override in order; a later one can move a row an earlier one moved."""
    for o in overrides:
        update_municities_psgc_code(municities_gdf, o.old, o.new)


def apply_bgysubmuns_overrides(bgysubmuns_gdf, overrides):
    """Apply each adm4 override in order, matching adm4_en too where the override names one."""
    for o in overrides:
        update_bgysubmuns_psgc_code(bgysubmuns_gdf, o.old, o.new, o.adm4_en)
