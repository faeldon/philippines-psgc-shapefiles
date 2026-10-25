#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""The geometry edits: rebuilt units are the union of their children, merges dissolve, and splits add up."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from ph_psgc_shape import levels
from ph_psgc_shape.debug import report_nulls
from ph_psgc_shape.geometry import GeometryEditError, apply_merges, rebuild_units, split_mothers
from ph_psgc_shape.release import Merge

CRS = 32651
NIR, REGION_VI = 1800000000, 600000000


def frame(rows, **columns):
    """A frame in UTM 51N of (code, shape) rows, plus constant or per-row columns."""
    codes, shapes = zip(*rows)
    return gpd.GeoDataFrame({"psgc_code": list(codes), **columns}, geometry=list(shapes), crs=CRS)


def provinces():
    """Negros Occidental and Negros Oriental under NIR, Iloilo under Region VI: 100 m squares side by side."""
    return gpd.GeoDataFrame(
        {"adm2_psgc": [1804500000, 1804600000, 603000000], "adm1_psgc": [NIR, NIR, REGION_VI]},
        geometry=[box(0, 0, 100, 100), box(100, 0, 200, 100), box(300, 0, 400, 100)],
        crs=CRS,
    )


def test_a_rebuilt_unit_is_the_union_of_its_children():
    regions = frame([(NIR, None), (REGION_VI, box(0, 0, 400, 100))])
    rebuild_units(regions, provinces(), "psgc_code", "adm1_psgc", [NIR])
    nir = regions.set_index("psgc_code").geometry[NIR]
    assert nir.area == pytest.approx(provinces().geometry[:2].area.sum(), rel=1e-4)
    assert nir.equals(box(0, 0, 200, 100))


def test_an_unlisted_unit_keeps_its_shape():
    regions = frame([(NIR, None), (REGION_VI, box(0, 0, 400, 100))])
    rebuild_units(regions, provinces(), "psgc_code", "adm1_psgc", [NIR])
    assert regions.set_index("psgc_code").geometry[REGION_VI].equals(box(0, 0, 400, 100))


def test_a_rebuilt_unit_without_children_fails():
    regions = frame([(900000000, None)])
    with pytest.raises(GeometryEditError, match="no child"):
        rebuild_units(regions, provinces(), "psgc_code", "adm1_psgc", [900000000])


DACANLAO, SAN_RAFAEL = 401007019, 401007038


def test_a_merge_keeps_into_with_the_union_and_drops_the_rest():
    bgy = frame([(DACANLAO, box(0, 0, 10, 10)), (SAN_RAFAEL, box(10, 0, 20, 10)), (401007001, box(30, 0, 40, 10))])
    bgy["geom_src"] = "source"
    merged = apply_merges(bgy, [Merge(DACANLAO, (DACANLAO, SAN_RAFAEL))])
    assert list(merged["psgc_code"]) == [DACANLAO, 401007001]
    assert merged.geometry.iloc[0].equals(box(0, 0, 20, 10))
    assert list(merged["geom_src"]) == ["dissolved", "source"]


def test_a_merge_whose_rows_arent_there_fails():
    bgy = frame([(DACANLAO, box(0, 0, 10, 10))], geom_src="source")
    with pytest.raises(GeometryEditError, match="merge into"):
        apply_merges(bgy, [Merge(DACANLAO, (DACANLAO, SAN_RAFAEL))])


def splits(*daughters):
    """A split file's daughters, as read_splits gives them: code, mothers (a list) and shape."""
    codes, mothers, shapes = zip(*daughters)
    return gpd.GeoDataFrame({"code": list(codes), "mothers": list(mothers)}, geometry=list(shapes), crs=CRS)


def mothers():
    return frame([(1606801010, box(0, 0, 100, 100)), (1606801001, box(100, 0, 200, 100))], src_pcode=["J", "B"])


def test_a_split_leaves_its_mother_what_the_daughter_doesnt_take():
    remaining = split_mothers(mothers(), splits((1606801027, ["J"], box(0, 0, 60, 100))), "src_pcode")
    assert remaining[0].equals(box(60, 0, 100, 100))
    assert set(remaining) == {0}


def test_a_daughter_and_what_is_left_cover_the_mother_exactly():
    daughter = box(0, 0, 60, 100)
    left = split_mothers(mothers(), splits((1606801027, ["J"], daughter)), "src_pcode")[0]
    assert left.union(daughter).symmetric_difference(box(0, 0, 100, 100)).area < 1.0


def test_a_daughter_reaching_outside_its_mother_fails():
    with pytest.raises(GeometryEditError, match="outside their mothers"):
        split_mothers(mothers(), splits((1606801027, ["J"], box(0, 0, 100, 102))), "src_pcode")


