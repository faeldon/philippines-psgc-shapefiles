#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Check a directory of PH_Adm* CSVs and shapefile zips against CONTRACT 2, or diff two such directories.

    python scripts/check_dist.py check <dist_dir> [--release releases/2026-3q.toml]
    python scripts/check_dist.py diff <a_dist_dir> <b_dist_dir>

check also requires each level's zip to hold one EPSG:32651 layer whose attributes equal its CSV; diff also
compares the zips' geometry. Both print one line per problem and exit 1 if there are any.
"""
from __future__ import annotations

import argparse
import contextlib
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio

REPO = Path(__file__).resolve().parent.parent
RELEASE = REPO / "releases/2026-3q.toml"


@dataclass(frozen=True)
class Level:
    """One output level: its file, its code column, its parents', and the PSGC geo_levels it holds."""

    name: str
    stem: str
    code: str | None
    parents: tuple[str, ...]
    geo_levels: tuple[str, ...]


LEVELS = (
    Level("adm0", "PH_Adm0_Country", None, (), ()),
    Level("adm1", "PH_Adm1_Regions", "adm1_psgc", (), ("Reg",)),
    Level("adm2", "PH_Adm2_ProvDists", "adm2_psgc", ("adm1_psgc",), ("Prov", "Dist")),
    Level("adm3", "PH_Adm3_MuniCities", "adm3_psgc", ("adm1_psgc", "adm2_psgc"), ("Mun", "City", "SGU")),
    Level("adm4", "PH_Adm4_BgySubMuns", "adm4_psgc", ("adm1_psgc", "adm2_psgc", "adm3_psgc"), ("Bgy", "SubMun")),
)
BY_CODE = {level.code: level for level in LEVELS if level.code}

# Codes a level holds that the PSGC table doesn't list at its geo_levels, and the reverse, each with
# the reason it's accepted. Anything not listed here fails the check.
KNOWN_EXTRA: dict[str, dict[int, str]] = {
    "adm1": {},
    "adm2": {
        990100000: "City of Isabela (Not a Province), handled by hand as a province-level row",
        1999900000: "Interim Province Code for 63 barangays of BARMM: in the PSGC table without a geo_level",
    },
    "adm3": {},
    "adm4": {
        1303901906: "Manila North Cemetery: a source polygon, not a PSGC barangay; kept so the map has no hole",
        1303901907: "Tutuban Mall: a source polygon, not a PSGC barangay; kept so the map has no hole",
    },
}
KNOWN_MISSING: dict[str, dict[int, str]] = {"adm1": {}, "adm2": {}, "adm3": {}, "adm4": {}}
# adm0 has no code column: one row per polygon of the singlepart country shapefile.
ADM0_ROWS = {"expected": 1, "known": 3640, "reason": "built from the singlepart country shapefile"}

MEASURE_TOLERANCE = {"len_crs": 1, "area_crs": 1, "len_km": 0, "area_km2": 0}

# adm4's geom_src values (ph_psgc_shape.geometry.GEOM_SOURCES): where each row's shape came from. Known's adm4,
# in dist/, never approximates; complete's, in dist/complete/, differs from it only in approximated rows.
GEOM_SOURCES = ("source", "dissolved", "plotted", "approximated", "none")
KNOWN_GEOM_SOURCES = tuple(s for s in GEOM_SOURCES if s != "approximated")
COMPLETE = "complete"

# Each zip holds one shapefile named for its level, in UTM zone 51N.
ZIP_CRS = 32651
ZIP_MEMBERS = (".cpg", ".dbf", ".prj", ".shp", ".shx")
GEOMETRY_TOLERANCE = 0.001  # metres


def read_level(dist_dir: Path, level: Level) -> pd.DataFrame | None:
    """Read a level's CSV, or None if the directory doesn't have it."""
    path = Path(dist_dir) / f"{level.stem}.csv"
    return pd.read_csv(path) if path.exists() else None


def zip_path(dist_dir, level: Level) -> Path:
    """Where a level's shapefile zip is in dist_dir."""
    return Path(dist_dir) / f"{level.stem}.shp.zip"


def zip_layer(path: Path, stem: str) -> str | None:
    """The zip's layer for stem: named stem, or stem.shp in the pre-093 double-extension layout."""
    names = [str(name) for name, _ in pyogrio.list_layers(f"zip://{path}")]
    return next((name for name in (stem, f"{stem}.shp") if name in names), None)


