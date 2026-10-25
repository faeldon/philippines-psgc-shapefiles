#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""The release's geometry edits: units rebuilt from their children, merged barangays, and splits.

Everything here works in UTM 51N (EPSG:32651), the CRS the levels measure and write in. Each row's
geom_src says where its shape came from: GEOM_SOURCES.
"""
from __future__ import annotations

import geopandas as gpd
from shapely import union_all

UTM_51N = 32651

# geom_src: the source shapefile's own shape, the union of other shapes, plotted from a law's technical
# description, approximated by a sized cut (complete only), or no shape at all.
GEOM_SOURCES = ("source", "dissolved", "plotted", "approximated", "none")

# Area, in square metres, below which a split's leftover or overlap counts as nothing.
COVER_TOLERANCE = 1.0


class GeometryEditError(ValueError):
    """A geometry edit that can't be applied as the release declares it."""


def _set_geometry(gdf, mask, geom):
    gdf.loc[mask, "geometry"] = gpd.GeoSeries([geom] * int(mask.sum()), index=gdf.index[mask], crs=gdf.crs)


def rebuild_units(gdf, children, code_col, parent_col, codes):
    """Give each unit in codes the union of its children's shapes, in place.

    gdf holds the units, keyed by code_col; children holds the level below, each row's unit in parent_col.
    Raises GeometryEditError for a code that isn't exactly one unit, or that has no child with a shape.
    """
    for code in codes:
        mask = gdf[code_col] == code
        if mask.sum() != 1:
            raise GeometryEditError(f"rebuild: {code} matches {int(mask.sum())} rows, not 1")
        shapes = children.loc[children[parent_col] == code].geometry.dropna()
        if shapes.empty:
            raise GeometryEditError(f"rebuild: {code} has no child with a shape")
        _set_geometry(gdf, mask, union_all(list(shapes.to_crs(gdf.crs))))


def apply_merges(gdf, merges, code_col="psgc_code"):
    """Merge barangays, in place of the frame returned: each merge's into row takes the union of its from rows.

    The other from rows are dropped, and into's geom_src becomes dissolved. Raises GeometryEditError when
    into or a from code isn't exactly one row.
    """
    for m in merges:
        rows = gdf[gdf[code_col].isin(m.from_codes)]
        if sorted(rows[code_col]) != sorted(set(m.from_codes)) or m.into not in m.from_codes:
            raise GeometryEditError(f"merge into {m.into}: from {list(m.from_codes)} matches {list(rows[code_col])}")
        into = gdf[code_col] == m.into
        _set_geometry(gdf, into, union_all(list(rows.geometry)))
        gdf.loc[into, "geom_src"] = "dissolved"
        gdf = gdf[~gdf[code_col].isin(set(m.from_codes) - {m.into})]
    return gdf


def read_splits(path, crs):
    """A split file's daughters: one row per daughter, with its code, its mothers' source pcodes, and its shape.

    The GeoJSON's features each carry code (the daughter's PSGC code) and mothers (a comma-separated list of
    the source adm4_pcode of each barangay it was cut from).
    """
    splits = gpd.read_file(path)
    splits["code"] = splits["code"].astype("int64")
    splits["mothers"] = splits["mothers"].str.split(",")
    return splits.to_crs(crs)


def split_mothers(gdf, splits, mother_col):
    """Cut each split's daughters out of its mothers' shapes; return the new mother shapes, by row index.

    A mother with nothing left is given None. Raises GeometryEditError when a mother isn't exactly one row,
    a daughter reaches outside its mothers, or two daughters overlap (each by more than COVER_TOLERANCE).
    """
    remaining = {}
    for mothers, group in splits.groupby(splits["mothers"].map(tuple)):
        rows = gdf[gdf[mother_col].isin(mothers)]
        if len(rows) != len(mothers):
            raise GeometryEditError(f"split from {list(mothers)}: {len(rows)} mother rows, not {len(mothers)}")
        whole = union_all(list(rows.geometry))
        daughters = union_all(list(group.geometry))
        outside = daughters.difference(whole).area
        overlap = sum(g.area for g in group.geometry) - daughters.area
        if outside > COVER_TOLERANCE or overlap > COVER_TOLERANCE:
            raise GeometryEditError(
                f"split from {list(mothers)}: daughters reach {outside:.1f} m² outside their mothers"
                f" and overlap by {overlap:.1f} m²"
            )
        for index, geom in rows.geometry.items():
            left = geom.difference(daughters)
            remaining[index] = left if left.area > COVER_TOLERANCE else None
    return remaining