def test_overlapping_daughters_fail():
    two = splits((1, ["J"], box(0, 0, 60, 100)), (2, ["J"], box(50, 0, 100, 100)))
    with pytest.raises(GeometryEditError, match="overlap"):
        split_mothers(mothers(), two, "src_pcode")


def test_a_mother_fully_divided_is_left_nothing():
    six = splits(*[(i, ["J"], box(i * 20, 0, i * 20 + 20, 100)) for i in range(5)])
    assert split_mothers(mothers(), six, "src_pcode") == {0: None}


def test_a_daughter_cut_from_several_mothers_takes_from_each():
    remaining = split_mothers(mothers(), splits((1, ["J", "B"], box(80, 0, 120, 100))), "src_pcode")
    assert remaining[0].equals(box(0, 0, 80, 100)) and remaining[1].equals(box(120, 0, 200, 100))


def test_plotted_daughters_join_the_source_with_their_mothers_columns_even_when_the_mother_is_used_up():
    source = frame([(1307501176, box(0, 0, 100, 100)), (1307501175, box(100, 0, 200, 100))])
    source["src_pcode"] = ["PH1307501176", "PH1307501175"]
    source["adm4_pcode"] = source["src_pcode"]
    source["adm3_en"] = "Caloocan City"
    source["adm4_en"] = ["Barangay 176", "Barangay 175"]
    source["geom_src"] = "source"
    halves = splits(
        (1380100189, ["PH1307501176"], box(0, 0, 50, 100)), (1380100190, ["PH1307501176"], box(50, 0, 100, 100))
    )
    psgc_df = pd.DataFrame({"psgc_code": [1380100189, 1380100190], "name": ["Barangay 176-A", "Barangay 176-B"]})
    out = levels.add_daughters(source, halves, psgc_df, "plotted")
    assert list(out["psgc_code"]) == [1307501175, 1380100189, 1380100190]  # 176 itself is used up
    added = out[out["geom_src"] == "plotted"]
    assert list(added["adm3_en"]) == ["Caloocan City"] * 2
    assert list(added["adm4_en"]) == ["Barangay 176-A", "Barangay 176-B"]
    assert list(added["adm3_pcode"]) == ["P1380100", "P1380100"]


def test_complete_gives_daughters_and_mothers_approximated_shapes():
    joined = frame([(1903617040, box(0, 0, 100, 100)), (1903617147, None)], src_pcode=["D", None])
    joined["geom_src"] = ["source", "none"]
    complete = levels.approximate(joined, splits((1903617147, ["D"], box(0, 0, 40, 100))))
    assert list(complete["geom_src"]) == ["approximated", "approximated"]
    assert complete.geometry.iloc[0].equals(box(40, 0, 100, 100))
    assert list(complete["area_crs"]) == [6000, 4000]
    assert list(joined["geom_src"]) == ["source", "none"]  # known is untouched


def test_complete_leaves_a_mother_the_cut_takes_nothing_from_as_it_was():
    joined = frame(
        [(1206317011, box(0, 0, 100, 100)), (1206317004, box(100, 0, 200, 100)), (1206317017, None)],
        src_pcode=["M", "C", None],
    )
    joined["geom_src"] = ["source", "source", "none"]
    complete = levels.approximate(joined, splits((1206317017, ["M", "C"], box(0, 0, 40, 100))))
    assert list(complete["geom_src"]) == ["approximated", "source", "approximated"]
    assert complete.geometry.iloc[1].equals(box(100, 0, 200, 100))


def joined_bgy():
    """A joined adm4 frame: Angoyao a PSGC row without a shape, Adams matched, and a shape with no PSGC row."""
    return frame(
        [(1903617146, None), (102801001, box(0, 0, 10, 10)), (1307501176, box(10, 0, 20, 10))],
        name=["Angoyao", "Adams", None],
    )


def test_a_shapeless_declaration_the_data_bears_out_passes():
    levels.check_shapeless(joined_bgy(), {1903617146: "no published boundary"})


@pytest.mark.parametrize("code", [102801001, 1307501176, 1903617999])  # has a shape, isn't PSGC, isn't there
def test_a_stale_shapeless_declaration_fails(code):
    with pytest.raises(GeometryEditError, match=f"shapeless: \\[{code}\\]"):
        levels.check_shapeless(joined_bgy(), {1903617146: "", code: ""})


def test_declared_shapeless_rows_are_reported_but_not_counted(capsys):
    joined = pd.DataFrame(
        {"psgc_code": [1903617146, 102801001], "name": ["Angoyao", "Adams"], "adm4_en": [None, "Adams"]}
    )
    report_nulls(joined, "adm4_en", explained={1903617146})
    out = capsys.readouterr().out
    assert "1 PSGC rows have no shape, as the release declares: [1903617146]" in out
    assert "All rows matched!" in out
