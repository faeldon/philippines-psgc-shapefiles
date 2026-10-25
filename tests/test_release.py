#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""load_release: a release file that can't be used fails loudly, naming the file and the key."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ph_psgc_shape.release import ReleaseError, load_release

REPO = Path(__file__).parent.parent
RELEASE = REPO / "releases" / "2023-4q.toml"
PACKAGE = REPO / "src" / "ph_psgc_shape"

# Integer literals the package may hold that look like codes but aren't: corr_code's format conversion.
NOT_CODES = {100_000_000}


def edited(tmp_path, old, new, count=1):
    """Write a copy of the 2023-4q release with old replaced by new; return its path."""
    text = RELEASE.read_text()
    assert old in text, f"{old!r} not in the release file"
    path = tmp_path / "edited.toml"
    path.write_text(text.replace(old, new, count))
    return path


def source_tree(root, release):
    """Create an empty file at each of the release's paths under root."""
    publication = [f"data/psgc/{release.psgc.publication}/{name}" for name in ("manifest.toml", "psgc.csv")]
    for rel in publication + [s.path for s in release.sources.values()]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).touch()


def fails(path, key, **kwargs):
    """Assert loading path raises a ReleaseError that names the file and the key."""
    with pytest.raises(ReleaseError) as e:
        load_release(path, **kwargs)
    assert str(path) in str(e.value) and key in str(e.value), str(e.value)


def test_the_2023_4q_release_loads():
    release = load_release(RELEASE, check_paths=False)
    assert release.id == "2023-4q"
    assert set(release.sources) == {"country", "region", "provdists", "municities", "bgysubmuns"}
    assert release.municities.overrides[0].old == 305401000


def test_unknown_key_fails(tmp_path):
    path = edited(tmp_path, 'publication = "2023-4q"', 'publication = "2023-4q"\nfile = "x.xlsx"')
    fails(path, "psgc.file", check_paths=False)


def test_unknown_key_in_an_override_fails(tmp_path):
    path = edited(tmp_path, "{ old = 305401000,", "{ olde = 1, old = 305401000,")
    fails(path, "municities.overrides[0].olde", check_paths=False)


def test_missing_key_fails(tmp_path):
    fails(edited(tmp_path, 'publication = "2023-4q"\n', ""), "psgc.publication", check_paths=False)


def test_a_publication_that_isnt_there_fails(tmp_path):
    source_tree(tmp_path, load_release(RELEASE, check_paths=False))
    path = edited(tmp_path, 'publication = "2023-4q"', 'publication = "2023-4Q"')
    fails(path, "psgc.publication", root=tmp_path)


def test_code_that_isnt_an_int_fails(tmp_path):
    path = edited(tmp_path, "{ old = 305401000,", '{ old = "305401000",')
    fails(path, "municities.overrides[0].old", check_paths=False)


def test_bool_is_not_a_code(tmp_path):
    fails(edited(tmp_path, "reserved_min = 900", "reserved_min = true"), "bgysubmuns.reserved_min", check_paths=False)


def test_duplicate_municities_old_code_fails(tmp_path):
    line = '  { old = 305401000, new = 330100000, note = "City of Angeles" },\n'
    fails(edited(tmp_path, line, line + line), "municities.overrides[1].old", check_paths=False)


def test_bgysubmuns_may_repeat_an_override():
    # Kulimpang and Mataya are each listed twice; applying one again changes nothing.
    olds = [o.old for o in load_release(RELEASE, check_paths=False).bgysubmuns.overrides]
    assert olds.count(1908702012) == 2


def test_missing_source_path_fails(tmp_path):
    release = load_release(RELEASE, check_paths=False)
    source_tree(tmp_path, release)
    (tmp_path / release.sources["municities"].path).unlink()
    fails(RELEASE, "sources.municities.path", root=tmp_path)


def test_existing_paths_pass(tmp_path):
    release = load_release(RELEASE, check_paths=False)
    source_tree(tmp_path, release)
    assert load_release(RELEASE, root=tmp_path) == release


def test_path_case_mismatch_fails(tmp_path):
    # The folder on disk is Provdists; macOS would open ProvDists, Linux would not.
    source_tree(tmp_path, load_release(RELEASE, check_paths=False))
    path = edited(tmp_path, "data/2023/Provdists/", "data/2023/ProvDists/")
    fails(path, "sources.provdists.path", root=tmp_path)


def test_unreadable_toml_fails(tmp_path):
    path = tmp_path / "bad.toml"
    path.write_text("id = \n")
    fails(path, "", check_paths=False)


def test_no_psgc_code_literals_in_package():
    """Every PSGC code lives in a release file; a 9- or 10-digit literal in the code is one leaking back."""
    found = []
    for module in sorted(PACKAGE.glob("*.py")):
        for node in ast.walk(ast.parse(module.read_text())):
            value = getattr(node, "value", None) if isinstance(node, ast.Constant) else None
            if isinstance(value, int) and value >= 100_000_000 and value not in NOT_CODES:
                found.append(f"{module.name}:{node.lineno}: {value}")
    assert not found


