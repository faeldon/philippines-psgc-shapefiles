#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""check_dist: CONTRACT 2 checks, the zip checks and the level-by-level diff, on small fixture directories."""
from __future__ import annotations

import zipfile

import geopandas as gpd
import pandas as pd
from conftest import write_zip
from shapely.geometry import box

import check_dist

PSGC = {
    "adm1": {100000000, 200000000},
    "adm2": {102800000, 200900000},
    "adm3": {102801000, 200901000},
    "adm4": {102801001, 200901001},
}


def edit(dist_dir, stem, change, zip_too=True):
    """Apply change(df) to one level's CSV in place and, unless zip_too is False, rewrite its zip to match."""
    path = dist_dir / f"{stem}.csv"
    df = pd.read_csv(path)
    change(df)
    df.to_csv(path, index=False)
    if zip_too:
        write_zip(dist_dir, stem, df)


def rezip(dist_dir, stem, rename):
    """Rewrite a level's zip with each member renamed by rename(name)."""
    path = dist_dir / f"{stem}.shp.zip"
    with zipfile.ZipFile(path) as z:
        members = {name: z.read(name) for name in z.namelist()}
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members.items():
            z.writestr(rename(name), data)


def test_fixture_passes(dist):
    assert not check_dist.check_dir(dist, PSGC)


def test_duplicate_code_fails(dist):
    edit(dist, "PH_Adm3_MuniCities", lambda df: df.loc.__setitem__((1, "adm3_psgc"), 102801000))
    assert any("duplicate adm3_psgc" in p for p in check_dist.check_dir(dist, PSGC))


def test_null_code_fails(dist):
    edit(dist, "PH_Adm4_BgySubMuns", lambda df: df.loc.__setitem__((0, "adm4_psgc"), None), zip_too=False)
    assert any("null adm4_psgc" in p for p in check_dist.check_dir(dist, PSGC))


def test_orphan_parent_fails(dist):
    edit(dist, "PH_Adm3_MuniCities", lambda df: df.loc.__setitem__((0, "adm2_psgc"), 999900000))
    assert any("adm2_psgc not in adm2" in p for p in check_dist.check_dir(dist, PSGC))


def test_unknown_extra_code_fails(dist):
    psgc = {**PSGC, "adm2": {102800000}}
    assert any("not in the PSGC table" in p for p in check_dist.check_dir(dist, psgc))


def test_known_extra_code_passes(dist, monkeypatch):
    monkeypatch.setitem(check_dist.KNOWN_EXTRA, "adm2", {200900000: "fixture"})
    psgc = {**PSGC, "adm2": {102800000}}
    assert not check_dist.check_dir(dist, psgc)


def test_missing_code_fails(dist):
    psgc = {**PSGC, "adm1": PSGC["adm1"] | {300000000}}
    assert any("missing" in p for p in check_dist.check_dir(dist, psgc))


def test_missing_zip_fails(dist):
    (dist / "PH_Adm2_ProvDists.shp.zip").unlink()
    assert "adm2: PH_Adm2_ProvDists.shp.zip is missing" in check_dist.check_dir(dist, PSGC)


def test_zips_false_checks_csvs_without_reading_zips(dist):
    (dist / "PH_Adm2_ProvDists.shp.zip").write_text("version https://git-lfs.github.com/spec/v1\n")
    edit(dist, "PH_Adm3_MuniCities", lambda df: df.loc.__setitem__((1, "adm3_psgc"), 102801000), zip_too=False)
    problems = check_dist.check_dir(dist, PSGC, zips=False)
    assert any("duplicate adm3_psgc" in p for p in problems)
    assert not any("zip" in p for p in problems)