def check_zip(dist_dir, level: Level, csv_df: pd.DataFrame) -> list[str]:
    """Return the problems with a level's zip: its layout, its CRS, and any attribute that differs from the CSV."""
    path = zip_path(dist_dir, level)
    if not path.exists():
        return [f"{level.name}: {path.name} is missing"]
    problems = []
    layers = [str(name) for name, _ in pyogrio.list_layers(f"zip://{path}")]
    if layers != [level.stem]:
        problems.append(f"{level.name}: {path.name} layers are {layers}, expected [{level.stem!r}]")
    with zipfile.ZipFile(path) as archive:
        members = sorted(archive.namelist())
    if members != [f"{level.stem}{ext}" for ext in ZIP_MEMBERS]:
        problems.append(f"{level.name}: {path.name} members are {members}")
    layer = zip_layer(path, level.stem)
    if layer is None:
        return problems
    crs = pyogrio.read_info(f"zip://{path}", layer=layer)["crs"]
    if crs != f"EPSG:{ZIP_CRS}":
        problems.append(f"{level.name}: {path.name} CRS is {crs}, expected EPSG:{ZIP_CRS}")
    attrs = gpd.read_file(f"zip://{path}", layer=layer, ignore_geometry=True)
    problems.extend(_diff_frames(f"{level.name} zip vs csv", pd.DataFrame(attrs), csv_df, None))
    return problems


def untrimmed(name: str, df: pd.DataFrame) -> list[str]:
    """One problem per text column holding values with leading or trailing whitespace."""
    problems = []
    for col in df.columns:
        if not pd.api.types.is_string_dtype(df[col]):
            continue
        values = df[col].dropna().astype(str)
        bad = values[values != values.str.strip()]
        if len(bad):
            problems.append(f"{name}: {len(bad)} {col} value(s) with leading/trailing whitespace, e.g. {bad.iloc[0]!r}")
    return problems


def check_level(level: Level, df, frames, psgc_codes, name=None) -> list[str]:
    """Return CONTRACT 2's problems with one level's CSV: grain, parents in frames, and codes against the PSGC table."""
    name = name or level.name
    if level.code is None:
        if len(df) not in (ADM0_ROWS["expected"], ADM0_ROWS["known"]):
            return [f"{name}: {len(df)} rows, expected {ADM0_ROWS['known']} ({ADM0_ROWS['reason']})"]
        return []
    problems = []
    codes = df[level.code]
    if codes.isna().any():
        problems.append(f"{name}: {int(codes.isna().sum())} null {level.code}")
    dups = sorted(codes[codes.duplicated()].dropna().astype(int).unique())
    if dups:
        problems.append(f"{name}: duplicate {level.code}: {dups[:10]}")
    for parent in level.parents:
        parent_df = frames[BY_CODE[parent].name]
        if parent_df is None:
            continue
        orphans = sorted(set(df[parent].dropna().astype(int)) - set(parent_df[parent].dropna().astype(int)))
        if orphans:
            problems.append(f"{name}: {parent} not in {BY_CODE[parent].name}: {orphans[:10]}")
    have = set(codes.dropna().astype(int))
    expected = psgc_codes.get(level.name, set())
    extra = sorted(have - expected - KNOWN_EXTRA[level.name].keys())
    missing = sorted(expected - have - KNOWN_MISSING[level.name].keys())
    if extra:
        problems.append(f"{name}: {len(extra)} code(s) not in the PSGC table at {level.geo_levels}: {extra[:10]}")
    if missing:
        problems.append(f"{name}: {len(missing)} PSGC code(s) missing: {missing[:10]}")
    return problems


def check_geom_src(name: str, df: pd.DataFrame, allowed=GEOM_SOURCES) -> list[str]:
    """Return the problems with adm4's geom_src: each row has an allowed value, and none exactly when it has no shape.

    A row has no shape when its length and area are 0, which the CSV alone shows (CI has no LFS zips).
    """
    if "geom_src" not in df.columns:
        return [f"{name}: no geom_src column"]
    problems = []
    bad = df[~df["geom_src"].isin(allowed)]
    if len(bad):
        values = sorted(bad["geom_src"].fillna("<empty>").astype(str).unique())
        problems.append(f"{name}: {len(bad)} geom_src value(s) not in {list(allowed)}: {values}")
    shapeless = (df["len_crs"] == 0) & (df["area_crs"] == 0)
    none = df["geom_src"] == "none"
    for rows, problem in ((none & ~shapeless, "geom_src none with a shape"), (shapeless & ~none, "no shape")):
        if rows.any():
            sample = sorted(df.loc[rows, "adm4_psgc"].dropna().astype(int))[:10]
            problems.append(f"{name}: {int(rows.sum())} row(s) with {problem} but geom_src not matching: {sample}")
    return problems


