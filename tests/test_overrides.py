#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""The overrides move exactly the rows they name, derive parents as before, and apply in file order."""
from __future__ import annotations

import pandas as pd

from ph_psgc_shape.overrides import (
    apply_bgysubmuns_overrides,
    apply_municities_overrides,
    apply_recodes,
    update_bgysubmuns_psgc_code,
    update_municities_psgc_code,
)
from ph_psgc_shape.release import BgyOverride, Override, Recode

# Datu Odin Sinsuat 1908707000 → 1908705000, then Matanog 1908709000 → 1908707000.
ODIN, MATANOG, ODIN_NEW = 1908707000, 1908709000, 1908705000


def municities(*codes):
    return pd.DataFrame({"psgc_code": list(codes), "adm3_pcode": "P0000000", "adm2_pcode": "P00000"})


def test_overrides_apply_in_file_order():
    in_order = municities(ODIN, MATANOG)
    apply_municities_overrides(in_order, [Override(ODIN, ODIN_NEW), Override(MATANOG, ODIN)])
    assert list(in_order["psgc_code"]) == [ODIN_NEW, ODIN]

    reversed_ = municities(ODIN, MATANOG)
    apply_municities_overrides(reversed_, [Override(MATANOG, ODIN), Override(ODIN, ODIN_NEW)])
    assert list(reversed_["psgc_code"]) == [ODIN_NEW, ODIN_NEW]


def test_municities_parents_derive_from_the_new_code():
    df = municities(305401000, 102801000)
    update_municities_psgc_code(df, 305401000, 330100000)  # City of Angeles
    assert df.iloc[0].tolist() == [330100000, "P0330100", "P03301"]
    assert df.iloc[1].tolist() == [102801000, "P0000000", "P00000"]


def test_municities_explicit_adm2():
    df = municities(330100000)
    update_municities_psgc_code(df, 330100000, 330100000, adm2_pcode=305400000)  # Angeles → Pampanga
    assert df.iloc[0].tolist() == [330100000, "P0330100", "P03054"]


def bgy(*rows):
    df = pd.DataFrame(rows, columns=["psgc_code", "adm4_en"])
    df["adm4_pcode"], df["adm3_pcode"], df["adm2_pcode"] = "P0000000000", "P0000000", "P00000"
    return df


def test_bgysubmuns_without_name_moves_every_row_with_the_code():
    df = bgy((1908707001, "Ambolodto"), (1908707001, "Other"), (102801001, "Adams"))
    update_bgysubmuns_psgc_code(df, 1908707001, 1908705001)
    assert list(df["psgc_code"]) == [1908705001, 1908705001, 102801001]
    assert df.iloc[0][["adm4_pcode", "adm3_pcode", "adm2_pcode"]].tolist() == ["P1908705001", "P1908705", "P19087"]


def test_bgysubmuns_with_name_moves_only_that_row():
    df = bgy((1908721002, "Bintan (Bentan)"), (1908721002, "Other"))
    apply_bgysubmuns_overrides(df, [BgyOverride(1908721002, 1908712001, "Bintan (Bentan)")])
    assert list(df["psgc_code"]) == [1908712001, 1908721002]
    assert df.iloc[1]["adm4_pcode"] == "P0000000000"


# 2024-2q's Negros Island Region and 2025-07's Sulu: whole provinces moved to another region.
NIR_AND_SULU = [Recode("06045", "18045"), Recode("06302", "18302"), Recode("19066", "09066")]


def test_recodes_move_a_province_and_its_parents():
    df = pd.DataFrame({"psgc_code": [604500000], "adm2_pcode": ["PH06045"], "adm1_pcode": ["PH06"]})
    apply_recodes(df, NIR_AND_SULU, ["adm2_pcode", "adm1_pcode"])
    assert df.iloc[0].tolist() == [1804500000, "P18045", "P18"]


def test_recodes_move_barangays_to_their_new_region():
    df = pd.DataFrame(
        {
            "psgc_code": [630200001, 1906601001, 102801001],  # Bacolod, Sulu (Jolo), Ilocos Norte
            "adm4_pcode": ["PH0630200001", "PH1906601001", "PH0102801001"],
            "adm3_pcode": ["PH0630200", "PH1906601", "PH0102801"],
            "adm1_pcode": ["PH06", "PH19", "PH01"],
        }
    )
    apply_recodes(df, NIR_AND_SULU, ["adm4_pcode", "adm3_pcode", "adm1_pcode"])
    assert list(df["psgc_code"]) == [1830200001, 906601001, 102801001]
    assert list(df["adm3_pcode"]) == ["P1830200", "P0906601", "PH0102801"]
    assert list(df["adm1_pcode"]) == ["P18", "P09", "PH01"]
