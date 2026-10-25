#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""psgc_data: manifests are strict, extracts are PSA's cells and the same every run, and check catches drift."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import openpyxl
import pytest

from ph_psgc_shape import psgc_data
from ph_psgc_shape.psgc_data import PsgcDataError

REPO = Path(__file__).parent.parent
COLUMNS = ["10-digit PSGC", "Name", "Correspondence Code", "Geographic Level"]
SOC_HEADER = list(psgc_data.SOC_COLUMNS)


def workbook(path: Path, sheets: dict):
    """Write an xlsx at path with these sheets, each a list of rows."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for row in rows:
            ws.append(row)
    wb.save(path)


def publication(root: Path, pub_id="2099-1q", sections=("January to March 2099",), soc_rows=None):
    """A publication folder under root with its raw files and a manifest naming their hashes."""
    raw = root / "raw" / pub_id
    raw.mkdir(parents=True)
    workbook(
        raw / "datafile.xlsx",
        {
            "PSGC": [
                COLUMNS,
                [1300000000.0, "National Capital Region (NCR)", 130000000.0, "Reg"],
                ["0990100000", "Isabela", None, None],
            ],
            "National Summary": [["CODE", "REGION", "PROV."], ["1300000000", "NCR", 0]],
            "Prov Sum": [["Province"], ["Abra"]],
        },
    )
    if soc_rows is None:
        soc_rows = [
            ["SUMMARY OF CHANGES"],
            ["October to December 2098"],
            SOC_HEADER,
            ["Barangay Old, City of X", "Correction of name", "0101001001", "Olde", "0101001001", "Cert."],
            ["January to March 2099"],
            SOC_HEADER,
            ["Barangay A, City of X", "Merging of barangays", "0101001099", "B", "0101001002", "Ordinance"],
            [None, None, None, "C", "0101001003"],
        ]
    workbook(raw / "soc.xlsx", {"2001-present": soc_rows})
    sha = {name: hashlib.sha256((raw / name).read_bytes()).hexdigest() for name in ("datafile.xlsx", "soc.xlsx")}
    folder = root / pub_id
    folder.mkdir()
    (folder / "manifest.toml").write_text(
        f"""id = "{pub_id}"
as_of = "2099-03-31"
announcement = "https://psa.gov.ph/classification/psgc"

[[files]]
role = "datafile"
name = "datafile.xlsx"
url = "https://psa.gov.ph/system/files/scd/datafile.xlsx"
sha256 = "{sha['datafile.xlsx']}"
sheets = {{ psgc = "PSGC", national_summary = "National Summary", prov_summary = "Prov Sum" }}

[[files]]
role = "summary_of_changes"
name = "soc.xlsx"
url = "https://psa.gov.ph/system/files/scd/soc.xlsx"
sha256 = "{sha['soc.xlsx']}"
sheets = {{ log = "2001-present" }}
sections = [{", ".join(f'"{s}"' for s in sections)}]

