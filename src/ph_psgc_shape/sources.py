#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""The raw source files the levels read, out of git: data/sources.toml, their manifest.

The OCHA boundaries, the hand-edited adm4 and the legacy zips are too big for plain git, so they are
assets of the repo's `sources` GitHub release. data/sources.toml names each one (its path under the
repo, the asset holding it, its SHA-256 and size, and where it came from), and scripts/sources.py
fetches them into those gitignored paths and checks them against it (CONTRACT 1).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .release import Table, closed, read_toml

# The manifest, relative to the repo root.
MANIFEST = Path("data") / "sources.toml"


class SourcesError(ValueError):
    """A sources manifest that can't be used, naming the file and the key at fault."""


@dataclass(frozen=True)
class SourceFile:
    """One raw file: where it goes, the release asset holding it, what it must hash to, and its origin."""

    path: str
    asset: str
    sha256: str
    size: int
    origin: str


@dataclass(frozen=True)
class Sources:
    """The release holding the raw files, and the files."""

    repo: str
    tag: str
    files: tuple[SourceFile, ...]

    def by_path(self) -> dict[str, SourceFile]:
        """The files, keyed by their path under the repo."""
        return {f.path: f for f in self.files}


def _file(t: Table) -> SourceFile:
    sha256 = t.take("sha256", "str")
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        t.fail(t.key("sha256"), "must be 64 lowercase hex digits")
    return closed(
        t,
        SourceFile(
            path=t.take("path", "str"),
            asset=t.take("asset", "str"),
            sha256=sha256,
            size=t.take("size", "int"),
            origin=t.take("origin", "str"),
        ),
    )


def load_sources(path) -> Sources:
    """Read and check a sources manifest: every key known, each hash 64 hex digits, no path or asset twice."""
    top = read_toml(Path(path), SourcesError)
    files = tuple(_file(f) for f in top.tables("file"))
    for key in ("path", "asset"):
        seen = set()
        for i, f in enumerate(files):
            if getattr(f, key) in seen:
                top.fail(f"file[{i}].{key}", f"repeats {getattr(f, key)!r}")
            seen.add(getattr(f, key))
    return closed(top, Sources(repo=top.take("repo", "str"), tag=top.take("tag", "str"), files=files))
