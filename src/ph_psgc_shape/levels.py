#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Build each dist/ level from its release source and the PSGC table.

Each level reads its source shapefile, joins it to the PSGC table, applies the release's corrections,
reports what didn't match, adds geometry measures, and returns its output frames, keyed by the folder
under dist/ each is written to ("" for dist/ itself). pipeline.run writes them with write_level, as
{folder}/{stem}.shp.zip and {folder}/{stem}.csv.
"""
from __future__ import annotations

import datetime
import tempfile
import zipfile
from pathlib import Path

import pandas as pd

from .debug import report_nulls
from .geo_utils import add_geometry_measures, convert_adm_pcode, read_shapefile
from .geometry import (
    COVER_TOLERANCE,
    UTM_51N,
    GeometryEditError,
    apply_merges,
    read_splits,
    rebuild_units,
    split_mothers,
)
from .matching import JOINED_COLUMNS, run_passes
from .overrides import PARENT_DIGITS, apply_municities_overrides, apply_recodes, update_municities_psgc_code
from .psgc import PSGC_COLUMNS

# Each level's output file name, under dist/ (and, for adm4, dist/complete/).
STEMS = {
    "country": "PH_Adm0_Country",
    "region": "PH_Adm1_Regions",
    "provdists": "PH_Adm2_ProvDists",
    "municities": "PH_Adm3_MuniCities",
    "bgysubmuns": "PH_Adm4_BgySubMuns",
}

# adm4's complete distribution: the approximated splits, written beside dist/'s adm0–3.
COMPLETE = "complete"

MEASURES = ["len_crs", "area_crs", "len_km", "area_km2", "geometry"]

# The barangay table's parent columns (psgc.barangay_table), renamed so they don't collide with the source's.
BGY_PARENT_COLUMNS = {
    "adm3_pcode": "bgy_adm3_pcode",
    "adm2_pcode": "bgy_adm2_pcode",
    "adm3_en": "bgy_adm3_en",
    "adm2_en": "bgy_adm2_en",
}

# A zip's default date when the caller gives none: the earliest a zip entry can hold.
ZIP_EPOCH = datetime.date(1980, 1, 1)

# The pcode columns of an adm4 source row: its own and its parents', which a recode rewrites.
ADM4_PCODES = ["adm4_pcode", "adm3_pcode", "adm2_pcode", "adm1_pcode"]


def write_level(gdf, stem, out_dir="dist", stamp=ZIP_EPOCH):
    """Write {out_dir}/{stem}.shp.zip and .csv from one frame, trimming whitespace from text columns.

    The shapefile's .dbf can't hold trailing spaces, so both files drop them and stay equal. The zip
    is byte-reproducible: its .dbf header and its entries are dated stamp (the release publication's
    as_of, from pipeline.run), and its members are in name order, so the same frame writes the same
    bytes.
    """
    out = gdf.copy()
    for col in out.columns:
        if col != "geometry" and pd.api.types.is_string_dtype(out[col]):
            out[col] = out[col].str.strip()
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        out.to_file(Path(tmp) / f"{stem}.shp", driver="ESRI Shapefile")
        dbf = Path(tmp) / f"{stem}.dbf"
        header = bytearray(dbf.read_bytes())
        header[1:4] = bytes([stamp.year - 1900, stamp.month, stamp.day])  # the .dbf's last-update date
        dbf.write_bytes(bytes(header))
        with zipfile.ZipFile(f"{out_dir}/{stem}.shp.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for member in sorted(Path(tmp).iterdir()):
                info = zipfile.ZipInfo(member.name, date_time=(stamp.year, stamp.month, stamp.day, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, member.read_bytes())
    out.drop(columns=["geometry"]).to_csv(f"{out_dir}/{stem}.csv", index=False)


def read_source(release, level):
    """Read a level's source shapefile, its columns named as the release says."""
    source = release.sources[level]
    gdf = read_shapefile(source.path)
    gdf.columns = list(source.columns)
    return gdf