def appended(tmp_path, text):
    """Write a copy of the 2023-4q release with text added at the end (new top-level tables)."""
    path = tmp_path / "appended.toml"
    path.write_text(RELEASE.read_text() + "\n" + text)
    return path


def recode(*prefixes):
    rows = ", ".join(f'{{ from = "{a}", to = "{b}" }}' for a, b in prefixes)
    return f"[recode]\nprefixes = [{rows}]\n"


def test_a_recode_is_read(tmp_path):
    release = load_release(appended(tmp_path, recode(("07061", "18061"))), check_paths=False)
    assert [(r.from_prefix, r.to_prefix) for r in release.recodes] == [("07061", "18061")]


def test_a_recode_prefix_that_isnt_five_digits_fails(tmp_path):
    fails(appended(tmp_path, recode(("0706", "18061"))), "recode.prefixes[0].from", check_paths=False)


def test_a_repeated_recode_prefix_fails(tmp_path):
    path = appended(tmp_path, recode(("07061", "18061"), ("07061", "18062")))
    fails(path, "recode.prefixes[1].from", check_paths=False)


def test_a_recode_onto_a_recoded_prefix_fails(tmp_path):
    fails(appended(tmp_path, recode(("07061", "18061"), ("18061", "18062"))), "recode.prefixes", check_paths=False)


def test_an_override_under_a_recoded_prefix_fails(tmp_path):
    # Bacolod's 2023 override names 604501000, which a 06045 recode moves before overrides run.
    fails(appended(tmp_path, recode(("06045", "18045"))), "municities.overrides", check_paths=False)


def test_name_corrections_are_read_and_a_repeated_code_fails(tmp_path):
    names = 'names = [{ code = 431200000, name = "City of Lucena", note = "footnote typed into the name" }]'
    path = edited(tmp_path, 'publication = "2023-4q"', f'publication = "2023-4q"\n{names}')
    assert load_release(path, check_paths=False).psgc.names[0].name == "City of Lucena"
    twice = names.replace("}]", '}, { code = 431200000, name = "Lucena" }]')
    path = edited(tmp_path, 'publication = "2023-4q"', f'publication = "2023-4q"\n{twice}')
    fails(path, "psgc.names[1].code", check_paths=False)


def test_rebuilds_merges_shapeless_and_edits_are_read(tmp_path):
    text = RELEASE.read_text()
    text = text.replace("[municities]\n", "[municities]\nrebuild = [1999901000]\n", 1)
    text = text.replace(
        "reserved_min = 900",
        "reserved_min = 900\n"
        'merges = [{ into = 401007019, from = [401007019, 401007038], note = "GR 234228" }]\n'
        'shapeless = [{ code = 1903617146, note = "Angoyao: no published boundary" }]',
        1,
    )
    text += '\n[region]\nrebuild = [1800000000]\n\n[edits]\nplotted = "data/edit/x/plotted.geojson"\n'
    path = tmp_path / "keys.toml"
    path.write_text(text)
    release = load_release(path, check_paths=False)
    assert release.region.rebuild == (1800000000,) and release.municities.rebuild == (1999901000,)
    assert release.bgysubmuns.merges[0].from_codes == (401007019, 401007038)
    assert release.bgysubmuns.shapeless == {1903617146: "Angoyao: no published boundary"}
    assert release.edits.plotted == "data/edit/x/plotted.geojson" and release.edits.approximated is None


def without_country_source(root):
    """A source tree for the 2023-4q release with its country shapefile missing; returns the missing path."""
    release = load_release(RELEASE, check_paths=False)
    source_tree(root, release)
    missing = release.sources["country"].path
    (root / missing).unlink()
    return missing


def test_a_missing_raw_source_says_to_fetch_it(tmp_path):
    missing = without_country_source(tmp_path)
    (tmp_path / "data" / "sources.toml").write_text(f'[[file]]\npath = "{missing}"\n')
    with pytest.raises(ReleaseError, match=r"sources\.country\.path.*run `python scripts/sources\.py fetch`"):
        load_release(RELEASE, root=tmp_path)


def test_a_missing_path_no_manifest_lists_is_only_not_found(tmp_path):
    without_country_source(tmp_path)
    with pytest.raises(ReleaseError, match="not found") as e:
        load_release(RELEASE, root=tmp_path)
    assert "sources.py" not in str(e.value)


def test_check_sources_false_skips_only_the_sources(tmp_path):
    without_country_source(tmp_path)
    assert load_release(RELEASE, root=tmp_path, check_sources=False).id == "2023-4q"
    (tmp_path / "data" / "psgc" / "2023-4q" / "psgc.csv").unlink()
    fails(RELEASE, "psgc.publication", root=tmp_path, check_sources=False)


def test_an_edit_file_that_isnt_there_fails(tmp_path):
    source_tree(tmp_path, load_release(RELEASE, check_paths=False))
    fails(appended(tmp_path, '[edits]\nplotted = "data/edit/x/plotted.geojson"\n'), "edits.plotted", root=tmp_path)


def test_the_2023_4q_release_has_no_edits():
    release = load_release(RELEASE, check_paths=False)
    assert release.recodes == () and release.region.rebuild == () and release.edits.plotted is None
    assert release.bgysubmuns.merges == () and release.bgysubmuns.shapeless == {}
