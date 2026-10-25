#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Read a release file (releases/<id>.toml): the sources and corrections one PSGC release is built from.

Everything that changes from one release to the next lives in the file, not in the code: the PSGC
publication it joins to (whose layout its manifest gives), each level's source shapefile and its
columns, and the corrections.
Overrides are applied in the order the file lists them, because one can move a row onto a code a
later one moves again.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

LEVEL_NAMES = ("country", "region", "provdists", "municities", "bgysubmuns")


class ReleaseError(ValueError):
    """A release file that can't be used, naming the file and the key at fault."""


@dataclass(frozen=True)
class Source:
    """A level's source shapefile and the names its columns are given, by position."""

    path: str
    columns: tuple[str, ...]


@dataclass(frozen=True)
class Override:
    """Move the rows whose PSGC code is old to new."""

    old: int
    new: int
    note: str = ""


@dataclass(frozen=True)
class ProvOverride:
    """Move an adm2 row from old to new, setting its adm2_pcode."""

    old: int
    new: int
    adm2_pcode: str
    note: str = ""


@dataclass(frozen=True)
class BgyOverride:
    """Move the barangay rows whose PSGC code is old (and name adm4_en, if given) to new."""

    old: int
    new: int
    adm4_en: str | None = None
    note: str = ""


@dataclass(frozen=True)
class NameFix:
    """Give the PSGC row with code this name: a typo in PSA's datafile, corrected as the table is read."""

    code: int
    name: str
    note: str = ""


@dataclass(frozen=True)
class Psgc:
    """The PSGC publication the release joins to: a folder under data/psgc/ (see psgc_data)."""

    publication: str
    names: tuple[NameFix, ...] = ()


@dataclass(frozen=True)
class Recode:
    """Move every source code whose first five digits are from_prefix to to_prefix (a transferred province)."""

    from_prefix: str
    to_prefix: str
    note: str = ""


@dataclass(frozen=True)
class Region:
    """adm1 corrections: the regions whose geometry is the union of their provinces and districts."""

    rebuild: tuple[int, ...] = ()


@dataclass(frozen=True)
class Merge:
    """Barangays merged into one: into takes the union of the from rows' shapes, and the others go."""

    into: int
    from_codes: tuple[int, ...]
    note: str = ""


@dataclass(frozen=True)
class Edits:
    """The release's split geometry: GeoJSON files in data/edit/<date>/ (levels.add_daughters, levels.approximate)."""

    plotted: str | None = None
    approximated: str | None = None


@dataclass(frozen=True)
class Provdists:
    """adm2 corrections: code overrides, and PSGC rows kept besides the Prov and Dist levels."""

    overrides: tuple[ProvOverride, ...]
    extra_names: tuple[str, ...]
    extra_codes: tuple[int, ...]


@dataclass(frozen=True)
class Municities:
    """adm3 corrections: code overrides, and the adm2 of each city PSA places under no province."""

    overrides: tuple[Override, ...]
    city_adm2: dict[int, int]
    rebuild: tuple[int, ...] = ()


@dataclass(frozen=True)
class Manila:
    """The codes that put Manila's sub-municipalities and pre-2021 barangays under the City of Manila."""

    ncr: int
    city: int
    old: int


