#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Fetch and check the raw source files, which live in the repo's `sources` GitHub release.

    python scripts/sources.py fetch [--from DIR]   # each file data/sources.toml lists: link, or download, and verify
    python scripts/sources.py check                # the files present against their SHA-256; 1 on a difference
    python scripts/sources.py manifest             # write data/sources.toml from the files on disk (a new source)
    python scripts/sources.py upload --target SHA [--yes]   # publish them as the `sources` release (CONTRACT 3)

fetch takes a file from DIR (by default this checkout's main checkout, so a worktree costs nothing)
when that copy matches, and otherwise downloads its asset with `gh`. A download that doesn't match its
hash is deleted, never put in place. upload prints what it would send and sends it only with --yes,
given after the maintainer's yes.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

# pylint: disable-next=wrong-import-position
from ph_psgc_shape.psgc_data import sha256_of  # noqa: E402

# pylint: disable-next=wrong-import-position
from ph_psgc_shape.sources import MANIFEST, SourceFile, Sources, load_sources  # noqa: E402

REPO_SLUG = "faeldon/philippines-psgc-shapefiles"
TAG = "sources"

# The folders whose files are sources, and where each came from (recorded in the manifest).
ORIGINS = {
    "data/2023": "OCHA COD-AB Philippines of 2023-11-06 (phl_admbnda_admN_psa_namria_20231106), by NAMRIA and PSA, "
    "CC BY-IGO: https://data.humdata.org/dataset/cod-ab-phl (HDX replaced these files with its v03 on 2026-05-28)",
    "data/edit/20240210": "this repo's hand edit (QGIS) of the 2023 adm4, for the PSGC's 3Q 2023 merges and splits",
    "data/2015": "OCHA's 2015 Level 0-3 shapefiles (no longer available) and the Level 4 shapefiles of "
    "https://github.com/justinelliotmeyers/official_philippines_shapefile_data_2016",
    "data/2011": "GADM's Level 0-4 shapefiles: https://gadm.org",
}


def gh(*args) -> subprocess.CompletedProcess:
    """Run the GitHub CLI; raise with what it said if it fails."""
    ran = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if ran.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {ran.stderr.strip() or ran.stdout.strip()}")
    return ran


def main_checkout(root: Path) -> Path | None:
    """The main checkout of the repository root is in, if root is a linked worktree; else None."""
    common = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    checkout = Path(common).parent if common else None
    return checkout if checkout and checkout.resolve() != root.resolve() else None


def asset_name(path: str) -> str:
    """A source's release asset: its path under data/, with / as __ (assets have no folders)."""
    return path.removeprefix("data/").replace("/", "__")


def matches(path: Path, f: SourceFile) -> bool:
    """Whether path holds exactly the file the manifest names (size first, the hash only if it agrees)."""
    return path.is_file() and path.stat().st_size == f.size and sha256_of(path) == f.sha256


def fetch(sources: Sources, root: Path, source: Path | None) -> list[str]:
    """Put every listed file in place under root; return one line per file that couldn't be."""
    problems = []
    for f in sources.files:
        dest = root / f.path
        if matches(dest, f):
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source is not None and matches(source / f.path, f):
            try:
                os.link(source / f.path, dest)
            except OSError:
                shutil.copy2(source / f.path, dest)
            print(f"linked     {f.path}")
            continue
        with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
            gh("release", "download", sources.tag, "-R", sources.repo, "-p", f.asset, "-D", tmp)
            got = Path(tmp) / f.asset
            if not matches(got, f):
                problems.append(f"{f.path}: the downloaded {f.asset} doesn't match its SHA-256; not kept")
                continue
            os.replace(got, dest)
        print(f"downloaded {f.path}")
    return problems


def check(sources: Sources, root: Path) -> list[str]:
    """One line per listed file that's missing or doesn't match its SHA-256."""
    problems = []
    for f in sources.files:
        path = root / f.path
        if not path.is_file():
            problems.append(f"{f.path}: missing (run `python scripts/sources.py fetch`)")
        elif not matches(path, f):
            problems.append(f"{f.path}: SHA-256 is {sha256_of(path)}, data/sources.toml says {f.sha256}")
    return problems


def manifest_text(root: Path) -> str:
    """data/sources.toml for the source folders' files on disk, in path order."""
    lines = [
        "# The raw source files the levels read, which are too big for git: assets of the repo's `sources`",
        "# GitHub release. scripts/sources.py fetches each to its path (gitignored) and checks its SHA-256",
        "# (CONTRACT 1). Written by `scripts/sources.py manifest`; a new source is a new entry.",
        "",
        f'repo = "{REPO_SLUG}"',
        f'tag = "{TAG}"',
    ]
    for folder, origin in ORIGINS.items():
        for path in sorted(p for p in (root / folder).rglob("*") if p.is_file() and p.name != ".DS_Store"):
            rel = path.relative_to(root).as_posix()
            lines += [
                "",
                "[[file]]",
                f'path = "{rel}"',
                f'asset = "{asset_name(rel)}"',
                f'sha256 = "{sha256_of(path)}"',
                f"size = {path.stat().st_size}",
                f'origin = "{origin}"',
            ]
    return "\n".join(lines) + "\n"


def upload(sources: Sources, root: Path, target: str, yes: bool) -> int:
    """Publish the files as the `sources` release at target; without yes, only say what would be sent."""
    total = sum(f.size for f in sources.files)
    print(f"release {sources.tag} of {sources.repo}, at {target}: {len(sources.files)} files, {total / 1e9:.2f} GB")
    for f in sources.files:
        print(f"  {f.asset}  {f.size / 1e6:,.1f} MB")
    problems = check(sources, root)
    if problems:
        print("\n".join(problems))
        return 1
    if not yes:
        print("nothing sent: rerun with --yes once the maintainer has said yes (CONTRACT 3)")
        return 3
    try:
        gh("release", "view", sources.tag, "-R", sources.repo, "--json", "tagName")
        exists = True
    except RuntimeError:
        exists = False
    if not exists:
        notes = "The raw source files this repo builds from (data/sources.toml lists each, with its SHA-256)."
        gh("release", "create", sources.tag, "-R", sources.repo, "--target", target, "--title", "Raw sources")
        gh("release", "edit", sources.tag, "-R", sources.repo, "--notes", notes, "--latest=false")
    have = set(
        gh(
            "release", "view", sources.tag, "-R", sources.repo, "--json", "assets", "-q", ".assets[].name"
        ).stdout.split()
    )
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        for f in sources.files:
            if f.asset in have:
                print(f"already there  {f.asset}")
                continue
            staged = Path(tmp) / f.asset
            os.link(root / f.path, staged)
            gh("release", "upload", sources.tag, "-R", sources.repo, str(staged))
            print(f"uploaded       {f.asset}")
    return 0


def main(argv=None) -> int:
    """Run fetch, check, manifest or upload, and return an exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    fetch_p = sub.add_parser("fetch")
    fetch_p.add_argument("--from", dest="source", type=Path, default=None)
    sub.add_parser("check")
    sub.add_parser("manifest")
    upload_p = sub.add_parser("upload")
    upload_p.add_argument("--target", required=True, help="the commit the release's tag is created at")
    upload_p.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "manifest":
        (REPO / MANIFEST).write_text(manifest_text(REPO))
        print(f"wrote {MANIFEST}")
        return 0
    sources = load_sources(REPO / MANIFEST)
    if args.command == "upload":
        return upload(sources, REPO, args.target, args.yes)
    if args.command == "fetch":
        problems = fetch(sources, REPO, args.source or main_checkout(REPO))
    else:
        problems = check(sources, REPO)
    for problem in problems:
        print(problem)
    print(f"sources {args.command}: {len(sources.files)} files, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
