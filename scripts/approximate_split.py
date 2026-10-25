#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Approximate the new barangays no published boundary describes: one straight cut each, sized to a target.

    python scripts/approximate_split.py data/edit/<date> [--out <dir>]

Reads <dir>/approximations.toml (see its header), the base adm4 it names and the PSGC publication's 2024
populations, and writes approximated.geojson and approximated-report.md (to --out, by default the same
folder). Each daughter is the part of its mothers on one side of a straight line, the line moved by
bisection until the part's area is within AREA_TOLERANCE of the target. The same inputs write the same
files. Exits 1 if a target can't be met.
"""
from __future__ import annotations

# Its command line and report writing follow plot_traverse.py, the other edit script, on purpose.
# pylint: disable=duplicate-code

import argparse
import math
import sys
import tomllib
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely import union_all
from shapely.geometry import Point, Polygon

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
# pylint: disable-next=wrong-import-position
from ph_psgc_shape.psgc import load_table  # noqa: E402

# pylint: disable-next=wrong-import-position
from ph_psgc_shape.psgc_data import load_manifest  # noqa: E402

CRS = 32651
AREA_TOLERANCE = 0.01


def half_plane(origin, direction, offset, reach):
    """The part of the plane where (x - origin) · direction >= offset, as a square reach metres across."""
    ux, uy = direction
    vx, vy = -uy, ux
    cx, cy = origin[0] + ux * offset, origin[1] + uy * offset
    return Polygon(
        [
            (cx + vx * reach, cy + vy * reach),
            (cx + vx * reach + ux * reach, cy + vy * reach + uy * reach),
            (cx - vx * reach + ux * reach, cy - vy * reach + uy * reach),
            (cx - vx * reach, cy - vy * reach),
        ]
    )


def cut(whole, direction, target):
    """The part of whole beyond a line across direction whose area is target, found by bisection."""
    origin = (whole.centroid.x, whole.centroid.y)
    xs, ys = np.asarray(whole.exterior.coords if whole.geom_type == "Polygon" else whole.convex_hull.exterior.coords).T
    proj = (xs - origin[0]) * direction[0] + (ys - origin[1]) * direction[1]
    lo, hi = float(proj.min()), float(proj.max())
    reach = 4 * (hi - lo) + 1000
    part = whole
    for _ in range(80):
        mid = (lo + hi) / 2
        part = whole.intersection(half_plane(origin, direction, mid, reach))
        if part.area > target:
            lo = mid
        else:
            hi = mid
    return part


def unit(dx, dy):
    """(dx, dy) scaled to length 1."""
    n = math.hypot(dx, dy)
    return dx / n, dy / n


def long_axis(geom, away_from):
    """The direction of geom's longest dimension, pointing away from the point away_from."""
    rect = list(geom.minimum_rotated_rectangle.exterior.coords)
    sides = [(rect[i], rect[i + 1]) for i in range(4)]
    (x0, y0), (x1, y1) = max(sides, key=lambda s: math.dist(*s))
    u = unit(x1 - x0, y1 - y0)
    c = geom.centroid
    if (c.x - away_from.x) * u[0] + (c.y - away_from.y) * u[1] < 0:
        u = (-u[0], -u[1])
    return u


def run(edit_dir: Path, out_dir: Path) -> int:  # pylint: disable=too-many-locals
    """Cut every split in edit_dir/approximations.toml; write the GeoJSON and report; return 0 or 1."""
    with open(edit_dir / "approximations.toml", "rb") as f:
        spec = tomllib.load(f)
    base = gpd.read_file(REPO / spec["source"]).to_crs(CRS)
    pcode, adm3 = "ADM4_PCODE", "ADM3_PCODE"  # the base adm4 shapefile's own column names
    population = load_table(load_manifest(spec["publication"])).set_index("psgc_code")["pop_2024"]
    features, failed = [], False
    report = ["# Approximated splits", "", "Indicative only: each is one straight cut, sized to a target area.", ""]
    report += [
        "| Barangay | Code | Mothers | Rule | Target (m²) | Cut (m²) | Off target |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for s in spec["split"]:
        whole = union_all(list(base.loc[base[pcode].isin(s["mothers"])].geometry))
        if s["size"] == "population":
            daughter, mother = float(population[s["code"]]), float(population[s["mother_codes"][0]])
            target = whole.area * daughter / (daughter + mother)
        else:
            target = float(s["area"])
        if s["rule"] == "long-axis":
            city = union_all(list(base.loc[base[adm3] == s["away_from_adm3"]].geometry)).centroid
            direction = long_axis(whole, city)
        else:
            point = gpd.GeoSeries([Point(*s["toward"])], crs=4326).to_crs(CRS).iloc[0]
            direction = unit(point.x - whole.centroid.x, point.y - whole.centroid.y)
        part = cut(whole, direction, target)
        off = part.area / target - 1
        failed |= abs(off) > AREA_TOLERANCE
        features.append({"code": s["code"], "name": s["name"], "mothers": ",".join(s["mothers"]), "geometry": part})
        report.append(
            f"| {s['name']} | {s['code']} | {', '.join(s['mothers'])} | {s['rule']}, {s['size']} | {target:,.0f}"
            f" | {part.area:,.0f} | {off:+.2%} |"
        )
    report += ["", "Bases:", ""] + [f"- {s['name']}: {' '.join(s['basis'].split())}" for s in spec["split"]]
    report += ["", "Result: " + ("FAILED" if failed else "every target met") + "."]
    out_dir.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(features, crs=CRS).to_file(out_dir / "approximated.geojson", driver="GeoJSON")
    (out_dir / "approximated-report.md").write_text("\n".join(report) + "\n")
    print("\n".join(report))
    return 1 if failed else 0


def main(argv=None) -> int:
    """Cut the splits in the edit folder named on the command line, and return an exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("edit_dir", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    return run(args.edit_dir, args.out or args.edit_dir)


if __name__ == "__main__":
    sys.exit(main())
