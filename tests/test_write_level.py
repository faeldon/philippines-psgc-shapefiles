#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""write_level: one zip and one CSV per level, from the same trimmed frame."""
from __future__ import annotations

import datetime
import time
import zipfile

import geopandas as gpd
import pandas as pd
import pyogrio
from shapely.geometry import box

import check_dist
from ph_psgc_shape.levels import write_level

STEM = "PH_Adm1_Regions"


def written(tmp_path, monkeypatch):
    """Run write_level on a two-row frame in tmp_path, as the pipeline runs from its working directory."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "dist").mkdir(exist_ok=True)
    gdf = gpd.GeoDataFrame(
        {"adm1_psgc": [100000000, 200000000], "adm1_en": ["Region I ", None], "len_crs": [20, 20]},
        geometry=[box(0, 0, 5, 5), box(10, 0, 15, 5)],
        crs=32651,
    )
    write_level(gdf, STEM)
    return tmp_path / "dist"


def test_zip_holds_one_utm_layer_named_for_the_level(tmp_path, monkeypatch):
    dist = written(tmp_path, monkeypatch)
    path = dist / f"{STEM}.shp.zip"
    assert sorted(zipfile.ZipFile(path).namelist()) == [
        f"{STEM}{ext}" for ext in (".cpg", ".dbf", ".prj", ".shp", ".shx")
    ]
    assert [str(name) for name, _ in pyogrio.list_layers(f"zip://{path}")] == [STEM]
    assert gpd.read_file(path).crs.to_epsg() == 32651


def test_names_are_trimmed_in_both_files(tmp_path, monkeypatch):
    dist = written(tmp_path, monkeypatch)
    csv = pd.read_csv(dist / f"{STEM}.csv")
    shp = gpd.read_file(dist / f"{STEM}.shp.zip")
    assert csv["adm1_en"].iloc[0] == "Region I" and shp["adm1_en"].iloc[0] == "Region I"
    assert pd.isna(csv["adm1_en"].iloc[1]) and pd.isna(shp["adm1_en"].iloc[1])


def test_the_same_frame_writes_the_same_zip_bytes(tmp_path, monkeypatch):
    first = written(tmp_path, monkeypatch) / f"{STEM}.shp.zip"
    before = first.read_bytes()
    time.sleep(1.1)  # a zip or .dbf dated by the clock would now differ
    second = written(tmp_path, monkeypatch) / f"{STEM}.shp.zip"
    assert second.read_bytes() == before


def test_the_zip_and_its_dbf_carry_the_stamp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    gdf = gpd.GeoDataFrame({"adm1_psgc": [100000000]}, geometry=[box(0, 0, 5, 5)], crs=32651)
    write_level(gdf, STEM, "dist", datetime.date(2026, 9, 30))
    with zipfile.ZipFile(tmp_path / "dist" / f"{STEM}.shp.zip") as archive:
        assert {i.date_time for i in archive.infolist()} == {(2026, 9, 30, 0, 0, 0)}
        assert list(archive.read(f"{STEM}.dbf")[1:4]) == [126, 9, 30]


def test_zip_matches_its_csv(tmp_path, monkeypatch):
    dist = written(tmp_path, monkeypatch)
    level = next(level for level in check_dist.LEVELS if level.stem == STEM)
    assert not check_dist.check_zip(dist, level, pd.read_csv(dist / f"{STEM}.csv"))