def test_second_layer_fails(dist, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    gpd.GeoDataFrame({"name": ["x"]}, geometry=[box(0, 0, 1, 1)], crs=4326).to_file(other / "Regions.shp")
    with zipfile.ZipFile(dist / "PH_Adm1_Regions.shp.zip", "a") as z:
        for f in other.iterdir():
            z.write(f, f.name)
    problems = check_dist.check_dir(dist, PSGC)
    assert any("adm1: PH_Adm1_Regions.shp.zip layers are" in p for p in problems)
    assert any("adm1: PH_Adm1_Regions.shp.zip members are" in p for p in problems)


def test_double_extension_members_fail(dist):
    rezip(dist, "PH_Adm3_MuniCities", lambda name: name.replace("PH_Adm3_MuniCities.", "PH_Adm3_MuniCities.shp."))
    problems = check_dist.check_dir(dist, PSGC)
    assert any("adm3: PH_Adm3_MuniCities.shp.zip members are" in p for p in problems)
    assert any("adm3: PH_Adm3_MuniCities.shp.zip layers are" in p for p in problems)


def test_wrong_crs_fails(dist):
    write_zip(dist, "PH_Adm4_BgySubMuns", pd.read_csv(dist / "PH_Adm4_BgySubMuns.csv"), crs=4326)
    assert any("CRS is EPSG:4326" in p for p in check_dist.check_dir(dist, PSGC))


def test_zip_attribute_differs_from_csv_fails(dist):
    df = pd.read_csv(dist / "PH_Adm3_MuniCities.csv")
    df.loc[0, "adm2_psgc"] = 200900000
    write_zip(dist, "PH_Adm3_MuniCities", df)
    assert any("adm3 zip vs csv: adm2_psgc differs" in p for p in check_dist.check_dir(dist, PSGC))


def test_untrimmed_name_fails(dist):
    edit(dist, "PH_Adm4_BgySubMuns", lambda df: df.loc.__setitem__((0, "adm4_en"), "Adams "), zip_too=False)
    assert any(
        "adm4: 1 adm4_en value(s) with leading/trailing whitespace" in p for p in check_dist.check_dir(dist, PSGC)
    )


def test_diff_identical_is_clean(dist, dist_ref):
    assert not check_dist.diff_dirs(dist_ref, dist)


def test_diff_dtype_change(dist, dist_ref):
    edit(dist, "PH_Adm1_Regions", lambda df: df.__setitem__("adm1_psgc", df["adm1_psgc"].astype(float)))
    assert any("adm1_psgc dtype" in p for p in check_dist.diff_dirs(dist_ref, dist))


def test_diff_renamed_value(dist, dist_ref):
    edit(dist, "PH_Adm3_MuniCities", lambda df: df.loc.__setitem__((0, "adm3_en"), "Adams City"))
    assert any("adm3_en differs" in p for p in check_dist.diff_dirs(dist_ref, dist))


def test_diff_code_moved(dist, dist_ref):
    edit(dist, "PH_Adm3_MuniCities", lambda df: df.loc.__setitem__((0, "adm2_psgc"), 200900000))
    assert any("adm2_psgc differs" in p for p in check_dist.diff_dirs(dist_ref, dist))


def test_diff_area_crs_within_one_passes(dist, dist_ref):
    edit(dist, "PH_Adm2_ProvDists", lambda df: df.__setitem__("area_crs", df["area_crs"] + 1))
    assert not check_dist.diff_dirs(dist_ref, dist)


def test_diff_area_crs_beyond_one_fails(dist, dist_ref):
    edit(dist, "PH_Adm2_ProvDists", lambda df: df.__setitem__("area_crs", df["area_crs"] + 2))
    assert any("area_crs differs" in p for p in check_dist.diff_dirs(dist_ref, dist))


def test_diff_area_km2_must_match(dist, dist_ref):
    edit(dist, "PH_Adm1_Regions", lambda df: df.loc.__setitem__((0, "area_km2"), 2.5))
    assert any("area_km2 differs" in p for p in check_dist.diff_dirs(dist_ref, dist))


def test_diff_geometry_moved_fails(dist, dist_ref):
    write_zip(dist, "PH_Adm4_BgySubMuns", pd.read_csv(dist / "PH_Adm4_BgySubMuns.csv"), shift=1.0)
    assert any("adm4 zip: geometry differs in 2 row(s)" in p for p in check_dist.diff_dirs(dist_ref, dist))


def test_diff_geometry_within_tolerance_passes(dist, dist_ref):
    write_zip(dist, "PH_Adm4_BgySubMuns", pd.read_csv(dist / "PH_Adm4_BgySubMuns.csv"), shift=1e-6)
    assert not check_dist.diff_dirs(dist_ref, dist)


def test_diff_adm0_geometry_moved_fails(dist, dist_ref):
    write_zip(dist, "PH_Adm0_Country", pd.read_csv(dist / "PH_Adm0_Country.csv"), shift=1.0)
    assert any("adm0 zip: geometry differs" in p for p in check_dist.diff_dirs(dist_ref, dist))


def test_diff_zip_code_on_one_side(dist, dist_ref):
    df = pd.read_csv(dist / "PH_Adm2_ProvDists.csv")
    df.loc[0, "adm2_psgc"] = 102900000
    write_zip(dist, "PH_Adm2_ProvDists", df)
    problems = check_dist.diff_dirs(dist_ref, dist)
    assert any("adm2 zip: 1 adm2_psgc only in the first: [102800000]" in p for p in problems)
    assert any("adm2 zip: 1 adm2_psgc only in the second: [102900000]" in p for p in problems)


def test_diff_zip_in_one_directory(dist, dist_ref):
    (dist / "PH_Adm1_Regions.shp.zip").unlink()
    assert "adm1: PH_Adm1_Regions.shp.zip is in only one directory" in check_dist.diff_dirs(dist_ref, dist)


def null_first_shape(dist_dir, stem):
    """Rewrite a level's zip with no shape in its first row, as Manila's sub-municipalities have."""
    df = pd.read_csv(dist_dir / f"{stem}.csv")
    shapes = [None] + [box(x, 0, x + 5, 5) for x in range(10, 10 * len(df), 10)]
    gpd.GeoDataFrame(df, geometry=shapes, crs=32651).to_file(dist_dir / f"{stem}.shp.zip", driver="ESRI Shapefile")


def test_diff_no_shape_on_both_sides_passes(dist, dist_ref):
    null_first_shape(dist, "PH_Adm4_BgySubMuns")
    null_first_shape(dist_ref, "PH_Adm4_BgySubMuns")
    assert not check_dist.diff_dirs(dist_ref, dist)


def test_diff_shape_lost_on_one_side_fails(dist, dist_ref):
    null_first_shape(dist, "PH_Adm4_BgySubMuns")
    assert any("adm4 zip: geometry differs in 1 row(s)" in p for p in check_dist.diff_dirs(dist_ref, dist))


def test_diff_reads_the_old_double_extension_layout(dist, dist_ref):
    rezip(dist_ref, "PH_Adm4_BgySubMuns", lambda name: name.replace("PH_Adm4_BgySubMuns.", "PH_Adm4_BgySubMuns.shp."))
    assert not check_dist.diff_dirs(dist_ref, dist)


ADM4 = "PH_Adm4_BgySubMuns"


def shapeless_first(df):
    """Make adm4's first row a barangay without a shape, as known's Marawi and Tupi daughters are."""
    df.loc[0, ["len_crs", "area_crs", "len_km", "area_km2"]] = 0
    df.loc[0, "geom_src"] = "none"


def test_a_row_without_a_shape_must_be_none(dist):
    edit(dist, ADM4, lambda df: df.loc.__setitem__((0, ["len_crs", "area_crs"]), 0))
    assert any("no shape but geom_src not matching: [102801001]" in p for p in check_dist.check_dir(dist, PSGC))


def test_none_with_a_shape_fails(dist):
    edit(dist, ADM4, lambda df: df.loc.__setitem__((0, "geom_src"), "none"))
    assert any("geom_src none with a shape" in p for p in check_dist.check_dir(dist, PSGC))


def test_a_shapeless_none_row_passes(dist):
    edit(dist, ADM4, shapeless_first)
    assert not check_dist.check_dir(dist, PSGC)


def test_known_never_approximates(dist):
    edit(dist, ADM4, lambda df: df.loc.__setitem__((0, "geom_src"), "approximated"))
    assert any("geom_src value(s) not in" in p and "approximated" in p for p in check_dist.check_dir(dist, PSGC))


def test_adm4_without_geom_src_fails(dist):
    edit(dist, ADM4, lambda df: df.pop("geom_src"))
    assert "adm4: no geom_src column" in check_dist.check_dir(dist, PSGC)


def with_complete(dist, change=None):
    """Give dist a complete/ adm4: known's first row shapeless, complete's approximated (and change applied)."""
    edit(dist, ADM4, shapeless_first)
    complete = dist / "complete"
    complete.mkdir()
    df = pd.read_csv(dist / f"{ADM4}.csv")
    df.loc[0, ["len_crs", "area_crs", "geom_src"]] = [40, 400, "approximated"]
    if change:
        change(df)
    df.to_csv(complete / f"{ADM4}.csv", index=False)
    write_zip(complete, ADM4, df)
    return complete


def test_complete_differing_only_in_approximated_rows_passes(dist):
    with_complete(dist)
    assert not check_dist.check_dir(dist, PSGC)


def test_complete_differing_in_a_row_it_doesnt_approximate_fails(dist):
    with_complete(dist, lambda df: df.loc.__setitem__((1, "adm4_en"), "Chanarian II"))
    problems = check_dist.check_dir(dist, PSGC)
    assert any("1 row(s) differ from known but aren't approximated: [200901001]" in p for p in problems)


def test_complete_parents_must_exist_in_dists_levels(dist):
    with_complete(dist, lambda df: df.loc.__setitem__((1, "adm3_psgc"), 200902000))
    assert any("complete adm4: adm3_psgc not in adm3" in p for p in check_dist.check_dir(dist, PSGC))


def test_complete_with_other_codes_than_known_fails(dist):
    with_complete(dist, lambda df: df.loc.__setitem__((1, "adm4_psgc"), 200901002))
    assert "complete adm4: codes differ from known's adm4" in check_dist.check_dir(dist, PSGC)


def test_diff_compares_complete_too(dist, dist_ref):
    with_complete(dist)
    with_complete(dist_ref, lambda df: df.loc.__setitem__((0, "area_crs"), 999))
    assert any(p.startswith("complete adm4: area_crs differs") for p in check_dist.diff_dirs(dist_ref, dist))


def csv_only_copy(dist_dir):
    """dist_dir without its zips, as the committed dist/ is: the zips are release assets."""
    for path in dist_dir.rglob("*.shp.zip"):
        path.unlink()
    return dist_dir


def test_check_csv_only_passes_a_directory_without_zips(dist, monkeypatch):
    csv_only_copy(dist)
    monkeypatch.setattr(check_dist, "psgc_codes_by_level", lambda _release: PSGC)
    assert check_dist.main(["check", str(dist), "--csv-only"]) == 0
    assert check_dist.main(["check", str(dist)]) == 1  # without the flag, the missing zips are problems
    assert any("is missing" in p for p in check_dist.check_dir(dist, PSGC))


def test_diff_against_a_csv_only_directory_compares_the_csvs_only(dist, dist_ref):
    csv_only_copy(dist_ref)
    assert not check_dist.diff_dirs(dist_ref, dist)
    edit(dist, "PH_Adm2_ProvDists", lambda df: df.loc.__setitem__((0, "adm2_en"), "Renamed"))
    assert any(p.startswith("adm2: adm2_en differs") for p in check_dist.diff_dirs(dist_ref, dist))


def test_diff_says_when_zips_arent_compared(dist, dist_ref, capsys):
    csv_only_copy(dist_ref)
    assert check_dist.main(["diff", str(dist_ref), str(dist)]) == 0
    assert f"zips not compared: {dist_ref} has none" in capsys.readouterr().out


def test_geom_src_values_match_the_pipelines():
    from ph_psgc_shape.geometry import GEOM_SOURCES  # pylint: disable=import-outside-toplevel

    assert check_dist.GEOM_SOURCES == GEOM_SOURCES


def test_check_takes_a_release(dist, monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(check_dist, "psgc_codes_by_level", lambda release: seen.append(release) or PSGC)
    release = tmp_path / "next.toml"
    assert check_dist.main(["check", str(dist), "--release", str(release)]) == 0
    assert seen == [release]
