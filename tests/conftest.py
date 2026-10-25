#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Shared fixtures: a passing dist/ directory, its zips written from the fixture CSVs."""
from __future__ import annotations

import shutil
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

FIXTURE = Path(__file__).parent / "fixtures" / "dist_ok"
CRS = 32651


def write_zip(dist_dir: Path, stem: str, df: pd.DataFrame, crs=CRS, shift=0.0):
    """Write dist_dir/{stem}.shp.zip from df, one 5 m square per row, as the pipeline writes it."""
    squares = [box(x + shift, 0, x + 5 + shift, 5) for x in range(0, 10 * len(df), 10)]
    gpd.GeoDataFrame(df, geometry=squares, crs=CRS).to_crs(crs).to_file(
        dist_dir / f"{stem}.shp.zip", driver="ESRI Shapefile"
    )


def make_dist(dst: Path) -> Path:
    """Copy the fixture CSVs to dst and write each level's matching zip."""
    shutil.copytree(FIXTURE, dst)
    for csv in sorted(dst.glob("*.csv")):
        write_zip(dst, csv.stem, pd.read_csv(csv))
    return dst


@pytest.fixture
def dist(tmp_path):
    """A writable, passing dist/ directory: the fixture CSVs and their zips."""
    return make_dist(tmp_path / "dist")


@pytest.fixture
def dist_ref(tmp_path):
    """A second, identical passing directory to diff against."""
    return make_dist(tmp_path / "ref")
