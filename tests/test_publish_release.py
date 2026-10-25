#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""publish_release: prepare refuses a build it can't vouch for, and upload sends exactly what was prepared."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import make_dist

import check_dist
import publish_release as pr
from test_check_dist import PSGC

RELEASE_2023 = Path(__file__).parent.parent / "releases" / "2023-4q.toml"

CHANGELOG = """# Changelog

| PSGC update | Released | Status |
| :---------- | :------- | -----: |
| [Third Quarter 2026 PSGC Updates](https://psa.gov.ph/classification/psgc/node/1684084314) | October 12, 2026 | ✅ |
| [Second Quarter 2026 PSGC Updates](https://psa.gov.ph/classification/psgc/node/1684083815) | July 13, 2026 | ✅ [^1] |
| [No Change in the Fourth Quarter 2023 PSGC](https://psa.gov.ph/classification/psgc/node/1684061953) | January 23, 2024 | ✅ (NC) |

## Data corrections

**October 2026: one layer per shapefile zip.** Each zip holds one layer.

**March 2022: an old correction.** Before.
"""


class Gh:
    """A stand-in for the gh CLI: records calls, knows which releases exist and what assets they hold."""

    def __init__(self, releases=None):
        self.calls, self.releases = [], dict(releases or {})

    def __call__(self, *args):
        self.calls.append(args)
        out = ""
        if args[:2] == ("release", "list"):
            out = json.dumps([{"tagName": t, "isLatest": i == 0} for i, t in enumerate(self.releases)])
        elif args[:2] == ("release", "create"):
            self.releases[args[2]] = set()
        elif args[:2] == ("release", "upload"):
            self.releases[args[2]].add(Path(args[-1]).name)
        elif args[:2] == ("release", "view"):
            if args[2] not in self.releases:
                raise pr.PublishError(f"release not found: {args[2]}")
            out = "\n".join(sorted(self.releases[args[2]])) if "assets" in args else "{}"
        return subprocess.CompletedProcess(args, 0, out, "")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A repo stand-in: a fixture dist/ committed, a CHANGELOG, no releases yet; the current release is 2023-4q."""
    root = tmp_path / "repo"
    make_dist(root / "dist")
    for zip_path in (root / "dist").glob("*.shp.zip"):
        zip_path.unlink()  # the committed dist/ is CSV-only
    (root / "CHANGELOG.md").write_text(CHANGELOG)
    monkeypatch.setattr(pr, "REPO", root)
    monkeypatch.setattr(pr, "CURRENT", RELEASE_2023)
    monkeypatch.setattr(check_dist, "psgc_codes_by_level", lambda _release: PSGC)
    gh = Gh()
    monkeypatch.setattr(pr, "gh", gh)
    monkeypatch.setattr(pr.subprocess, "run", lambda args, **_: subprocess.CompletedProcess(args, 1, "", ""))
    return root, gh


def build(tmp_path):
    """A regenerate.py-style build: <out>/dist with the fixture's zips and CSVs."""
    out = tmp_path / "build"
    make_dist(out / "dist")
    return out