def check_complete(dist_dir, frames, psgc_codes, zips: bool = True) -> list[str]:
    """Return the problems with dist_dir/complete/'s adm4: CONTRACT 2 against dist_dir's levels, and its
    difference from known's adm4 (dist_dir's), which may only be in rows complete approximates."""
    level, known = LEVELS[-1], frames["adm4"]
    complete_dir = Path(dist_dir) / COMPLETE
    df = read_level(complete_dir, level)
    if df is None:
        return [f"complete: {level.stem}.csv is missing"]
    problems = untrimmed("complete adm4", df)
    if zips:
        problems.extend(f"complete {p}" for p in check_zip(complete_dir, level, df))
    problems.extend(check_level(level, df, frames, psgc_codes, name="complete adm4"))
    problems.extend(check_geom_src("complete adm4", df))
    if known is None or list(df.columns) != list(known.columns):
        return problems + ["complete adm4: columns differ from known's adm4"]
    if set(df[level.code]) != set(known[level.code]):
        return problems + ["complete adm4: codes differ from known's adm4"]
    a, b = known.set_index(level.code).sort_index(), df.set_index(level.code).sort_index()
    differs = ~((a == b) | (a.isna() & b.isna())).all(axis=1)
    unflagged = sorted(int(c) for c in differs[differs].index if b.loc[c, "geom_src"] != "approximated")
    if unflagged:
        problems.append(
            f"complete adm4: {len(unflagged)} row(s) differ from known but aren't approximated: {unflagged[:10]}"
        )
    return problems


def check_dir(dist_dir, psgc_codes: dict[str, set[int]], zips: bool = True) -> list[str]:
    """Return every CONTRACT 2 problem in dist_dir; psgc_codes maps level name to the PSGC table's codes.

    adm4 is known's: no row approximated. When dist_dir has a complete/ folder, its adm4 is checked too
    (check_complete). zips=False checks the CSVs alone, for a checkout without git-lfs, where the zips are
    pointer files.
    """
    problems = []
    frames = {level.name: read_level(dist_dir, level) for level in LEVELS}
    for level in LEVELS:
        df = frames[level.name]
        if df is None:
            problems.append(f"{level.name}: {level.stem}.csv is missing")
            continue
        problems.extend(untrimmed(level.name, df))
        if zips:
            problems.extend(check_zip(dist_dir, level, df))
        problems.extend(check_level(level, df, frames, psgc_codes))
    if frames["adm4"] is not None:
        problems.extend(check_geom_src("adm4", frames["adm4"], allowed=KNOWN_GEOM_SOURCES))
    if (Path(dist_dir) / COMPLETE).is_dir():
        problems.extend(check_complete(dist_dir, frames, psgc_codes, zips))
    return problems


def _diff_frames(name: str, a: pd.DataFrame, b: pd.DataFrame, key: str | None) -> list[str]:
    problems = []
    if list(a.columns) != list(b.columns):
        return [f"{name}: columns differ: {list(a.columns)} vs {list(b.columns)}"]
    a_types, b_types = a.dtypes.astype(str), b.dtypes.astype(str)
    for col in a.columns:
        if a_types[col] != b_types[col]:
            problems.append(f"{name}: {col} dtype {a_types[col]} vs {b_types[col]}")
    if len(a) != len(b):
        problems.append(f"{name}: {len(a)} rows vs {len(b)}")
    if key is None:
        if len(a) != len(b):
            return problems
        a, b = a.reset_index(drop=True), b.reset_index(drop=True)
    else:
        only_a = sorted(set(a[key]) - set(b[key]))
        only_b = sorted(set(b[key]) - set(a[key]))
        if only_a:
            problems.append(f"{name}: {len(only_a)} {key} only in the first: {only_a[:10]}")
        if only_b:
            problems.append(f"{name}: {len(only_b)} {key} only in the second: {only_b[:10]}")
        common = sorted(set(a[key]) & set(b[key]))
        a = a.drop_duplicates(key).set_index(key).loc[common]
        b = b.drop_duplicates(key).set_index(key).loc[common]
    return problems + _diff_values(name, a, b)


def _diff_values(name: str, a: pd.DataFrame, b: pd.DataFrame) -> list[str]:
    """Compare aligned frames column by column: measures within MEASURE_TOLERANCE, the rest exactly."""
    problems = []
    for col in a.columns:
        tolerance = MEASURE_TOLERANCE.get(col)
        if tolerance is None:
            changed = ~((a[col] == b[col]) | (a[col].isna() & b[col].isna()))
        else:
            changed = (a[col] - b[col]).abs() > tolerance
        if changed.any():
            sample = list(changed[changed].index[:5])
            problems.append(f"{name}: {col} differs in {int(changed.sum())} row(s), e.g. {sample}")
    return problems