[layout]
columns = ["psgc_code", "name", "corr_code", "geo_level"]
"""
    )
    return psgc_data.load_manifest(pub_id, root)


def edited_manifest(root, old, new):
    path = root / "2099-1q" / "manifest.toml"
    text = path.read_text()
    assert old in text, f"{old!r} not in the manifest"
    path.write_text(text.replace(old, new, 1))
    return path


def manifest_fails(root, key):
    with pytest.raises(PsgcDataError) as e:
        psgc_data.load_manifest("2099-1q", root)
    assert "manifest.toml" in str(e.value) and key in str(e.value), str(e.value)


def test_the_committed_manifests_load():
    for pub_id in psgc_data.publications(REPO / "data" / "psgc"):
        assert psgc_data.load_manifest(pub_id, REPO / "data" / "psgc").id == pub_id


def test_extract_writes_psa_cells_as_text(tmp_path):
    manifest = publication(tmp_path)
    psgc_data.extract(manifest)
    assert (manifest.folder / "psgc.csv").read_text().splitlines() == [
        "10-digit PSGC,Name,Correspondence Code,Geographic Level",
        "1300000000,National Capital Region (NCR),130000000,Reg",  # whole floats lose their .0
        "0990100000,Isabela,,",  # a zero-padded text code keeps its zero; empty cells are empty
    ]
    assert (manifest.folder / "national-summary.csv").read_text() == "CODE,REGION,PROV.\n1300000000,NCR,0\n"


def test_extract_keeps_only_the_publications_sections(tmp_path):
    manifest = publication(tmp_path)
    psgc_data.extract(manifest)
    assert (manifest.folder / "summary-of-changes.csv").read_text().splitlines() == [
        "section," + ",".join(SOC_HEADER),
        'January to March 2099,"Barangay A, City of X",Merging of barangays,0101001099,B,0101001002,Ordinance,',
        "January to March 2099,,,,C,0101001003,,",
    ]


def test_extract_is_the_same_every_run(tmp_path):
    manifest = publication(tmp_path)
    psgc_data.extract(manifest)
    first = {p.name: p.read_bytes() for p in manifest.folder.glob("*.csv")}
    psgc_data.extract(manifest)
    assert {p.name: p.read_bytes() for p in manifest.folder.glob("*.csv")} == first


def test_a_raw_file_that_isnt_the_manifests_fails(tmp_path):
    manifest = publication(tmp_path)
    workbook(psgc_data.raw_dir(manifest) / "soc.xlsx", {"2001-present": [["changed"]]})
    with pytest.raises(PsgcDataError, match="soc.xlsx: SHA-256"):
        psgc_data.extract(manifest)


def test_a_section_missing_from_the_log_fails(tmp_path):
    manifest = publication(tmp_path, sections=("April to June 2099",))
    with pytest.raises(PsgcDataError, match="'April to June 2099' not found"):
        psgc_data.extract(manifest)


def test_a_value_past_the_seventh_column_fails(tmp_path):
    rows = [["January to March 2099"], SOC_HEADER, ["Barangay A", "Correction of name", "1", "", "", "", "", "stray"]]
    manifest = publication(tmp_path, soc_rows=rows)
    with pytest.raises(PsgcDataError, match="past column 7"):
        psgc_data.extract(manifest)


def test_check_finds_a_changed_extract_and_skips_publications_without_raw_files(tmp_path):
    manifest = publication(tmp_path)
    psgc_data.extract(manifest)
    assert psgc_data.check(tmp_path) == ([], [])
    (manifest.folder / "psgc.csv").write_text("edited\n")
    shutil.copytree(manifest.folder, tmp_path / "2099-2q")
    edited = (tmp_path / "2099-2q" / "manifest.toml").read_text().replace('id = "2099-1q"', 'id = "2099-2q"')
    (tmp_path / "2099-2q" / "manifest.toml").write_text(edited)
    problems, skipped = psgc_data.check(tmp_path)
    assert problems == ["2099-1q: psgc.csv differs from its raw file datafile.xlsx"] and skipped == ["2099-2q"]


def test_an_unknown_manifest_key_fails(tmp_path):
    publication(tmp_path)
    edited_manifest(tmp_path, 'as_of = "2099-03-31"', 'as_of = "2099-03-31"\nasof = "x"')
    manifest_fails(tmp_path, "asof")


def test_a_manifest_needs_one_file_of_each_role(tmp_path):
    publication(tmp_path)
    edited_manifest(tmp_path, 'role = "summary_of_changes"', 'role = "datafile"')
    manifest_fails(tmp_path, "files")


def test_a_sha256_that_isnt_hex_fails(tmp_path):
    publication(tmp_path)
    path = tmp_path / "2099-1q" / "manifest.toml"
    text = path.read_text()
    start = text.index('sha256 = "') + len('sha256 = "')
    path.write_text(text[:start] + "XYZ" + text[start + 3 :])
    manifest_fails(tmp_path, "files[0].sha256")


def test_an_id_that_isnt_its_folder_fails(tmp_path):
    publication(tmp_path)
    edited_manifest(tmp_path, 'id = "2099-1q"', 'id = "2099-2q"')
    manifest_fails(tmp_path, "id")


@pytest.mark.parametrize(
    "old, new, key",
    [
        ('"corr_code", ', "", "layout.columns"),
        ('"corr_code", ', '"name", ', "layout.columns"),
        ('"geo_level"]', '"geo_level"]\ndrop = ["geo_level"]', "layout.drop"),
        ('"geo_level"]', '"geo_level"]\ndrop = ["_blank"]', "layout.drop"),
    ],
    ids=["required column missing", "column named twice", "required column dropped", "dropped column not named"],
)
def test_a_layout_that_cant_be_read_fails(tmp_path, old, new, key):
    publication(tmp_path)
    edited_manifest(tmp_path, old, new)
    manifest_fails(tmp_path, key)


ADD_ROW = '{ code = 1307400000, name = "NCR, Second District (Not a Province)", geo_level = "Dist" }'


def test_add_rows_are_read(tmp_path):
    publication(tmp_path)
    edited_manifest(tmp_path, '"geo_level"]', f'"geo_level"]\nadd_rows = [{ADD_ROW}]')
    rows = psgc_data.load_manifest("2099-1q", tmp_path).layout.add_rows
    assert [(r.code, r.geo_level) for r in rows] == [(1307400000, "Dist")]


def test_an_added_code_listed_twice_fails(tmp_path):
    publication(tmp_path)
    edited_manifest(tmp_path, '"geo_level"]', f'"geo_level"]\nadd_rows = [{ADD_ROW}, {ADD_ROW}]')
    manifest_fails(tmp_path, "layout.add_rows[1].code")


def test_unknown_key_in_an_added_row_fails(tmp_path):
    publication(tmp_path)
    edited_manifest(tmp_path, '"geo_level"]', f'"geo_level"]\nadd_rows = [{ADD_ROW[:-1]}, level = 1 }}]')
    manifest_fails(tmp_path, "layout.add_rows[0].level")
