#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Diff two PSGC publications into a worklist, and check PSA's claims against what the data shows.

PSA hand-encodes its datafiles, so a claim in the Summary of Changes can disagree with the datafile it
came with. diff() reads only the committed files under data/psgc/: both publications' tables (through
psgc.load_table, so the diff sees the table the pipeline does) and the newer one's Summary of Changes.
It writes data/psgc/<new>/diff-from-<old>.md and .csv, the same bytes for the same inputs, and nothing
else. Every claim is reported, with a status, and every difference no claim covers is reported as
unexplained: nothing is resolved silently.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

import pandas as pd

from .psgc import load_table, read_csv
from .psgc_data import Manifest, load_manifest

CONSISTENT = "consistent"
SPELLING = "consistent (spelling differs)"
INCONSISTENT = "inconsistent"
NOT_FOUND = "not found"
UNCHECKED = "unchecked"
UNEXPLAINED = "unexplained"
# The order statuses are reported in: what needs a person's attention first.
STATUS_ORDER = (INCONSISTENT, NOT_FOUND, UNCHECKED, SPELLING, CONSISTENT)

# A claim's kind, from the first of these keywords its Unit Type contains (lowercased).
KINDS = (
    ("correction", "rename"),
    ("renam", "rename"),
    ("change of name", "rename"),
    ("transfer", "transfer"),
    ("merg", "merge"),
    ("split", "split"),
    ("divi", "split"),
    ("new city", "reclassify"),
    ("conversion", "reclassify"),
    ("convert", "reclassify"),
    ("creat", "create"),
    ("new", "create"),
)

# Words that can lead a claim's name but not the datafile's (some datafile names keep them: "Barangay 176-A").
NAME_PREFIXES = ("Barangay ", "Bgy. ", "Municipality of ", "Province of ")

# The national summary's count columns, by the start of their header, and the levels each counts.
COUNTS = (("PROV", ("Prov",)), ("CIT", ("City",)), ("MUN", ("Mun",)), ("BGY", ("Bgy",)))

CSV_COLUMNS = (
    "kind",
    "status",
    "type",
    "section",
    "code",
    "old_code",
    "name_old",
    "name_new",
    "level_old",
    "level_new",
    "detail",
)


@dataclass
class Claim:
    """One claim in a Summary of Changes, with the continuation rows folded into it."""

    section: str
    type: str
    name: str
    new_codes: list[str] = field(default_factory=list)
    old_name: str = ""
    old_codes: list[str] = field(default_factory=list)
    parts: list[tuple[str, str]] = field(default_factory=list)  # merged units: (old name, old code)

    @property
    def kind(self) -> str:
        """rename, transfer, merge, split, reclassify, create, or unchecked."""
        lowered = self.type.lower()
        return next((kind for word, kind in KINDS if word in lowered), UNCHECKED)


class Finding(dict):
    """A claim checked against the data, a difference, or a count mismatch: one row of the report.

    Keyed by CSV_COLUMNS (each "" unless given), and readable as attributes: finding.status.
    """

    def __init__(self, **values):
        unknown = sorted(set(values) - set(CSV_COLUMNS))
        if unknown:
            raise TypeError(f"Finding has no column {unknown[0]!r}")
        super().__init__({c: values.get(c, "") for c in CSV_COLUMNS})

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name, value):
        if name not in CSV_COLUMNS:
            raise AttributeError(name)
        self[name] = value

    def row(self) -> list[str]:
        """The finding as a CSV row, in CSV_COLUMNS order."""
        return [self[c] for c in CSV_COLUMNS]


