#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""The committed PSGC publications under data/psgc/: each reads through its layout, and none needs its raw files.

Marked integration because it reads the repo's data. The raw files are gitignored, so CI has none: the
checks that need them, or git history, skip without them.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from ph_psgc_shape import psgc, psgc_data
from ph_psgc_shape.release import load_release

pytestmark = pytest.mark.integration

REPO = Path(__file__).parent.parent
DISTRICT_CODES = [1303900000, 1307400000, 1307500000, 1307600000]


@pytest.fixture(autouse=True)
def in_repo():
    cwd = os.getcwd()
    os.chdir(REPO)
    yield
    os.chdir(cwd)


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def test_every_publication_has_a_folder():
    assert psgc_data.publications(REPO / "data" / "psgc") == sorted(
        ["2023-4q", "2024-1q", "2024-04", "2024-2q", "2024-3q", "2024-4q", "2025-1q"]
        + ["2025-2q", "2025-07", "2025-3q", "2025-4q", "2026-1q", "2026-2q", "2026-3q"]
    )


@pytest.mark.parametrize("pub_id", psgc_data.publications(REPO / "data" / "psgc"))
def test_each_publication_reads_with_its_codes_names_and_levels(pub_id):
    df = psgc.load_table(psgc_data.load_manifest(pub_id))
    assert df["psgc_code"].is_unique
    ncr = df[df["psgc_code"] == 1300000000]
    assert ncr[["name", "geo_level"]].values.tolist() == [["National Capital Region (NCR)", "Reg"]]
    assert ncr["corr_code"].tolist() == [130000000.0]
    assert sorted(df.loc[df["geo_level"] == "Dist", "psgc_code"]) == DISTRICT_CODES


def test_4q_2023_keeps_every_row():
    # Every row has a name, and the four nameless-code rows are the districts district_codes fills.
    release = load_release(REPO / "releases" / "2023-4q.toml", check_sources=False)
    assert len(psgc.load_psgc_table(release)) == 43762


def test_no_excel_file_is_tracked_under_data_psgc():
    assert [p for p in git("ls-files", "data/psgc").splitlines() if p.endswith(".xlsx")] == []


def test_raw_downloads_are_ignored():
    assert git("check-ignore", "data/psgc/raw/2024-1q/x.xlsx").strip() == "data/psgc/raw/2024-1q/x.xlsx"


@pytest.mark.parametrize("pub_id", psgc_data.publications(REPO / "data" / "psgc"))
def test_the_manifest_hash_is_the_datafile_git_once_held(pub_id):
    """R7: each datafile left git unchanged. CI's shallow checkout has no history, so this skips there."""
    path = f"data/psgc/{psgc_data.load_manifest(pub_id).file('datafile').name}"
    last = git("rev-list", "-1", "HEAD", "--", path).strip()
    if not last:
        pytest.skip("no history of the committed datafile here (shallow clone)")
    # The last commit to touch it either holds it (the removal isn't committed yet) or removed it.
    held = subprocess.run(["git", "cat-file", "-e", f"{last}:{path}"], cwd=REPO, check=False).returncode == 0
    blob = subprocess.run(
        ["git", "show", f"{last if held else last + '^'}:{path}"], cwd=REPO, capture_output=True, check=True
    ).stdout
    assert hashlib.sha256(blob).hexdigest() == psgc_data.load_manifest(pub_id).file("datafile").sha256


def test_the_extracts_match_their_raw_files():
    problems, skipped = psgc_data.check()
    if len(skipped) == len(psgc_data.publications()):
        pytest.skip("no raw files here (data/psgc/raw/ is gitignored)")
    assert not problems, "\n".join(problems)