def read_zip_geometry(dist_dir, level: Level) -> gpd.GeoDataFrame:
    """A level zip's geometry, indexed by code (adm0: by row), from either zip layout."""
    path = zip_path(dist_dir, level)
    layer = zip_layer(path, level.stem)
    columns = [level.code] if level.code else []
    gdf = gpd.read_file(f"zip://{path}", layer=layer, columns=columns)
    return gdf.set_index(level.code) if level.code else gdf


def diff_zip_geometry(dir_a, dir_b, level: Level) -> list[str]:
    """Return the codes whose shape differs, beyond GEOMETRY_TOLERANCE, between two directories' zips."""
    have = [zip_path(d, level).exists() for d in (dir_a, dir_b)]
    if not all(have):
        return [f"{level.name}: {level.stem}.shp.zip is in only one directory"] if any(have) else []
    a, b = read_zip_geometry(dir_a, level), read_zip_geometry(dir_b, level)
    name = f"{level.name} zip"
    problems = []
    if level.code is None and len(a) != len(b):
        return [f"{name}: {len(a)} shapes vs {len(b)}"]
    only_a, only_b = sorted(set(a.index) - set(b.index)), sorted(set(b.index) - set(a.index))
    if only_a:
        problems.append(f"{name}: {len(only_a)} {level.code} only in the first: {only_a[:10]}")
    if only_b:
        problems.append(f"{name}: {len(only_b)} {level.code} only in the second: {only_b[:10]}")
    common = a.index.intersection(b.index)
    geom_a, geom_b = a.geometry.loc[common], b.geometry.loc[common]
    # A row with no shape on both sides (Manila's sub-municipalities) is unchanged, not different.
    same = geom_a.geom_equals_exact(geom_b, tolerance=GEOMETRY_TOLERANCE) | (geom_a.isna() & geom_b.isna())
    if not same.all():
        moved = list(same[~same].index[:5])
        problems.append(f"{name}: geometry differs in {int((~same).sum())} row(s), e.g. {moved}")
    return problems


def csv_only(dist_dir) -> bool:
    """Whether a directory holds the CSVs without the zips, as the committed dist/ does (they're release assets)."""
    return not any(Path(dist_dir).glob("*.shp.zip"))


def diff_dirs(dir_a, dir_b) -> list[str]:
    """Return every difference between two directories of PH_Adm* CSVs and zips, level by level.

    Each directory's complete/ adm4 is compared too, when either has one. When either directory is
    CSV-only (csv_only), the zips aren't compared: only the CSVs are.
    """
    problems = []
    zips = not (csv_only(dir_a) or csv_only(dir_b))
    pairs = [(dir_a, dir_b, level, level.name) for level in LEVELS]
    pairs.append((Path(dir_a) / COMPLETE, Path(dir_b) / COMPLETE, LEVELS[-1], "complete adm4"))
    for a_dir, b_dir, level, name in pairs:
        a, b = read_level(a_dir, level), read_level(b_dir, level)
        if a is None or b is None:
            if (a is None) != (b is None):
                problems.append(f"{name}: {level.stem}.csv is in only one directory")
        else:
            problems.extend(_diff_frames(name, a, b, level.code))
        if zips:
            problems.extend(f"{name}{p[len(level.name):]}" for p in diff_zip_geometry(a_dir, b_dir, level))
    return problems


def psgc_codes_by_level(release_path: Path) -> dict[str, set[int]]:
    """The PSGC table's codes for each level, from the same prepared table the release's pipeline joins to."""
    sys.path.insert(0, str(REPO / "src"))
    # pylint: disable-next=import-outside-toplevel
    from ph_psgc_shape import psgc, release

    # The release's paths are relative to the repo, wherever check runs from.
    release_path = Path(release_path).resolve()
    with contextlib.chdir(REPO):
        table = psgc.load_psgc_table(release.load_release(release_path, check_sources=False))
    return {
        level.name: set(table.loc[table["geo_level"].isin(level.geo_levels), "psgc_code"].astype(int))
        for level in LEVELS
        if level.code
    }


def main(argv=None) -> int:
    """Run check or diff and return an exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("dist_dir", type=Path)
    check.add_argument("--release", type=Path, default=RELEASE)
    check.add_argument("--csv-only", action="store_true", help="check the CSVs alone (the committed dist/)")
    diff = sub.add_parser("diff")
    diff.add_argument("a", type=Path)
    diff.add_argument("b", type=Path)
    args = parser.parse_args(argv)

    if args.command == "check":
        problems = check_dir(args.dist_dir, psgc_codes_by_level(args.release), zips=not args.csv_only)
    else:
        problems = diff_dirs(args.a, args.b)
        for side in (args.a, args.b):
            if csv_only(side):
                print(f"check_dist diff: zips not compared: {side} has none (only the CSVs are)")
    for problem in problems:
        print(problem)
    print(f"check_dist {args.command}: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