def parent_psgc(gdf, pcode_column, zero_suffix):
    """A parent level's PSGC codes, as ints, from a pcode column."""
    return gdf[pcode_column].apply(lambda x: convert_adm_pcode(x, zero_suffix)).astype(int)


def describe(gdf):
    """Print a frame's head, columns and shape, as each level logs its source."""
    print(gdf.head())
    print(gdf.columns)
    print(gdf.shape)


def finish(gdf, keep, names):
    """Keep and rename the output columns; return the level's frame."""
    gdf = gdf[keep]
    gdf.columns = names
    print(gdf.head())
    return gdf


def rebuild(gdf, children, parent_col, codes, name_col):
    """Give each unit in codes the union of its children's shapes (geometry.rebuild_units), and re-measure.

    A rebuilt unit with no source row (a new region) takes its PSGC name in name_col, so the match
    report counts it as matched.
    """
    if not codes:
        return gdf
    if children is None:
        raise GeometryEditError(f"rebuild {list(codes)}: the level below wasn't built")
    rebuild_units(gdf, children, "psgc_code", parent_col, codes)
    new = gdf["psgc_code"].isin(codes) & gdf[name_col].isna()
    gdf.loc[new, name_col] = gdf.loc[new, "name"]
    return add_geometry_measures(gdf, epsg_code=UTM_51N)


def country(_psgc_df, release, _children=None):
    """Build level 0 (country)."""
    country_gdf = read_source(release, "country")
    describe(country_gdf)
    country_gdf = add_geometry_measures(country_gdf, epsg_code=UTM_51N)
    return {"": finish(country_gdf, ["adm0_en"] + MEASURES, ["adm0_en"] + MEASURES)}


def region(psgc_df, release, children=None):
    """Build level 1 (regions).

    The release's rebuilt regions take the union of their provinces and districts from children, the
    provdists level's frame.
    """
    psgc_df = psgc_df[psgc_df["geo_level"] == "Reg"]

    regions_gdf = read_source(release, "region")
    regions_gdf["psgc_code"] = parent_psgc(regions_gdf, "adm1_pcode", "00000000")
    describe(regions_gdf)

    regions_shape_gdf = regions_gdf.merge(psgc_df, on="psgc_code", how="outer")
    regions_shape_gdf = regions_shape_gdf[
        PSGC_COLUMNS + ["adm1_pcode", "adm1_en", "adm0_pcode", "shape_len", "shape_area", "shape_sqkm", "geometry"]
    ]
    regions_shape_gdf = add_geometry_measures(regions_shape_gdf, epsg_code=UTM_51N)
    regions_shape_gdf = rebuild(regions_shape_gdf, children, "adm1_psgc", release.region.rebuild, "adm1_en")
    report_nulls(regions_shape_gdf, "adm1_en", report_table=True)

    return {
        "": finish(
            regions_shape_gdf,
            ["psgc_code", "name", "geo_level"] + MEASURES,
            ["adm1_psgc", "adm1_en", "geo_level"] + MEASURES,
        )
    }