@dataclass(frozen=True)
class Bgysubmuns:  # pylint: disable=too-many-instance-attributes
    """adm4 corrections and the codes the matching passes and parent fixes need."""

    overrides: tuple[BgyOverride, ...]
    reserved_min: int
    keep_reserved_prefix: str
    sga_from_prefix: str
    sga_to_prefix: str
    manila: Manila
    non_barangay_areas: dict[int, str]
    merges: tuple[Merge, ...] = ()
    shapeless: dict[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Debug:
    """A barangay whose matching is logged after every pass."""

    barangay: str
    psgc: int


@dataclass(frozen=True)
class Release:  # pylint: disable=too-many-instance-attributes
    """Everything one release of dist/ is built from."""

    id: str
    psgc: Psgc
    sources: dict[str, Source]
    provdists: Provdists
    municities: Municities
    bgysubmuns: Bgysubmuns
    debug: Debug | None = None
    recodes: tuple[Recode, ...] = ()
    region: Region = Region()
    edits: Edits = Edits()


_REQUIRED = object()


class Table:
    """One TOML table being read: each key is taken once, and anything left over is an error.

    Failures raise error (ReleaseError unless given), naming the file and the full key.
    """

    def __init__(self, path: Path, where: str, data, error=ReleaseError):
        self.path, self.where, self.error = path, where, error
        if not isinstance(data, dict):
            self.fail(where, "must be a table")
        self.data, self.taken = data, set()

    def fail(self, key: str, problem: str):
        """Raise this table's error naming the file and the full key."""
        raise self.error(f"{self.path}: {key}: {problem}")

    def key(self, name: str) -> str:
        """The full dotted name of a key in this table."""
        return f"{self.where}.{name}" if self.where else name

    def take(self, name: str, kind: str, default=_REQUIRED):
        """The value of name, checked to be of kind (int, str, strs, ints, table, tables)."""
        self.taken.add(name)
        if name not in self.data:
            if default is _REQUIRED:
                self.fail(self.key(name), "missing")
            return default
        value = self.data[name]
        if not _is_kind(value, kind):
            self.fail(self.key(name), f"must be {_KIND_NAMES[kind]}, not {value!r}")
        return value

    def table(self, name: str, default=_REQUIRED) -> Table | None:
        """The sub-table name, as a Table."""
        value = self.take(name, "table", default)
        return None if value is None else Table(self.path, self.key(name), value, self.error)

    def tables(self, name: str, default=_REQUIRED) -> list[Table]:
        """The array of tables name, each as a Table."""
        values = self.take(name, "tables", default)
        return [Table(self.path, f"{self.key(name)}[{i}]", t, self.error) for i, t in enumerate(values)]

    def close(self):
        """Fail on any key nothing took."""
        unknown = sorted(set(self.data) - self.taken)
        if unknown:
            self.fail(self.key(unknown[0]), "unknown key")


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_kind(value, kind: str) -> bool:
    checks = {
        "int": _is_int,
        "str": lambda v: isinstance(v, str),
        "strs": lambda v: isinstance(v, list) and all(isinstance(x, str) for x in v),
        "ints": lambda v: isinstance(v, list) and all(_is_int(x) for x in v),
        "table": lambda v: isinstance(v, dict),
        "tables": lambda v: isinstance(v, list) and all(isinstance(x, dict) for x in v),
    }
    return checks[kind](value)


_KIND_NAMES = {
    "int": "an integer",
    "str": "a string",
    "strs": "a list of strings",
    "ints": "a list of integers",
    "table": "a table",
    "tables": "a list of tables",
}


def closed(table: Table, value):
    """Close table (failing on any key nothing took) and return value."""
    table.close()
    return value


def _psgc(t: Table) -> Psgc:
    names = []
    for i, n in enumerate(t.tables("names", [])):
        fix = closed(n, NameFix(code=n.take("code", "int"), name=n.take("name", "str"), note=n.take("note", "str", "")))
        if fix.code in {f.code for f in names}:
            t.fail(f"{t.key('names')}[{i}].code", f"duplicate code {fix.code}")
        names.append(fix)
    return closed(t, Psgc(publication=t.take("publication", "str"), names=tuple(names)))


def _prefix_of(t: Table, name: str) -> str:
    """A five-digit code prefix, as text (a province's first five PSGC digits)."""
    value = t.take(name, "str")
    if not (value.isdigit() and len(value) == 5):
        t.fail(t.key(name), f"must be five digits, not {value!r}")
    return value


def _recodes(t: Table | None) -> tuple[Recode, ...]:
    if t is None:
        return ()
    recodes = []
    for i, r in enumerate(t.tables("prefixes")):
        recode = closed(r, Recode(_prefix_of(r, "from"), _prefix_of(r, "to"), r.take("note", "str", "")))
        if recode.from_prefix in {x.from_prefix for x in recodes}:
            t.fail(f"{t.key('prefixes')}[{i}].from", f"duplicate prefix {recode.from_prefix}")
        recodes.append(recode)
    return closed(t, tuple(recodes))


def _region(t: Table | None) -> Region:
    if t is None:
        return Region()
    return closed(t, Region(rebuild=tuple(t.take("rebuild", "ints", []))))


def _edits(t: Table | None) -> Edits:
    if t is None:
        return Edits()
    return closed(t, Edits(plotted=t.take("plotted", "str", None), approximated=t.take("approximated", "str", None)))


def _sources(t: Table) -> dict[str, Source]:
    sources = {}
    for level in LEVEL_NAMES:
        s = t.table(level)
        sources[level] = closed(s, Source(path=s.take("path", "str"), columns=tuple(s.take("columns", "strs"))))
    t.close()
    return sources


def _override(o: Table) -> Override:
    return closed(o, Override(old=o.take("old", "int"), new=o.take("new", "int"), note=o.take("note", "str", "")))


def _provdists(t: Table) -> Provdists:
    overrides = tuple(
        closed(
            o,
            ProvOverride(
                old=o.take("old", "int"),
                new=o.take("new", "int"),
                adm2_pcode=o.take("adm2_pcode", "str"),
                note=o.take("note", "str", ""),
            ),
        )
        for o in t.tables("overrides")
    )
    return closed(
        t,
        Provdists(
            overrides=overrides,
            extra_names=tuple(t.take("extra_names", "strs", [])),
            extra_codes=tuple(t.take("extra_codes", "ints", [])),
        ),
    )


def _municities(t: Table) -> Municities:
    overrides = tuple(_override(o) for o in t.tables("overrides"))
    seen = set()
    for i, o in enumerate(overrides):
        if o.old in seen:
            t.fail(f"{t.key('overrides')}[{i}].old", f"duplicate old code {o.old}")
        seen.add(o.old)
    city_adm2 = {}
    for c in t.tables("city_adm2"):
        c.take("note", "str", "")
        city_adm2[c.take("city", "int")] = c.take("adm2", "int")
        c.close()
    return closed(t, Municities(overrides=overrides, city_adm2=city_adm2, rebuild=tuple(t.take("rebuild", "ints", []))))


def _bgysubmuns(t: Table) -> Bgysubmuns:
    overrides = tuple(
        closed(
            o,
            BgyOverride(
                old=o.take("old", "int"),
                new=o.take("new", "int"),
                adm4_en=o.take("adm4_en", "str", None),
                note=o.take("note", "str", ""),
            ),
        )
        for o in t.tables("overrides")
    )
    m = t.table("manila")
    manila = closed(m, Manila(ncr=m.take("ncr", "int"), city=m.take("city", "int"), old=m.take("old", "int")))
    areas = {}
    for a in t.tables("non_barangay_areas"):
        areas[a.take("code", "int")] = a.take("name", "str")
        a.close()
    merges = tuple(
        closed(
            m,
            Merge(into=m.take("into", "int"), from_codes=tuple(m.take("from", "ints")), note=m.take("note", "str", "")),
        )
        for m in t.tables("merges", [])
    )
    shapeless = {}
    for s in t.tables("shapeless", []):
        shapeless[s.take("code", "int")] = s.take("note", "str")
        s.close()
    return closed(
        t,
        Bgysubmuns(
            overrides=overrides,
            reserved_min=t.take("reserved_min", "int"),
            keep_reserved_prefix=t.take("keep_reserved_prefix", "str"),
            sga_from_prefix=t.take("sga_from_prefix", "str"),
            sga_to_prefix=t.take("sga_to_prefix", "str"),
            manila=manila,
            non_barangay_areas=areas,
            merges=merges,
            shapeless=shapeless,
        ),
    )


def _check_recodes(path: Path, release: Release):
    """Fail on two overlapping prefixes, or on a correction whose code a recode moves before it runs.

    The recodes run first, so a correction naming a code under a recoded prefix would never match.
    """
    froms = [r.from_prefix for r in release.recodes]
    for r in release.recodes:
        if r.to_prefix in froms:
            raise ReleaseError(f"{path}: recode.prefixes: {r.from_prefix}→{r.to_prefix} lands on a recoded prefix")
    corrections = [(f"provdists.overrides[{i}].old", o.old) for i, o in enumerate(release.provdists.overrides)] + [
        (f"municities.overrides[{i}].old", o.old) for i, o in enumerate(release.municities.overrides)
    ]
    corrections += [(f"bgysubmuns.overrides[{i}].old", o.old) for i, o in enumerate(release.bgysubmuns.overrides)]
    corrections += [("municities.city_adm2.city", code) for code in release.municities.city_adm2]
    for key, code in corrections:
        if str(code).zfill(10)[:5] in froms:
            raise ReleaseError(f"{path}: {key}: {code} is under a recoded prefix; name its recoded code")


def _debug(t: Table | None) -> Debug | None:
    if t is None:
        return None
    return closed(t, Debug(barangay=t.take("barangay", "str"), psgc=t.take("psgc", "int")))


def check_path(path: Path, rel: str, key: str, root: Path):
    """Fail unless rel exists under root with exactly this casing, segment by segment.

    macOS's filesystem ignores case, so a plain exists() passes there for a path that fails on Linux.
    """
    current = root
    for part in Path(rel).parts:
        if not current.is_dir() or part not in os.listdir(current):
            raise ReleaseError(f"{path}: {key}: {rel} not found under {root} (paths are case-sensitive)")
        current = current / part


def read_toml(path: Path, error=ReleaseError) -> Table:
    """The TOML file at path as a top-level Table; an unreadable file raises error naming it."""
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise error(f"{path}: {e}") from e
    return Table(path, "", data, error)


def check_source(path: Path, rel: str, key: str, root: Path):
    """check_path for a level's source, saying to fetch it when data/sources.toml lists it.

    The raw sources aren't in git (data/sources.toml, scripts/sources.py), so a fresh checkout has none
    until they're fetched; that, not a wrong path, is the usual reason one is missing.
    """
    try:
        check_path(path, rel, key, root)
    except ReleaseError as e:
        manifest = root / "data" / "sources.toml"
        if manifest.is_file() and f'path = "{rel}"' in manifest.read_text(encoding="utf-8"):
            raise ReleaseError(f"{e}; it's a raw source: run `python scripts/sources.py fetch`") from e
        raise


def load_release(path, root=None, check_paths=True, check_sources=True) -> Release:
    """Read and check the release file at path.

    Source paths and the PSGC publication's folder are relative to root (the working directory by default) and, unless
    check_paths is False, must exist there. check_sources=False skips only the levels' source files, for what
    reads the PSGC table and not the boundaries (check_dist, CI without the fetched sources). Raises ReleaseError for
    anything unusable.
    """
    path = Path(path)
    top = read_toml(path)
    release = Release(
        id=top.take("id", "str"),
        psgc=_psgc(top.table("psgc")),
        sources=_sources(top.table("sources")),
        provdists=_provdists(top.table("provdists")),
        municities=_municities(top.table("municities")),
        bgysubmuns=_bgysubmuns(top.table("bgysubmuns")),
        debug=_debug(top.table("debug", None)),
        recodes=_recodes(top.table("recode", None)),
        region=_region(top.table("region", None)),
        edits=_edits(top.table("edits", None)),
    )
    top.close()
    _check_recodes(path, release)
    if check_paths:
        root = Path.cwd() if root is None else Path(root)
        for name in ("manifest.toml", "psgc.csv"):
            check_path(path, f"data/psgc/{release.psgc.publication}/{name}", "psgc.publication", root)
        for level, source in release.sources.items() if check_sources else ():
            check_source(path, source.path, f"sources.{level}.path", root)
        for kind in ("plotted", "approximated"):
            edit = getattr(release.edits, kind)
            if edit is not None:
                check_path(path, edit, f"edits.{kind}", root)
    return release
