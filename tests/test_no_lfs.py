#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""The repository needs no git-lfs: no LFS rule, nothing tracked that is too big for git, and every raw source
the release files read listed in data/sources.toml (scripts/sources.py fetches them).

Marked integration: it reads what git tracks, which CI's checkout has without LFS or the sources.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ph_psgc_shape.release import load_release
from ph_psgc_shape.sources import load_sources

pytestmark = pytest.mark.integration

REPO = Path(__file__).parent.parent
GITHUB_FILE_LIMIT = 100 * 1024 * 1024  # GitHub refuses a pushed file over 100 MiB


def tracked() -> list[str]:
    out = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z"], capture_output=True, check=True).stdout
    return [p for p in out.decode().split("\0") if p]


def test_no_file_is_stored_through_git_lfs():
    attributes = REPO / ".gitattributes"
    assert not attributes.exists() or "filter=lfs" not in attributes.read_text()


def test_no_raw_source_or_shapefile_zip_is_tracked():
    sources = load_sources(REPO / "data" / "sources.toml").by_path()
    files = tracked()
    assert not [p for p in files if p in sources], "a raw source is tracked: it belongs in the sources release"
    assert not [p for p in files if p.startswith("dist/") and p.endswith(".shp.zip")]


def test_every_tracked_file_fits_in_plain_git():
    big = [p for p in tracked() if (REPO / p).is_file() and (REPO / p).stat().st_size > GITHUB_FILE_LIMIT]
    assert not big


def test_every_source_a_release_reads_is_listed():
    listed = set(load_sources(REPO / "data" / "sources.toml").by_path())
    for path in sorted((REPO / "releases").glob("*.toml")):
        release = load_release(path, check_paths=False)
        for level, source in release.sources.items():
            assert source.path in listed, f"{path.name}: sources.{level}.path {source.path} isn't in data/sources.toml"
