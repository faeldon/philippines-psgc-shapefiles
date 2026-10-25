#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Plot the barangays a law describes by bearing and distance, and place them against their mothers.

    python scripts/plot_traverse.py data/edit/<date> [--out <dir>]

Reads <dir>/traverses.toml (see its header) and the base adm4 it names, and writes plotted.geojson and
plotted-report.md (to --out, by default the same folder). Each polygon is plotted in metres from its tie
point, its closure and area checked against the law's, then placed: the tie points' coordinates aren't
published, so each group is fitted to its mothers by rotation (within MAX_ROTATION, since the laws'
bearings are grid bearings) and translation. fit = "iou" matches the group's union to the mothers'
shape; fit = "edges" lays the corners the group names along the mothers' boundary with the units it
adjoins. Each polygon is then clipped to its mothers; within a group, an overlap goes to the earlier
polygon and a leftover piece of the mothers to the polygon it shares the most border with.
Exits 1 if any check fails.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely import affinity, union_all
from shapely.geometry import LineString, MultiPoint, Polygon

REPO = Path(__file__).resolve().parent.parent
CRS = 32651
AREA_TOLERANCE = 0.01  # a plotted polygon's area against the law's, before placement
COVER_TOLERANCE = 1.0  # square metres
MAX_ROTATION = 3.0  # degrees

BEARING = re.compile(r"^([NS]) (\d{2})°(\d{2})' ([EW])$")
DUE = {"Due North": 0.0, "Due East": 90.0, "Due South": 180.0, "Due West": 270.0}


def azimuth(bearing: str) -> float:
    """A bearing (N 45°30' E, or Due North) as an azimuth in degrees clockwise from north."""
    if bearing in DUE:
        return DUE[bearing]
    m = BEARING.match(bearing)
    if m is None:
        raise ValueError(f"not a bearing: {bearing!r}")
    ns, deg, mins, ew = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
    angle = deg + mins / 60
    return {("N", "E"): angle, ("S", "E"): 180 - angle, ("S", "W"): 180 + angle, ("N", "W"): 360 - angle}[(ns, ew)]


def step(x, y, bearing, distance):
    """The point distance metres from (x, y) along bearing."""
    az = math.radians(azimuth(bearing))
    return x + distance * math.sin(az), y + distance * math.cos(az)


def plot(tie_line, lines):
    """The corners of a traverse in metres from its tie point, and its closure error.

    Corner 1 is the tie line's end; each line runs to the next corner, and the last back to 1. The
    closure error is how far the last line ends from corner 1.
    """
    corners = [step(0.0, 0.0, *tie_line)]
    for bearing, distance in lines:
        corners.append(step(*corners[-1], bearing, distance))
    end = corners.pop()
    return corners, math.dist(end, corners[0])


@dataclass
class Plotted:
    """One polygon as the law gives it, plotted from its tie point."""

    code: int
    name: str
    stated: float
    corners: list
    closure: float
    corrections: list

    @property
    def shape(self):
        """The polygon its corners make (the closure error left open)."""
        return Polygon(self.corners).buffer(0)


def place(geom, theta, dx, dy):
    """geom rotated theta degrees counter-clockwise about its tie point (the origin), then shifted by (dx, dy)."""
    return affinity.translate(affinity.rotate(geom, theta, origin=(0, 0)), dx, dy)


def search(cost, start, spans, steps):
    """Minimise cost(theta, dx, dy) by a grid search around start, then finer grids around the best."""
    best = (cost(*start), start)
    for span, size in zip(spans, steps):
        theta0, dx0, dy0 = best[1]
        thetas = np.clip(np.arange(theta0 - span[0], theta0 + span[0] + 1e-9, size[0]), -MAX_ROTATION, MAX_ROTATION)
        for theta in np.unique(thetas):
            for dx in np.arange(dx0 - span[1], dx0 + span[1] + 1e-9, size[1]):
                for dy in np.arange(dy0 - span[1], dy0 + span[1] + 1e-9, size[1]):
                    c = cost(float(theta), float(dx), float(dy))
                    if c < best[0]:
                        best = (c, (float(theta), float(dx), float(dy)))
    return best


def fit_iou(group_shape, mothers):
    """Place group_shape to overlap mothers as much as it can: rotation and translation, by IoU.

    At each rotation the shift is searched around the one that lays the rotated shape's centroid on the
    mothers', so a rotation and its shift are found together.
    """
    c0 = mothers.centroid

    def shift(theta, ox, oy):
        g0 = affinity.rotate(group_shape, theta, origin=(0, 0)).centroid
        return c0.x - g0.x + ox, c0.y - g0.y + oy

    def cost(theta, ox, oy):
        g = place(group_shape, theta, *shift(theta, ox, oy))
        return -g.intersection(mothers).area / g.union(mothers).area

    score, (theta, ox, oy) = search(
        cost, (0.0, 0.0, 0.0), [(MAX_ROTATION, 300), (0.5, 30), (0.1, 4)], [(0.25, 25), (0.05, 5), (0.01, 1)]
    )
    return (theta, *shift(theta, ox, oy)), f"IoU {-score:.4f}"


