#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""pipeline.run builds exactly the named levels, in order, and rejects unknown names first."""
from __future__ import annotations

import datetime
from types import SimpleNamespace

import pandas as pd
import pytest

from ph_psgc_shape import pipeline

TABLE = pd.DataFrame(
    {
        "psgc_code": [100000000, 102800000, 102801000, 102801001],
        "name": ["Region I", "Ilocos Norte", "Adams", "Adams"],
        "geo_level": ["Reg", "Prov", "Mun", "Bgy"],
    }
)


@pytest.fixture
def recorded(monkeypatch):
    """Replace the table load and every level function; return the list of (level, frame) calls."""
    calls = []
    monkeypatch.setattr(pipeline, "load_psgc_table", lambda *_: TABLE.copy())
    for name in pipeline.LEVELS:
        monkeypatch.setitem(
            pipeline.LEVELS, name, lambda df, _release, _child, name=name: calls.append((name, df)) or {}
        )
    return calls


def test_unknown_level_raises_before_reading(monkeypatch):
    def unread(*_):
        raise AssertionError("read the PSGC table before rejecting the level")

    monkeypatch.setattr(pipeline, "load_psgc_table", unread)
    with pytest.raises(ValueError, match="nope"):
        pipeline.run(None, levels=("municities", "nope"))


def test_default_runs_municities_only(recorded):
    pipeline.run(None)
    assert [name for name, _ in recorded] == ["municities"]


def test_named_levels_run_in_level_order(recorded):
    pipeline.run(None, levels=("bgysubmuns", "region"))
    assert [name for name, _ in recorded] == ["region", "bgysubmuns"]


def test_bgysubmuns_gets_the_joined_barangay_table(recorded):
    pipeline.run(None, levels=("region", "bgysubmuns"))
    frames = dict(recorded)
    assert list(frames["region"]["psgc_code"]) == list(TABLE["psgc_code"])
    bgy = frames["bgysubmuns"]
    assert list(bgy["psgc_code"]) == [102801001]
    assert bgy.iloc[0]["adm3_en"] == "Adams" and bgy.iloc[0]["adm2_en"] == "Ilocos Norte"


def rebuilding(region=(), municities=()):
    """A release stand-in that rebuilds these region and municities codes."""
    return SimpleNamespace(
        psgc=SimpleNamespace(publication="2026-3q"),
        region=SimpleNamespace(rebuild=region),
        municities=SimpleNamespace(rebuild=municities),
    )


def test_a_rebuilding_level_has_its_children_built_first():
    order = pipeline.build_order(rebuilding(region=(1800000000,), municities=(1999901000,)), ("region", "municities"))
    assert order == ["provdists", "region", "bgysubmuns", "municities"]


def test_a_level_that_doesnt_rebuild_needs_no_children():
    assert pipeline.build_order(rebuilding(), ("region", "municities")) == ["region", "municities"]


def test_children_are_built_but_only_named_levels_are_written(monkeypatch, tmp_path):
    written, children = [], {}
    monkeypatch.setattr(pipeline, "load_psgc_table", lambda *_: TABLE.copy())
    monkeypatch.setattr(
        pipeline._levels, "write_level", lambda gdf, stem, out, stamp: written.append((stem, out, stamp))
    )
    for name in pipeline.LEVELS:

        def level(_df, _release, child, name=name):
            children[name] = child
            return {"": f"{name} frame", **({"complete": f"{name} complete"} if name == "bgysubmuns" else {})}

        monkeypatch.setitem(pipeline.LEVELS, name, level)
    pipeline.run(rebuilding(municities=(1999901000,)), levels=("municities",), out_dir=str(tmp_path))
    assert children["municities"] == "bgysubmuns frame"
    # 2026-3q's manifest says as_of 2026-09-30: the date its zips carry.
    assert written == [("PH_Adm3_MuniCities", str(tmp_path), datetime.date(2026, 9, 30))]