def provdists(psgc_df, release, _children=None):
    """Build level 2 (provinces and districts)."""
    corrections = release.provdists
    psgc_df = psgc_df[
        (psgc_df["geo_level"] == "Prov")
        | psgc_df["name"].isin(corrections.extra_names)
        | (psgc_df["geo_level"] == "Dist")
        | psgc_df["psgc_code"].isin(corrections.extra_codes)
    ]

    provdists_gdf = read_source(release, "provdists")
    provdists_gdf["psgc_code"] = parent_psgc(provdists_gdf, "adm2_pcode", "00000")
    apply_recodes(provdists_gdf, release.recodes, ["adm2_pcode", "adm1_pcode"])
    for o in corrections.overrides:
        mask = provdists_gdf["psgc_code"] == o.old
        provdists_gdf.loc[mask, "psgc_code"] = o.new
        provdists_gdf.loc[mask, "adm2_pcode"] = o.adm2_pcode
    describe(provdists_gdf)

    provdists_shape_gdf = provdists_gdf.merge(psgc_df, on="psgc_code", how="outer")
    provdists_shape_gdf = provdists_shape_gdf[
        PSGC_COLUMNS
        + ["adm2_pcode", "adm2_en", "adm1_pcode", "adm0_pcode", "shape_len", "shape_area", "shape_sqkm"]
        + ["geometry"]
    ]
    report_nulls(provdists_shape_gdf, column_name="adm2_en", report_table=True)

    provdists_shape_gdf = add_geometry_measures(provdists_shape_gdf, epsg_code=UTM_51N)
    provdists_shape_gdf["adm1_psgc"] = parent_psgc(provdists_shape_gdf, "adm1_pcode", "00000000")
    return {
        "": finish(
            provdists_shape_gdf,
            ["adm1_psgc", "psgc_code", "name", "geo_level"] + MEASURES,
            ["adm1_psgc", "adm2_psgc", "adm2_en", "geo_level"] + MEASURES,
        )
    }


def municities(psgc_df, release, children=None):
    """Build level 3 (municipalities and cities).

    Applies the release's recodes and PSGC code overrides, then gives each city in city_adm2 its adm2.
    The release's rebuilt municipalities take the union of their barangays from children, the
    bgysubmuns level's frame.
    """
    psgc_df = psgc_df[
        (psgc_df["geo_level"] == "Mun") | (psgc_df["geo_level"] == "City") | (psgc_df["geo_level"] == "SGU")
    ]

    municities_gdf = read_source(release, "municities")
    municities_gdf["psgc_code"] = parent_psgc(municities_gdf, "adm3_pcode", "000")
    apply_recodes(municities_gdf, release.recodes, ["adm3_pcode", "adm2_pcode", "adm1_pcode"])
    apply_municities_overrides(municities_gdf, release.municities.overrides)
    for city, adm2 in release.municities.city_adm2.items():
        update_municities_psgc_code(municities_gdf, city, city, adm2_pcode=adm2)
    describe(municities_gdf)

    municities_shape_gdf = municities_gdf.merge(psgc_df, on="psgc_code", how="outer")
    municities_shape_gdf = municities_shape_gdf[
        PSGC_COLUMNS
        + ["adm3_pcode", "adm3_en", "adm2_pcode", "adm1_pcode", "adm0_pcode", "shape_len", "shape_area", "shape_sqkm"]
        + ["geometry"]
    ]
    municities_shape_gdf = add_geometry_measures(municities_shape_gdf, epsg_code=UTM_51N)
    municities_shape_gdf = rebuild(municities_shape_gdf, children, "adm3_psgc", release.municities.rebuild, "adm3_en")
    report_nulls(municities_shape_gdf, column_name="adm3_en", report_table=True)

    municities_shape_gdf["adm1_psgc"] = parent_psgc(municities_shape_gdf, "adm1_pcode", "00000000")
    municities_shape_gdf["adm2_psgc"] = parent_psgc(municities_shape_gdf, "adm2_pcode", "00000")
    return {
        "": finish(
            municities_shape_gdf,
            ["adm1_psgc", "adm2_psgc", "psgc_code", "name", "geo_level"] + MEASURES,
            ["adm1_psgc", "adm2_psgc", "adm3_psgc", "adm3_en", "geo_level"] + MEASURES,
        )
    }


