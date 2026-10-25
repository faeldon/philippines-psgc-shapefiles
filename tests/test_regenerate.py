#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""regenerate: it refuses any out_dir that could write over the repo's dist/, before running anything."""
from __future__ import annotations

import builtins

import pytest

import regenerate


@pytest.fixture
def no_script_import(monkeypatch):
    """Fail the test if regenerate gets as far as importing the pipeline."""
    real_import = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith("ph_psgc_shape"):
            raise AssertionError("regenerate imported the pipeline; it should have refused first")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)


def test_refuses_out_dir_inside_repo(no_script_import, capsys):
    assert regenerate.main([str(regenerate.REPO / "tmp-regenerate")]) == 2
    assert "inside the repo" in capsys.readouterr().err
    assert not (regenerate.REPO / "tmp-regenerate").exists()


def test_refuses_the_repo_itself(no_script_import):
    assert regenerate.main([str(regenerate.REPO)]) == 2


def test_refuses_non_empty_dist(tmp_path, no_script_import, capsys):
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "PH_Adm1_Regions.csv").write_text("x\n")
    assert regenerate.main([str(tmp_path)]) == 2
    assert "already has files" in capsys.readouterr().err
