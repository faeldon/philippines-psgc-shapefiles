#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Run the named levels of a release, in level order."""
from __future__ import annotations

import datetime
from pathlib import Path

from . import levels as _levels
from .psgc import barangay_table, load_psgc_table
from .psgc_data import load_manifest

# The levels run can build, in the order it builds and writes them.
LEVELS = {
    "country": _levels.country,
    "region": _levels.region,
    "provdists": _levels.provdists,
    "municities": _levels.municities,
    "bgysubmuns": _levels.bgysubmuns,
}

# A level that rebuilds units from the level below it, and that level.
CHILDREN = {"region": "provdists", "municities": "bgysubmuns"}


def _rebuilds(release, name):
    """The codes a release rebuilds at a level (none for a level that never rebuilds)."""
    if release is None:
        return ()
    return {"region": release.region.rebuild, "municities": release.municities.rebuild}.get(name, ())


def build_order(release, levels):
    """The levels to build, in order: the named ones, each after the level it rebuilds from, if any."""
    needed = set(levels) | {CHILDREN[name] for name in levels if _rebuilds(release, name)}
    order = [name for name in LEVELS if name in needed]
    for parent, child in CHILDREN.items():
        if parent in needed and child in needed and order.index(child) > order.index(parent):
            order.remove(child)
            order.insert(order.index(parent), child)
    return order


def run(release, levels=("municities",), out_dir="dist"):
    """Read the release's PSGC table, build the named levels, and write each to out_dir.

    The default builds municities only, as the CLI always has. A level that rebuilds units from the level
    below (the release's region or municities rebuild) has that level built first, and written only if
    it's named too. An unknown level name raises ValueError before anything is read.
    """
    unknown = set(levels) - LEVELS.keys()
    if unknown:
        raise ValueError(f"Unknown level(s): {', '.join(sorted(unknown))}. Known: {', '.join(LEVELS)}")
    df = load_psgc_table(release)
    if df is None:
        return

    print("==== PSGC Table Read =====")
    print(df.head())
    print(df.shape)

    built = {}
    for name in build_order(release, levels):
        child = built.get(CHILDREN.get(name), {}).get("")
        built[name] = LEVELS[name](barangay_table(df) if name == "bgysubmuns" else df, release, child)
    stamp = _stamp(release)
    for name in LEVELS:
        if name in levels:
            for folder, gdf in built[name].items():
                _levels.write_level(gdf, _levels.STEMS[name], str(Path(out_dir) / folder), stamp)


def _stamp(release):
    """The date a release's zips carry: its PSGC publication's as_of (so a rebuild writes the same bytes)."""
    if release is None:
        return _levels.ZIP_EPOCH
    return datetime.date.fromisoformat(load_manifest(release.psgc.publication).as_of)