def fix_adm4_parents(gdf, release):
    """Make every adm4 row's parent codes exist in the level above (CONTRACT 2), in place.

    Takes the joined adm4 frame once adm1_psgc, adm2_psgc and adm3_psgc are set, with its PSGC code in
    psgc_code and name in name. Manila's sub-municipalities, which have no shapefile row and so no
    parents, go under the City of Manila; barangays parented to a sub-municipality or to Manila's
    pre-2021 code go under the City of Manila; any other row with no shapefile row (a barangay without
    a shape) takes its parents from its own code; barangays of a city in city_adm2 get that city's adm2;
    and the non-barangay areas get their source names.
    """
    manila = release.bgysubmuns.manila
    city_adm2 = release.municities.city_adm2
    submun = gdf["geo_level"] == "SubMun"
    gdf.loc[submun, "adm1_psgc"] = manila.ncr
    gdf.loc[submun, "adm3_psgc"] = manila.city
    under_manila = gdf["adm3_psgc"].isin({manila.old} | set(gdf.loc[submun, "psgc_code"]))
    gdf.loc[under_manila, "adm3_psgc"] = manila.city
    unparented = gdf["adm3_psgc"] == 0
    for col, digits in (("adm1_psgc", 2), ("adm2_psgc", 5), ("adm3_psgc", 7)):
        gdf.loc[unparented, col] = gdf.loc[unparented, "psgc_code"] // 10 ** (10 - digits) * 10 ** (10 - digits)
    in_city = gdf["adm3_psgc"].isin(city_adm2.keys())
    gdf.loc[in_city, "adm2_psgc"] = gdf.loc[in_city, "adm3_psgc"].map(city_adm2)
    for code, name in release.bgysubmuns.non_barangay_areas.items():
        gdf.loc[gdf["psgc_code"] == code, "name"] = name


def add_daughters(gdf, splits, psgc_df, kind):
    """Cut a split file's daughters out of their mothers in the adm4 source frame, and add them as rows.

    Each daughter row takes its PSGC code as its pcodes and its PSGC name as adm4_en, so the matching
    passes match it by code and name; its other columns come from its first mother. A mother with
    nothing left is dropped. Returns the new frame.
    """
    remaining = split_mothers(gdf, splits, "src_pcode")
    mothers = gdf.loc[gdf["src_pcode"].isin({m for ms in splits["mothers"] for m in ms})].set_index("src_pcode")
    for index, geom in remaining.items():
        gdf.loc[index, "geometry"] = geom
    gdf = gdf.drop(index=[i for i, geom in remaining.items() if geom is None])
    names = psgc_df.set_index("psgc_code")["name"]
    rows = []
    for _, d in splits.iterrows():
        row = mothers.loc[d["mothers"][0]].copy()
        code = str(d["code"]).zfill(10)
        for col in ADM4_PCODES:
            row[col] = "P" + code[: PARENT_DIGITS[col]]
        row["psgc_code"] = d["code"]
        row["adm4_en"] = names[d["code"]]
        row["src_pcode"] = None
        row["geom_src"] = kind
        row["geometry"] = d.geometry
        rows.append(row)
    added = pd.DataFrame(rows).set_geometry("geometry", crs=gdf.crs)
    return pd.concat([gdf, added], ignore_index=True)


def approximate(gdf, splits):
    """Complete's adm4: the joined frame with the approximated daughters given shapes cut from their mothers.

    The daughters are rows already (PSGC rows without a shape); they, and each mother the cut takes
    something from, become approximated. Returns a new frame; gdf is unchanged.
    """
    gdf = gdf.copy()
    remaining = split_mothers(gdf, splits, "src_pcode")
    if any(geom is None for geom in remaining.values()):
        raise GeometryEditError("approximated: a mother would be left without a shape")
    for index, geom in remaining.items():
        if gdf.geometry[index].area - geom.area > COVER_TOLERANCE:
            gdf.loc[index, "geometry"] = geom
            gdf.loc[index, "geom_src"] = "approximated"
    for _, d in splits.iterrows():
        mask = gdf["psgc_code"] == d["code"]
        if mask.sum() != 1:
            raise GeometryEditError(f"approximated: daughter {d['code']} matches {int(mask.sum())} rows, not 1")
        gdf.loc[mask, "geometry"] = d.geometry
        gdf.loc[mask, "geom_src"] = "approximated"
    return add_geometry_measures(gdf, epsg_code=UTM_51N)


