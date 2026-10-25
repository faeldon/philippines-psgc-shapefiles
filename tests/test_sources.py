#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""sources: the manifest is strict, fetch puts only matching files in place, and upload sends nothing unasked."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import sources
from ph_psgc_shape.sources import SourceFile, Sources, SourcesError, load_sources

CONTENT = b"a shapefile's bytes"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


ONE = SourceFile("data/2023/Regions/r.shp", "2023__Regions__r.shp", sha(CONTENT), len(CONTENT), "OCHA")
MANIFEST = Sources("owner/repo", "sources", (ONE,))


def downloads(monkeypatch, data=CONTENT):
    """Stub gh: a release download writes data as the asset; return the list of gh calls made."""
    calls = []

    def gh(*args):
        calls.append(args)
        if args[:2] == ("release", "download"):
            Path(args[args.index("-D") + 1], args[args.index("-p") + 1]).write_bytes(data)
        return None

    monkeypatch.setattr(sources, "gh", gh)
    return calls


def test_a_manifest_is_read(tmp_path):
    (tmp_path / "s.toml").write_text(
        'repo = "o/r"\ntag = "sources"\n\n[[file]]\npath = "data/x"\nasset = "x"\n'
        f'sha256 = "{sha(CONTENT)}"\nsize = {len(CONTENT)}\norigin = "OCHA"\n'
    )
    assert load_sources(tmp_path / "s.toml").files[0].asset == "x"


@pytest.mark.parametrize(
    ("change", "key"),
    [
        (lambda t: t.replace('origin = "OCHA"', 'origin = "OCHA"\nextra = 1'), "file[0].extra"),
        (lambda t: t.replace(sha(CONTENT), "abc"), "file[0].sha256"),
        (lambda t: t + t[t.index("[[file]]") :], "file[1].path"),
    ],
)
def test_a_manifest_that_cant_be_used_fails(tmp_path, change, key):
    text = (
        'repo = "o/r"\ntag = "sources"\n\n[[file]]\npath = "data/x"\nasset = "x"\n'
        f'sha256 = "{sha(CONTENT)}"\nsize = {len(CONTENT)}\norigin = "OCHA"\n'
    )
    (tmp_path / "s.toml").write_text(change(text))
    with pytest.raises(SourcesError, match=key.replace("[", r"\[").replace("]", r"\]")):
        load_sources(tmp_path / "s.toml")


def test_fetch_downloads_a_missing_file_and_checks_it(tmp_path, monkeypatch):
    calls = downloads(monkeypatch)
    assert not sources.fetch(MANIFEST, tmp_path, None)
    assert (tmp_path / ONE.path).read_bytes() == CONTENT
    assert calls[0][:3] == ("release", "download", "sources")


def test_fetch_skips_a_file_already_in_place(tmp_path, monkeypatch):
    (tmp_path / ONE.path).parent.mkdir(parents=True)
    (tmp_path / ONE.path).write_bytes(CONTENT)
    assert not downloads(monkeypatch) and not sources.fetch(MANIFEST, tmp_path, None)


def test_fetch_links_from_another_checkout_before_downloading(tmp_path, monkeypatch):
    main = tmp_path / "main"
    (main / ONE.path).parent.mkdir(parents=True)
    (main / ONE.path).write_bytes(CONTENT)
    calls = downloads(monkeypatch)
    assert not sources.fetch(MANIFEST, tmp_path / "wt", main)
    assert not calls
    assert (tmp_path / "wt" / ONE.path).stat().st_ino == (main / ONE.path).stat().st_ino


def test_a_download_that_doesnt_match_is_not_kept(tmp_path, monkeypatch):
    downloads(monkeypatch, data=b"something else")
    problems = sources.fetch(MANIFEST, tmp_path, None)
    assert problems and "doesn't match its SHA-256" in problems[0]
    assert not (tmp_path / ONE.path).exists()
    assert list((tmp_path / ONE.path).parent.iterdir()) == []


def test_check_reports_missing_and_changed_files(tmp_path):
    assert "missing" in sources.check(MANIFEST, tmp_path)[0]
    (tmp_path / ONE.path).parent.mkdir(parents=True)
    (tmp_path / ONE.path).write_bytes(b"edited")
    assert "SHA-256 is" in sources.check(MANIFEST, tmp_path)[0]


def test_upload_without_yes_sends_nothing(tmp_path, monkeypatch, capsys):
    (tmp_path / ONE.path).parent.mkdir(parents=True)
    (tmp_path / ONE.path).write_bytes(CONTENT)
    calls = downloads(monkeypatch)
    assert sources.upload(MANIFEST, tmp_path, "abc123", yes=False) == 3
    assert not calls
    assert "nothing sent" in capsys.readouterr().out


def test_the_asset_name_is_the_path_under_data():
    assert sources.asset_name("data/edit/20240210/ph_adm4_20240210.shp") == "edit__20240210__ph_adm4_20240210.shp"
