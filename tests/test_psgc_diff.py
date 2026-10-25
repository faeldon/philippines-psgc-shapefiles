#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""psgc_diff: every claim gets a status by its rule, every uncovered difference is reported, and reruns match."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from ph_psgc_shape import psgc_diff

HEADER = ["10-digit PSGC", "Name", "Correspondence Code", "Geographic Level"]
SOC = ["section", "Region/Province/Municipal/Bgy. Name", "Unit Type", "New Code", "Mother Unit/Old Name", "Old Code"]
SOC += ["Description/Legal basis", "Remarks"]
SECTION = "January to March 2099"


def write_csv(path: Path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(rows)


def publication(root: Path, pub_id: str, table, claims=(), summary=None):
    """A committed publication folder: a minimal manifest, psgc.csv from table, and the claims given."""
    folder = root / pub_id
    folder.mkdir(parents=True)
    zeros = "0" * 64
    (folder / "manifest.toml").write_text(
        f"""id = "{pub_id}"
as_of = "2099-03-31"
announcement = "https://psa.gov.ph/classification/psgc"

[[files]]
role = "datafile"
name = "d.xlsx"
url = "https://psa.gov.ph/d.xlsx"
sha256 = "{zeros}"
sheets = {{ psgc = "PSGC", national_summary = "National Summary", prov_summary = "Prov Sum" }}

[[files]]
role = "summary_of_changes"
name = "s.xlsx"
url = "https://psa.gov.ph/s.xlsx"
sha256 = "{zeros}"
sheets = {{ log = "2001-present" }}
sections = ["{SECTION}"]

[layout]
columns = ["psgc_code", "name", "corr_code", "geo_level"]
"""
    )
    write_csv(folder / "psgc.csv", [HEADER] + [list(r) for r in table])
    write_csv(folder / "summary-of-changes.csv", [SOC] + [[SECTION, *c, "", ""][: len(SOC)] for c in claims])
    write_csv(folder / "national-summary.csv", summary or [["CODE", "REGION", "PROV.", "CITIES", "MUN.", "BGY."]])
    write_csv(folder / "prov-summary.csv", [["Province"]])
    return folder


OLD = [
    ("0101000000", "Region I", "", "Reg"),
    ("0101001000", "Adams", "", "Mun"),
    ("0101001001", "Olde", "", "Bgy"),
    ("0101001002", "B", "", "Bgy"),
    ("0101001003", "C", "", "Bgy"),
    ("0101001004", "Moved", "", "Bgy"),
    ("0101001005", "Brooke'S", "", "Bgy"),
]


def run(tmp_path, new_table, claims, **kwargs):
    """compare OLD with new_table and these claims: (claims, unexplained, counts, the Comparison)."""
    publication(tmp_path, "2099-0q", OLD)
    publication(tmp_path, "2099-1q", new_table, claims, **kwargs)
    comparison = psgc_diff.compare("2099-0q", "2099-1q", tmp_path)
    return comparison.claims, comparison.unexplained, comparison.counts, comparison


def statuses(findings):
    return [(f.code, f.status) for f in findings]


def test_continuation_rows_fold_into_the_claim_and_types_carry_down(tmp_path):
    folder = publication(
        tmp_path,
        "2099-1q",
        OLD,
        [
            ["Barangay A, X", "Merging of barangays", "0101001099", "B", "0101001002"],
            ["", "", "", "C", "0101001003"],
            ["Barangay Q, X", "Renaming of barangays", "0101001001", "Olde", "0101001001"],
            ["Barangay R, X", "", "0101001005", "Brooke'S", "0101001005"],
        ],
    )
    claims = psgc_diff.read_claims(psgc_diff.load_manifest("2099-1q", tmp_path))
    assert [(c.name, c.kind) for c in claims] == [
        ("Barangay A, X", "merge"),
        ("Barangay Q, X", "rename"),
        ("Barangay R, X", "rename"),
    ]
    assert claims[0].old_codes == ["0101001002"] and claims[0].parts == [("C", "0101001003")]
    assert folder.exists()


def test_a_name_correction_that_the_data_shows_is_consistent(tmp_path):
    new = [r if r[0] != "0101001001" else ("0101001001", "Olden", "", "Bgy") for r in OLD]
    claims, unexplained, _, _ = run(
        tmp_path, new, [["Barangay Olden, X", "Correction of name", "0101001001", "Olde", "0101001001"]]
    )
    assert statuses(claims) == [("0101001001", "consistent")] and unexplained == []


def test_a_name_correction_the_data_spells_differently_is_inconsistent(tmp_path):
    new = [r if r[0] != "0101001001" else ("0101001001", "Oldest", "", "Bgy") for r in OLD]
    claims, unexplained, _, _ = run(
        tmp_path, new, [["Barangay Olden, X", "Correction of name", "0101001001", "Olde", "0101001001"]]
    )
    assert statuses(claims) == [("0101001001", "inconsistent")] and "'Oldest'" in claims[0].detail
    assert unexplained == []  # the claim covers the code, even though it disagrees with it


def test_a_difference_only_in_punctuation_is_consistent_spelling_differs(tmp_path):
    new = [r if r[0] != "0101001005" else ("0101001005", "Brooke's", "", "Bgy") for r in OLD]
    claims, _, _, _ = run(
        tmp_path, new, [["Barangay BROOKE'S, X", "Correction of name", "0101001005", "Brooke'S", "0101001005"]]
    )
    assert statuses(claims) == [("0101001005", "consistent (spelling differs)")]


def test_a_name_that_keeps_its_unit_word_is_consistent(tmp_path):
    new = OLD + [("0101001010", "Barangay 176-A", "", "Bgy")]
    claims, _, _, _ = run(tmp_path, new, [["Barangay 176-A, X", "Newly created barangay", "0101001010", "", ""]])
    assert statuses(claims) == [("0101001010", "consistent")]


def test_a_claimed_code_missing_from_the_data_is_not_found(tmp_path):
    claims, _, _, _ = run(tmp_path, OLD, [["Barangay New, X", "Newly created barangay", "0101001077", "", ""]])
    assert statuses(claims) == [("0101001077", "not found")]


def test_a_creation_of_a_code_that_already_existed_at_that_level_is_inconsistent(tmp_path):
    claims, _, _, _ = run(tmp_path, OLD, [["Barangay B, X", "Newly created barangay", "0101001002", "", ""]])
    assert statuses(claims) == [("0101001002", "inconsistent")]


def test_a_transfer_to_a_new_code_needs_the_old_code_gone(tmp_path):
    moved = [r for r in OLD if r[0] != "0101001004"] + [("0102001004", "Moved", "", "Bgy")]
    kept = OLD + [("0102001004", "Moved", "", "Bgy")]
    claim = [["Barangay Moved, Y", "Transfer of barangay", "0102001004", "Moved, X", "0101001004"]]
    assert statuses(run(tmp_path / "a", moved, claim)[0]) == [("0102001004", "consistent")]
    claims = run(tmp_path / "b", kept, claim)[0]
    assert statuses(claims) == [("0102001004", "inconsistent")] and "still" in claims[0].detail


def test_a_merge_needs_every_merged_code_gone(tmp_path):
    merged = [r for r in OLD if r[0] not in ("0101001002", "0101001003")] + [("0101001099", "A", "", "Bgy")]
    half = [r for r in OLD if r[0] != "0101001002"] + [("0101001099", "A", "", "Bgy")]
    claim = [
        ["Barangay A, X", "Merging of barangays", "0101001099", "B", "0101001002"],
        ["", "", "", "C", "0101001003"],
    ]
    assert statuses(run(tmp_path / "a", merged, claim)[0]) == [("0101001099", "consistent")]
    assert statuses(run(tmp_path / "b", half, claim)[0]) == [("0101001099", "inconsistent")]


def test_a_reclassification_needs_the_level_to_change(tmp_path):
    city = [r if r[0] != "0101001000" else ("0101001000", "City of Adams", "", "City") for r in OLD]
    claim = [["City of Adams, X", "New City", "0101001000", "Municipality of Adams", "0101001000"]]
    assert statuses(run(tmp_path / "a", city, claim)[0]) == [("0101001000", "consistent")]
    assert statuses(run(tmp_path / "b", OLD, claim)[0]) == [("0101001000", "inconsistent")]


def test_a_type_with_no_rule_is_unchecked_not_dropped(tmp_path):
    claims, _, _, _ = run(tmp_path, OLD, [["Something, X", "Annexation", "0101001001", "", ""]])
    assert statuses(claims) == [("0101001001", "unchecked")]


def test_a_difference_no_claim_covers_is_unexplained(tmp_path):
    new = [r if r[0] != "0101001005" else ("0101001005", "Brooke's", "", "Bgy") for r in OLD] + [
        ("0101001006", "D", "", "Bgy")
    ]
    _, unexplained, _, _ = run(tmp_path, new, [])
    assert [(d.kind, d.code, d.detail) for d in unexplained] == [
        ("changed", "0101001005", "renamed"),
        ("added", "0101001006", ""),
    ]


def test_a_code_listed_twice_is_reported_not_dropped(tmp_path):
    new = OLD + [("0101001004", "Moved Twin", "", "Bgy")]
    comparison = run(tmp_path, new, [])[3]
    assert [(d.section, d.code, d.name_new, d.status) for d in comparison.duplicates] == [
        ("2099-1q", "0101001004", "Moved; Moved Twin", "inconsistent")
    ]
    report = psgc_diff.report(comparison)
    assert "## Codes listed more than once (1)" in report and "Moved Twin" in report


def test_a_summary_count_that_disagrees_with_the_sheet_is_listed(tmp_path):
    summary = [["CODE", "REGION", "PROV.", "CITIES", "MUN.", "BGY."], ["0100000000", "Region I", "-", "0", "1", "9"]]
    _, _, counts, _ = run(tmp_path, OLD, [], summary=summary)
    assert [(c.section, c.detail) for c in counts if c.section == "2099-1q"] == [
        ("2099-1q", "BGY: the summary says 9, the PSGC sheet has 5 Bgy")
    ]


def test_a_summary_with_no_region_rows_is_unchecked_not_passed(tmp_path):
    _, _, counts, _ = run(tmp_path, OLD, [])
    assert {(c.section, c.status) for c in counts} == {("2099-0q", "unchecked"), ("2099-1q", "unchecked")}


def test_the_diff_writes_two_files_into_the_new_folder_the_same_every_run(tmp_path):
    publication(tmp_path, "2099-0q", OLD)
    folder = publication(
        tmp_path, "2099-1q", OLD, [["Barangay Olde, X", "Correction of name", "0101001001", "Olde", "0101001001"]]
    )
    before = set(tmp_path.rglob("*"))
    written = psgc_diff.diff("2099-0q", "2099-1q", tmp_path)
    assert sorted(p.name for p in written) == ["diff-from-2099-0q.csv", "diff-from-2099-0q.md"]
    assert set(tmp_path.rglob("*")) - before == {folder / "diff-from-2099-0q.csv", folder / "diff-from-2099-0q.md"}
    first = {p: p.read_bytes() for p in written}
    psgc_diff.diff("2099-0q", "2099-1q", tmp_path)
    assert {p: p.read_bytes() for p in written} == first


@pytest.mark.parametrize(
    "claimed, actual, status",
    [
        ("Barangay Sto. Niño, X", "Sto. Niño", "consistent"),
        ("Bgy. Alianza, City of Bago", "Alianza", "consistent"),
        ("Barangay Lapu-Lapu, X", "Lapu-lapu", "consistent (spelling differs)"),
        ("Bgy. Buanan, City of Bago", "Abuanan", "inconsistent"),
    ],
)
def test_name_status(claimed, actual, status):
    assert psgc_diff.name_status(claimed, actual) == status