def test_prepare_stages_every_asset_and_its_sums(repo, tmp_path):
    root, _ = repo
    stage = pr.prepare(build(tmp_path), RELEASE_2023, None, latest=True, staging=root / "release-staging")
    names = sorted(p.name for p in stage.iterdir())
    assert {"SHA256SUMS", "notes.md", "meta.json"} <= set(names)
    assert len([n for n in names if n.startswith("PH_Adm")]) == 10  # five zips and five CSVs (no complete)
    for line in (stage / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ")
        assert pr.sha256_of(stage / name) == digest


def test_prepare_refuses_a_build_that_fails_its_check(repo, tmp_path):
    out = build(tmp_path)
    (out / "dist" / "PH_Adm1_Regions.shp.zip").unlink()
    with pytest.raises(pr.PublishError, match="fails check_dist"):
        pr.prepare(out, RELEASE_2023, None, latest=True, staging=repo[0] / "release-staging")


def test_prepare_refuses_csvs_that_differ_from_the_committed_dist(repo, tmp_path):
    root, _ = repo
    path = root / "dist" / "PH_Adm2_ProvDists.csv"
    path.write_text(path.read_text().replace("Ilocos", "ILOCOS"))
    with pytest.raises(pr.PublishError, match="PH_Adm2_ProvDists.csv differs"):
        pr.prepare(build(tmp_path), RELEASE_2023, None, latest=True, staging=root / "release-staging")


def staged(repo, tmp_path):
    root, _ = repo
    pr.prepare(build(tmp_path), RELEASE_2023, None, latest=True, staging=root / "release-staging")
    return root / "release-staging"


def test_upload_creates_the_release_and_sends_every_asset(repo, tmp_path):
    staging = staged(repo, tmp_path)
    pr.upload("psgc-2023-4q", "2023-4q", "abc123", staging=staging)
    gh = repo[1]
    create = next(c for c in gh.calls if c[:2] == ("release", "create"))
    assert create[2] == "psgc-2023-4q" and "PSGC 4Q 2023 (psgc-2023-4q)" in create
    assert "--target" in create and "--latest=true" in create
    assert len(gh.releases["psgc-2023-4q"]) == 11  # ten assets and SHA256SUMS


def test_upload_adds_only_what_an_existing_release_lacks(repo, tmp_path):
    staging = staged(repo, tmp_path)
    pr.upload("psgc-2023-4q", "2023-4q", "abc123", staging=staging)
    gh = repo[1]
    before = len(gh.calls)
    pr.upload("psgc-2023-4q", "2023-4q", "abc123", staging=staging)
    assert not [c for c in gh.calls[before:] if c[:2] in {("release", "upload"), ("release", "create")}]


def test_upload_refuses_a_file_changed_since_prepare(repo, tmp_path):
    staging = staged(repo, tmp_path)
    target = staging / "2023-4q" / "PH_Adm4_BgySubMuns.csv"
    content = target.read_text()
    target.unlink()  # a hard link: replace it rather than edit the build's file through it
    target.write_text(content + "\n")
    with pytest.raises(pr.PublishError, match="PH_Adm4_BgySubMuns.csv changed since prepare"):
        pr.upload("psgc-2023-4q", "2023-4q", "abc123", staging=staging)


def test_upload_refuses_a_tag_the_remote_lacks_without_a_target(repo, tmp_path):
    staging = staged(repo, tmp_path)
    with pytest.raises(pr.PublishError, match="no tag v0.2.0 on the remote"):
        pr.upload("v0.2.0", "2023-4q", None, staging=staging)


def test_a_complete_adm4_is_published_as_its_own_assets(tmp_path):
    dist = make_dist(tmp_path / "dist")
    (dist / "complete").mkdir()
    shutil.copy2(dist / "PH_Adm4_BgySubMuns.csv", dist / "complete" / "PH_Adm4_BgySubMuns.csv")
    assets = pr.assets_of(dist)
    assert assets["PH_Adm4_BgySubMuns_complete.csv"] == dist / "complete" / "PH_Adm4_BgySubMuns.csv"
    laid = pr.layout(tmp_path / "dist" / "complete", tmp_path / "laid")
    assert (laid / "PH_Adm4_BgySubMuns.csv").exists()


def test_the_notes_hold_the_publications_since_the_previous_release_and_name_the_publication():
    # Since 2026-1q (as of March 31): 2Q and 3Q 2026, matched by their manifests' PSA announcement.
    text = pr.notes(CHANGELOG, "2026-3q", pr.as_of("2026-1q"))
    assert "Third Quarter 2026" in text and "Second Quarter 2026" in text
    assert "Fourth Quarter 2023" not in text
    assert "[^1]" not in text  # the footnote it points to is the CHANGELOG's
    assert "one layer per shapefile zip" in text and "an old correction" not in text
    assert text.rstrip().endswith("<!-- psgc-publication: 2026-3q -->")


def test_the_first_publication_s_notes_hold_its_own_announcement_only():
    text = pr.notes(CHANGELOG, "2023-4q", None)
    assert "Fourth Quarter 2023" in text and "Third Quarter 2026" not in text


def test_a_publication_id_reads_as_people_say_it():
    assert pr.label("2026-3q") == "3Q 2026" and pr.label("2024-04") == "April 2024"