def fit_edges(polygon, mothers, adjoining, edges):  # pylint: disable=too-many-locals
    """Place polygon so its corners edges[0]..edges[1] lie along the mothers' boundary with adjoining.

    The cost is the mean distance of points along those lines from that boundary, plus the area the
    polygon reaches outside its mothers, per metre of the lines.
    """
    first, last = edges
    path = LineString(polygon.corners[first - 1 : last])
    samples = MultiPoint([path.interpolate(d) for d in np.arange(0, path.length, 25.0)])
    target = mothers.boundary.intersection(adjoining.buffer(10.0))
    shape = polygon.shape

    def cost(theta, dx, dy):
        pts = place(samples, theta, dx, dy)
        outside = place(shape, theta, dx, dy).difference(mothers).area
        return float(np.mean([target.distance(p) for p in pts.geoms])) + outside / path.length

    c0, g0 = mothers.centroid, shape.centroid
    start = (0.0, c0.x - g0.x, c0.y - g0.y)
    score, params = search(
        cost, start, [(MAX_ROTATION, 3000), (0.5, 200), (0.1, 20)], [(1.0, 100), (0.1, 10), (0.02, 1)]
    )
    return params, f"mean distance to the shared boundary {score:.1f} m (with the outside penalty)"


def clip_group(shapes, mothers):
    """Clip each placed shape to the mothers; an overlap goes to the earlier shape, a leftover to a neighbour.

    Returns the clipped shapes, in order. A leftover piece of the mothers goes to the shape it shares the
    longest border with (or, touching none, the nearest).
    """
    clipped, taken = [], None
    for s in shapes:
        part = s.intersection(mothers)
        if taken is not None:
            part = part.difference(taken)
        clipped.append(part)
        taken = part if taken is None else taken.union(part)
    if len(shapes) > 1:
        left = mothers.difference(taken)
        pieces = getattr(left, "geoms", [left])
        for piece in pieces:
            if piece.area <= 0:
                continue
            border = [piece.boundary.intersection(c.buffer(0.01)).length for c in clipped]
            i = int(np.argmax(border)) if max(border) > 0 else int(np.argmin([piece.distance(c) for c in clipped]))
            clipped[i] = clipped[i].union(piece)
    return [polygonal(c) for c in clipped]


def polygonal(geom):
    """A geometry's polygon parts: what an overlay leaves of a shape, without its stray lines and points."""
    parts = [g for g in getattr(geom, "geoms", [geom]) if g.geom_type in ("Polygon", "MultiPolygon")]
    return union_all(parts)


def run(edit_dir: Path, out_dir: Path) -> int:  # pylint: disable=too-many-locals
    """Plot, place and clip every group in edit_dir/traverses.toml; write the GeoJSON and report; return 0 or 1."""
    with open(edit_dir / "traverses.toml", "rb") as f:
        spec = tomllib.load(f)
    base = gpd.read_file(REPO / spec["source"]).to_crs(CRS)
    pcode = "ADM4_PCODE"  # the base adm4 shapefile's own column name
    report, features, failed = ["# Plotted splits", ""], [], False
    for group in spec["group"]:
        mothers = union_all(list(base.loc[base[pcode].isin(group["mothers"])].geometry))
        polys = []
        for p in group["polygon"]:
            corners, closure = plot(p["tie_line"], p["lines"])
            polys.append(Plotted(p["code"], p["name"], p["area"], corners, closure, p.get("corrections", [])))
        if group["fit"] == "iou":
            params, score = fit_iou(union_all([q.shape for q in polys]), mothers)
        else:
            adjoining = union_all(list(base.loc[base[pcode].isin(group["adjoins"])].geometry))
            params, score = fit_edges(polys[0], mothers, adjoining, group["edges"])
        placed = [place(q.shape, *params) for q in polys]
        clipped = clip_group(placed, mothers)
        whole = union_all(clipped)
        cover_gap = mothers.difference(whole).area if len(polys) > 1 else 0.0
        report += [f"## {group['name']}", "", f"{group['law']}: {group['url']}", ""]
        report += [
            f"Placed by {group['fit']} fit: rotation {params[0]:.2f}°,"
            f" shift ({params[1]:.1f}, {params[2]:.1f}) m; {score}."
        ]
        plotted_area = sum(q.shape.area for q in polys)
        report += [
            f"Mothers {', '.join(group['mothers'])}: {mothers.area:,.0f} m²;"
            f" the plotted polygons: {plotted_area:,.0f} m².",
            "",
        ]
        report += [
            "| Barangay | Code | Lines | Closure (m) | Stated (m²) | Plotted (m²) | Plotted vs stated | Clipped (m²) |"
        ]
        report += ["| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for q, c in zip(polys, clipped):
            off = q.shape.area / q.stated - 1
            failed |= abs(off) > AREA_TOLERANCE
            report.append(
                f"| {q.name} | {q.code} | {len(q.corners)} | {q.closure:.2f} | {q.stated:,.0f} | {q.shape.area:,.0f}"
                f" | {off:+.2%} | {c.area:,.0f} |"
            )
            features.append({"code": q.code, "name": q.name, "mothers": ",".join(group["mothers"]), "geometry": c})
        if cover_gap > COVER_TOLERANCE:
            failed = True
        report += ["", f"Cover: the clipped polygons leave {cover_gap:,.1f} m² of their mothers uncovered.", ""]
        corrections = [f"- {q.name}: {c}" for q in polys for c in q.corrections]
        report += (["Corrections to the law's text:", ""] + corrections + [""]) if corrections else []
    report += ["Result: " + ("FAILED" if failed else "every check passed") + "."]
    out_dir.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(features, crs=CRS).to_file(out_dir / "plotted.geojson", driver="GeoJSON")
    (out_dir / "plotted-report.md").write_text("\n".join(report) + "\n")
    print("\n".join(report))
    return 1 if failed else 0


def main(argv=None) -> int:
    """Plot the traverses in the edit folder named on the command line, and return an exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("edit_dir", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    return run(args.edit_dir, args.out or args.edit_dir)


if __name__ == "__main__":
    sys.exit(main())