def _text(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def read_claims(manifest) -> list[Claim]:
    """The publication's claims, from its summary-of-changes.csv.

    A row with no name continues the claim above it: its old name and code are a merged unit, its new
    code a further new unit. A row with no Unit Type takes the type of the row above it in its section.
    """
    claims, last_type = [], {}
    df = read_csv(manifest.folder / "summary-of-changes.csv")
    for row in df.itertuples(index=False):
        section, name, unit_type, new_code, old_name, old_code = (_text(v) for v in row[:6])
        unit_type = unit_type or last_type.get(section, "")
        last_type[section] = unit_type
        if name or not claims:
            claims.append(Claim(section=section, type=unit_type, name=name, old_name=old_name))
            claim = claims[-1]
            claim.new_codes += [new_code] if new_code else []
            claim.old_codes += [old_code] if old_code else []
            continue
        claim = claims[-1]
        claim.new_codes += [new_code] if new_code else []
        if old_name or old_code:
            claim.parts.append((old_name, old_code))
    return claims


def code_of(text: str) -> int | None:
    """A 10-digit PSGC code as an int; None for anything else (older 9-digit codes aren't comparable)."""
    return int(text) if re.fullmatch(r"\d{10}", text) else None


def claim_names(text: str) -> tuple[str, ...]:
    """The names a claim can mean: the text before the first comma, as it is and without a leading unit word."""
    name = text.split(",")[0].strip()
    for prefix in NAME_PREFIXES:
        if name.startswith(prefix):
            return (name, name[len(prefix) :])
    return (name,)


def _folded(name: str) -> str:
    return re.sub(r"[\W_]+", "", name.casefold())


def name_status(claimed: str, actual: str) -> str:
    """consistent if the claim's name (with or without its unit word) equals actual, consistent (spelling
    differs) if only case, spacing or punctuation differ, inconsistent otherwise."""
    names = claim_names(claimed)
    if actual in names:
        return CONSISTENT
    return SPELLING if _folded(actual) in {_folded(n) for n in names} else INCONSISTENT


def _worst(*statuses) -> str:
    return min(statuses, key=STATUS_ORDER.index)


def duplicates(pub_id: str, table: pd.DataFrame) -> list[Finding]:
    """Each code the publication's table lists more than once, as an inconsistent finding.

    Tables compares the first row of each code, so without this a repeated code would vanish unseen.
    """
    repeated = table[table["psgc_code"].duplicated(keep=False)]
    return [
        Finding(
            kind="duplicate",
            status=INCONSISTENT,
            section=pub_id,
            code=str(code).zfill(10),
            name_new="; ".join(_text(n) for n in rows["name"]),
            detail=f"listed {len(rows)} times; the diff compares the first",
        )
        for code, rows in repeated.groupby("psgc_code", sort=True)
    ]


class Tables:
    """The two publications' tables, by code (the first row of a code PSA lists twice; see duplicates)."""

    def __init__(self, old: pd.DataFrame, new: pd.DataFrame, old_id: str, new_id: str):
        self.old = old.drop_duplicates("psgc_code").set_index("psgc_code")
        self.new = new.drop_duplicates("psgc_code").set_index("psgc_code")
        self.old_id, self.new_id = old_id, new_id

    def get(self, side: str, code: int | None):
        """The row for code in old or new, or None."""
        table = self.old if side == "old" else self.new
        return None if code is None or code not in table.index else table.loc[code]

    def describe(self, side: str, code: int | None) -> str:
        """How a code appears in one publication, for a report's detail."""
        row = self.get(side, code)
        pub = self.old_id if side == "old" else self.new_id
        return f"not in {pub}" if row is None else f"{_text(row['name'])} ({_text(row['geo_level'])}) in {pub}"


def _finding(claim: Claim, status: str, tables: Tables, codes: tuple, detail="") -> Finding:
    """The claim's report row; codes is its (new code, old code) as ints or None."""
    code, old_code = codes
    old_row, new_row = tables.get("old", old_code if old_code is not None else code), tables.get("new", code)
    return Finding(
        kind="claim",
        status=status,
        type=claim.type,
        section=claim.section,
        code=claim.new_codes[0] if claim.new_codes else "",
        old_code=claim.old_codes[0] if claim.old_codes else "",
        name_old=claim.old_name,
        name_new=claim.name,
        level_old="" if old_row is None else _text(old_row["geo_level"]),
        level_new="" if new_row is None else _text(new_row["geo_level"]),
        detail=detail,
    )


def _name_check(claim: Claim, tables: Tables, code: int) -> tuple[str, str]:
    """The claim's name against the new publication's, and a detail when they differ."""
    row = tables.get("new", code)
    status = name_status(claim.name, _text(row["name"]))
    return status, ("" if status == CONSISTENT else f"the datafile names it {_text(row['name'])!r}")


def check_claim(claim: Claim, tables: Tables) -> tuple[Finding, set[int]]:
    """The claim's status by the rule for its kind, and the codes whose differences it explains."""
    codes = [code_of(c) for c in claim.new_codes]
    old_codes = [code_of(c) for c in claim.old_codes]
    code = codes[0] if codes else None
    old_code = old_codes[0] if old_codes else None
    kind = claim.kind
    if kind == UNCHECKED:
        return _finding(claim, UNCHECKED, tables, (code, old_code), f"no rule for {claim.type!r}"), set()
    if code is None:
        return _finding(claim, NOT_FOUND, tables, (None, old_code), "the claim gives no 10-digit new code"), set()
    if tables.get("new", code) is None:
        return _finding(claim, NOT_FOUND, tables, (code, old_code), f"{code} is {tables.describe('new', code)}"), set()
    rule = {
        "rename": _rename,
        "reclassify": _reclassify,
        "create": _create,
        "transfer": _transfer,
        "merge": _merge,
        "split": _split,
    }[kind]
    status, detail, covered = rule(claim, tables, code, old_code)
    return _finding(claim, status, tables, (code, old_code), detail), covered


def _rename(claim, tables, code, _old_code):
    status, detail = _name_check(claim, tables, code)
    old = tables.get("old", code)
    if old is None:
        return INCONSISTENT, f"{code} is {tables.describe('old', code)}", {code}
    if claim.old_name:
        old_status = name_status(claim.old_name, _text(old["name"]))
        if old_status != CONSISTENT:
            detail = "; ".join(filter(None, [detail, f"{tables.old_id} names it {_text(old['name'])!r}"]))
        status = _worst(status, old_status)
    return status, detail, {code}


def _reclassify(claim, tables, code, _old_code):
    status, detail = _name_check(claim, tables, code)
    old, new = tables.get("old", code), tables.get("new", code)
    if old is None:
        return INCONSISTENT, f"{code} is {tables.describe('old', code)}", {code}
    if old["geo_level"] == new["geo_level"]:
        return INCONSISTENT, f"its level stays {_text(new['geo_level'])}", {code}
    return status, detail, {code}


def _create(claim, tables, code, _old_code):
    status, detail = _name_check(claim, tables, code)
    old, new = tables.get("old", code), tables.get("new", code)
    if old is not None and old["geo_level"] == new["geo_level"]:
        return INCONSISTENT, f"{code} was already {tables.describe('old', code)}", {code}
    if old is not None:
        detail = "; ".join(filter(None, [detail, f"reuses the code of {tables.describe('old', code)}"]))
    return status, detail, {code}


def _transfer(claim, tables, code, old_code):
    status, detail = _name_check(claim, tables, code)
    if old_code is None or old_code == code:
        if tables.get("old", code) is None:
            return INCONSISTENT, f"{code} is {tables.describe('old', code)}", {code}
        return status, "; ".join(filter(None, [detail, "same code; the new parent isn't checked"])), {code}
    problems = []
    if tables.get("old", old_code) is None:
        problems.append(f"old code {old_code} is {tables.describe('old', old_code)}")
    if tables.get("new", old_code) is not None:
        problems.append(f"old code {old_code} is still {tables.describe('new', old_code)}")
    if tables.get("old", code) is not None:
        problems.append(f"new code {code} was already {tables.describe('old', code)}")
    if problems:
        return INCONSISTENT, "; ".join(problems), {code, old_code}
    return status, detail, {code, old_code}


def _merge(claim, tables, code, old_code):
    status, detail = _name_check(claim, tables, code)
    merged = [code_of(c) for c in claim.old_codes] + [code_of(c) for _, c in claim.parts]
    remaining = [c for c in merged if c is not None and c != code and tables.get("new", c) is not None]
    if remaining:
        listed = ", ".join(f"{c} ({tables.describe('new', c)})" for c in remaining)
        return INCONSISTENT, f"merged codes still present: {listed}", {code, *filter(None, merged)}
    return status, detail, {code, *filter(None, merged), *filter(None, [old_code])}


def _split(claim, tables, code, old_code):
    status, detail = _name_check(claim, tables, code)
    missing = [c for c in (code_of(x) for x in claim.new_codes[1:]) if c is not None and tables.get("new", c) is None]
    if missing:
        return INCONSISTENT, f"new codes not in {tables.new_id}: {', '.join(map(str, missing))}", {code}
    return status, detail, {code, *filter(None, [old_code]), *filter(None, map(code_of, claim.new_codes))}


def differences(tables: Tables) -> list[Finding]:
    """Every code added, removed, renamed, changed in level, or changed in corr_code, by code."""
    out = []
    old, new = tables.old, tables.new
    for code in sorted(set(old.index) | set(new.index)):
        o, n = tables.get("old", code), tables.get("new", code)
        if o is None or n is None:
            row = n if o is None else o
            out.append(
                Finding(
                    kind="added" if o is None else "removed",
                    status="",
                    code=str(code).zfill(10),
                    name_old="" if o is None else _text(row["name"]),
                    name_new="" if n is None else _text(row["name"]),
                    level_old="" if o is None else _text(row["geo_level"]),
                    level_new="" if n is None else _text(row["geo_level"]),
                )
            )
            continue
        changes = []
        if _text(o["name"]) != _text(n["name"]):
            changes.append("renamed")
        if _text(o["geo_level"]) != _text(n["geo_level"]):
            changes.append("level changed")
        if not (pd.isna(o["corr_code"]) and pd.isna(n["corr_code"])) and o["corr_code"] != n["corr_code"]:
            changes.append(f"corr_code {_text(o['corr_code'])} -> {_text(n['corr_code'])}")
        if changes:
            out.append(
                Finding(
                    kind="changed",
                    status="",
                    code=str(code).zfill(10),
                    name_old=_text(o["name"]),
                    name_new=_text(n["name"]),
                    level_old=_text(o["geo_level"]),
                    level_new=_text(n["geo_level"]),
                    detail="; ".join(changes),
                )
            )
    return out


def _cell(row: list[str], i: int | None) -> str:
    """A summary row's cell i, stripped; empty past the row's end or for no column."""
    return row[i].strip() if i is not None and i < len(row) else ""


def _count(value: str) -> int | None:
    """A summary cell as a count: a dash is zero; anything that isn't a whole number is None."""
    value = "0" if value in ("-", "–", "—") else value.replace(",", "")
    return int(float(value)) if re.fullmatch(r"\d+(\.0+)?", value) else None


def _region_mismatches(manifest, row: list[str], columns: dict, in_region: pd.DataFrame) -> list[Finding]:
    """One region row of the national summary against its region's rows of the PSGC table."""
    out = []
    for label, levels in COUNTS:
        claimed = _count(_cell(row, columns[label]))
        actual = int(in_region["geo_level"].isin(levels).sum())
        if claimed is not None and claimed != actual:
            out.append(
                Finding(
                    kind="count",
                    status=INCONSISTENT,
                    section=manifest.id,
                    code=_cell(row, columns["CODE"]),
                    name_new=_cell(row, columns["CODE"] + 1),
                    detail=f"{label}: the summary says {claimed}, the PSGC sheet has {actual} {'/'.join(levels)}",
                )
            )
    return out


def count_check(manifest, table: pd.DataFrame) -> list[Finding]:
    """Each region's counts in the national summary against counts from the PSGC table; the mismatches.

    A summary with no region rows to compare is reported as unchecked, never passed.
    """
    rows = list(csv.reader(io.StringIO((manifest.folder / "national-summary.csv").read_text(encoding="utf-8"))))
    header_at = next((i for i, r in enumerate(rows) if any(c.strip().upper() == "CODE" for c in r)), None)
    if header_at is None:
        return [Finding(kind="count", status=UNCHECKED, section=manifest.id, detail="no CODE header in the summary")]
    header = [c.strip().upper() for c in rows[header_at]]
    columns = {label: next((i for i, h in enumerate(header) if h.startswith(label)), None) for label, _ in COUNTS}
    columns["CODE"] = header.index("CODE")
    prefix = table["psgc_code"].map(lambda c: str(c).zfill(10)[:2])
    regions = [r for r in rows[header_at + 1 :] if re.fullmatch(r"\d{10}", _cell(r, columns["CODE"]))]
    if not regions:
        return [Finding(kind="count", status=UNCHECKED, section=manifest.id, detail="no region rows to compare")]
    out = []
    for r in regions:
        out += _region_mismatches(manifest, r, columns, table[prefix == _cell(r, columns["CODE"])[:2]])
    return out


def layout_rows(manifest) -> set[int]:
    """The codes whose rows the manifest's layout supplies (add_rows), not PSA's sheet."""
    return {r.code for r in manifest.layout.add_rows}


@dataclass
class Comparison:
    """What diff reports: the claims checked, the unexplained differences, the count findings, and the
    codes either publication lists twice."""

    old: Manifest  # the older publication
    new: Manifest  # the newer publication
    claims: list[Finding]
    unexplained: list[Finding]
    counts: list[Finding]
    duplicates: list[Finding]


def compare(old_id: str, new_id: str, root=None) -> Comparison:
    """Check the newer publication's claims and both summaries, and find the differences no claim covers.

    A difference in a row a manifest supplies (its layout's add_rows) is the layout's, not PSA's, so
    it isn't reported as unexplained; the report names those rows instead.
    """
    old_m, new_m = load_manifest(old_id, root), load_manifest(new_id, root)
    old_t, new_t = load_table(old_m), load_table(new_m)
    tables = Tables(old_t, new_t, old_id, new_id)
    checked = [check_claim(claim, tables) for claim in read_claims(new_m)]
    covered = layout_rows(old_m) | layout_rows(new_m) | set().union(*(codes for _, codes in checked))
    unexplained = [d for d in differences(tables) if int(d.code) not in covered]
    for d in unexplained:
        d.status = UNEXPLAINED
    counts = count_check(old_m, old_t) + count_check(new_m, new_t)
    return Comparison(
        old=old_m,
        new=new_m,
        claims=[f for f, _ in checked],
        unexplained=unexplained,
        counts=counts,
        duplicates=duplicates(old_id, old_t) + duplicates(new_id, new_t),
    )


def _md_table(findings: list[Finding], columns) -> list[str]:
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = ["| " + " | ".join(h for h, _ in columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(cell(getattr(f, a)) for _, a in columns) + " |" for f in findings]
    return lines


def report(comparison: Comparison) -> str:
    """The Markdown report: a summary, then claims by status, unexplained differences and counts."""
    old_m, new_m = comparison.old, comparison.new
    old_id, new_id = old_m.id, new_m.id
    unexplained, counts = comparison.unexplained, comparison.counts
    by_status = {s: [c for c in comparison.claims if c.status == s] for s in STATUS_ORDER}
    lines = [
        f"# PSGC diff: {old_id} → {new_id}",
        "",
        f"From PSA's {old_id} publication (as of {old_m.as_of}) to {new_id} (as of {new_m.as_of},"
        f" [announcement]({new_m.announcement})). Claims are the rows of {new_id}'s Summary of Changes"
        f" ({', '.join(repr(s) for s in new_m.soc_sections)}), checked against both datafiles.",
        "",
        f"Written by `python scripts/psgc_data.py diff {old_id} {new_id}` from the committed files under"
        " `data/psgc/`; rerunning it gives this file unchanged.",
        "",
    ]
    for pub_id, manifest in ((old_id, old_m), (new_id, new_m)):
        added = sorted(layout_rows(manifest))
        if added:
            lines += [
                f"{pub_id}'s datafile lacks {len(added)} rows its manifest adds ({', '.join(map(str, added))});"
                " differences in them are the manifest's, not PSA's, and aren't listed below.",
                "",
            ]
    lines += [
        "## Summary",
        "",
        "| | Count |",
        "|---|---|",
    ]
    lines += [f"| Claims {s} | {len(by_status[s])} |" for s in STATUS_ORDER]
    lines += [
        f"| Differences no claim explains | {len(unexplained)} |",
        f"| Summary count findings | {len(counts)} |",
        f"| Codes listed more than once | {len(comparison.duplicates)} |",
    ]
    claim_columns = [
        ("Status", "status"),
        ("Type", "type"),
        ("Claim", "name_new"),
        ("New code", "code"),
        ("Old name", "name_old"),
        ("Old code", "old_code"),
        ("Level", "level_new"),
        ("What the data shows", "detail"),
    ]
    for status in STATUS_ORDER:
        if by_status[status]:
            lines += ["", f"## Claims: {status} ({len(by_status[status])})", ""]
            lines += _md_table(by_status[status], claim_columns)
    if comparison.duplicates:
        lines += ["", f"## Codes listed more than once ({len(comparison.duplicates)})", ""]
        lines += _md_table(
            comparison.duplicates,
            [("Publication", "section"), ("Code", "code"), ("Names", "name_new"), ("Finding", "detail")],
        )
    lines += ["", f"## Differences no claim explains ({len(unexplained)})", ""]
    if unexplained:
        lines += _md_table(
            unexplained,
            [
                ("Change", "kind"),
                ("Code", "code"),
                (f"Name in {old_id}", "name_old"),
                (f"Name in {new_id}", "name_new"),
                ("Level", "level_old"),
                ("Level after", "level_new"),
                ("Detail", "detail"),
            ],
        )
    else:
        lines.append("None: every difference between the two datafiles is covered by a claim.")
    lines += ["", f"## Summary counts against the PSGC sheet ({len(counts)})", ""]
    if counts:
        lines += _md_table(
            counts,
            [
                ("Status", "status"),
                ("Publication", "section"),
                ("Region", "code"),
                ("Name", "name_new"),
                ("Finding", "detail"),
            ],
        )
    else:
        lines.append(
            "Every region's province, city, municipality and barangay count in both national summaries"
            " matches its PSGC sheet (Prov, City, Mun and Bgy rows by region code)."
        )
    return "\n".join(lines) + "\n"


def diff(old_id: str, new_id: str, root=None) -> list:
    """Write data/psgc/<new_id>/diff-from-<old_id>.md and .csv; return their paths."""
    comparison = compare(old_id, new_id, root)
    folder = comparison.new.folder
    md = folder / f"diff-from-{old_id}.md"
    md.write_text(report(comparison), encoding="utf-8")
    out = folder / f"diff-from-{old_id}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        findings = comparison.claims + comparison.duplicates + comparison.unexplained + comparison.counts
        writer.writerows(row.row() for row in findings)
    return [md, out]