def check_shapeless(joined, shapeless):
    """Raise GeometryEditError unless each declared shapeless code is a PSGC row the join left without a shape.

    A declaration the data no longer bears out (the code matched a shape, or isn't in the PSGC table) would
    otherwise hide a row from the match report for nothing.
    """
    rows = joined[joined["psgc_code"].isin(shapeless) & joined["name"].notna()]
    stale = sorted(set(shapeless) - set(rows.loc[rows.geometry.isna(), "psgc_code"]))
    if stale:
        raise GeometryEditError(f"shapeless: {stale} aren't PSGC rows without a shape")


def bgysubmuns(psgc_df, release, _children=None):
    """Build level 4 (barangays and sub-municipalities): known, and complete when the release approximates.

    Takes the barangay table (psgc.barangay_table), drops the source's reserved areas, applies the
    release's recodes, merges and plotted splits to the source, then runs the matching passes
    (matching.run_passes). Complete is known with the approximated splits (written to dist/complete/).
    """
    corrections = release.bgysubmuns
    psgc_df = psgc_df.rename(columns=BGY_PARENT_COLUMNS)
    bgysubmuns_gdf = read_source(release, "bgysubmuns").to_crs(epsg=UTM_51N)
    bgysubmuns_gdf["psgc_code"] = parent_psgc(bgysubmuns_gdf, "adm4_pcode", "")

    # Drop forest reserves, unclaimed areas and watersheds, except old Manila's (Tutuban, North Cemetery)
    bgysubmuns_gdf = bgysubmuns_gdf[
        (bgysubmuns_gdf["psgc_code"] % 1000 < corrections.reserved_min)
        | (bgysubmuns_gdf["adm4_pcode"].str.startswith(corrections.keep_reserved_prefix))
    ].copy()
    bgysubmuns_gdf["src_pcode"] = bgysubmuns_gdf["adm4_pcode"]
    bgysubmuns_gdf["geom_src"] = "source"
    apply_recodes(bgysubmuns_gdf, release.recodes, ADM4_PCODES)
    bgysubmuns_gdf = apply_merges(bgysubmuns_gdf, corrections.merges)
    if release.edits.plotted:
        splits = read_splits(release.edits.plotted, bgysubmuns_gdf.crs)
        bgysubmuns_gdf = add_daughters(bgysubmuns_gdf, splits, psgc_df, "plotted")

    joined = run_passes(bgysubmuns_gdf, psgc_df, release)
    check_shapeless(joined, corrections.shapeless)
    joined = joined[[c for c in JOINED_COLUMNS if not c.startswith("shape_")] + ["src_pcode", "geom_src"]]
    joined.loc[joined.geometry.isna(), "geom_src"] = "none"

    joined = add_geometry_measures(joined, epsg_code=UTM_51N)
    joined["adm1_psgc"] = parent_psgc(joined, "adm1_pcode", "00000000")
    joined["adm2_psgc"] = parent_psgc(joined, "adm2_pcode", "00000")
    joined["adm3_psgc"] = parent_psgc(joined, "adm3_pcode", "000")
    fix_adm4_parents(joined, release)
    keep = ["adm1_psgc", "adm2_psgc", "adm3_psgc", "psgc_code", "name", "geo_level", "geom_src"] + MEASURES
    names = ["adm1_psgc", "adm2_psgc", "adm3_psgc", "adm4_psgc", "adm4_en", "geo_level", "geom_src"] + MEASURES
    outputs = {"": finish(joined, keep, names)}
    if release.edits.approximated:
        splits = read_splits(release.edits.approximated, joined.crs)
        outputs[COMPLETE] = finish(approximate(joined, splits), keep, names)
    return outputs
