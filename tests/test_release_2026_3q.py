#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""releases/2026-3q.toml against PSA's own data: its recodes are exactly the transfers PSA published, and its
edit files are what the scripts make from their inputs.

Marked integration: it reads data/psgc/ and data/edit/. The edit files' rerun needs the base adm4 shapefile,
a raw source (scripts/sources.py fetch), and is skipped where it isn't fetched (CI).
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

import approximate_split
import plot_traverse
from ph_psgc_shape.release import load_release

pytestmark = pytest.mark.integration

REPO = Path(__file__).parent.parent
RELEASE = load_release(REPO / "releases" / "2026-3q.toml", root=REPO, check_sources=False)
EDIT = REPO / "data" / "edit" / "20261025"
BASE = REPO / "data" / "edit" / "20240210" / "ph_adm4_20240210.shp"


def transfers(publication):
    """Every Transferred row of a publication's Summary of Changes, as (old code, new code), 10 digits each."""
    with open(REPO / "data" / "psgc" / publication / "summary-of-changes.csv", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["Unit Type"].startswith("Transferred")]
    return [(r["Old Code"].strip().zfill(10), r["New Code"].strip().zfill(10)) for r in rows]


def test_every_transfer_is_one_of_the_releases_prefix_moves():
    moves = {r.from_prefix: r.to_prefix for r in RELEASE.recodes}
    rows = transfers("2024-2q") + transfers("2025-07")
    assert len(rows) == 1849
    for old, new in rows:
        assert old[5:] == new[5:], f"{old} → {new} isn't a pure prefix move"
        assert moves.get(old[:5]) == new[:5], f"{old} → {new} isn't one of the release's recodes"


def test_every_recode_moves_something():
    used = {old[:5] for old, _ in transfers("2024-2q") + transfers("2025-07")}
    assert {r.from_prefix for r in RELEASE.recodes} == used


@pytest.mark.skipif(not BASE.is_file(), reason="the raw sources aren't fetched (scripts/sources.py fetch)")
@pytest.mark.parametrize(("script", "name"), [(plot_traverse, "plotted"), (approximate_split, "approximated")])
def test_the_edit_files_are_what_their_scripts_make(tmp_path, script, name):
    assert script.run(EDIT, tmp_path) == 0
    assert (tmp_path / f"{name}.geojson").read_bytes() == (EDIT / f"{name}.geojson").read_bytes()
    assert (tmp_path / f"{name}-report.md").read_text() == (EDIT / f"{name}-report.md").read_text()
