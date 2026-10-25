#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Publish a built quarter as a GitHub release: its zips, CSVs and SHA256SUMS, in two steps.

    python scripts/publish_release.py prepare <out_dir> [--release releases/<id>.toml] [--since ID|DATE] [--latest]
    python scripts/publish_release.py upload --tag TAG [--id ID] [--target SHA]

prepare checks <out_dir>/dist (a regenerate.py build), requires its CSVs to equal the committed dist/
when it's the current release, diffs it against the latest published release, stages it in
release-staging/<publication id>/ and prints what would be published. It uploads nothing: the
maintainer reads the summary and says yes (CONTRACT 3). upload, run by /sdlc:publish as
release.publish, then publishes exactly the staged bytes, refusing any that changed since prepare.
It creates the release, or adds the assets it lacks; it never replaces one.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import check_dist
import regenerate

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

# pylint: disable-next=wrong-import-position
from ph_psgc_shape.psgc_data import load_manifest, publications, sha256_of  # noqa: E402

# pylint: disable-next=wrong-import-position
from ph_psgc_shape.release import load_release  # noqa: E402

REPO_SLUG = "faeldon/philippines-psgc-shapefiles"
CURRENT = REPO / regenerate.RELEASE  # the release dist/ holds
STAGING = REPO / "release-staging"
SOURCES_TAG = "sources"
# The machine-readable line in a release's notes naming the publication it matches.
MARKER = "<!-- psgc-publication: {} -->"
MONTHS = {
    m: i
    for i, m in enumerate(
        "January February March April May June July August September October " "November December".split(), 1
    )
}


class PublishError(RuntimeError):
    """A build or a staged release that can't be published, saying why."""


def gh(*args) -> subprocess.CompletedProcess:
    """Run the GitHub CLI; raise with what it said if it fails."""
    ran = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if ran.returncode != 0:
        raise PublishError(f"gh {' '.join(args[:2])} failed: {ran.stderr.strip() or ran.stdout.strip()}")
    return ran


def assets_of(dist_dir: Path) -> dict[str, Path]:
    """A build's release assets, by asset name: each level's zip and CSV, complete's adm4 suffixed _complete."""
    out = {}
    for level in check_dist.LEVELS:
        for ext in (".shp.zip", ".csv"):
            out[f"{level.stem}{ext}"] = dist_dir / f"{level.stem}{ext}"
            complete = dist_dir / check_dist.COMPLETE / f"{level.stem}{ext}"
            if complete.exists():
                out[f"{level.stem}_complete{ext}"] = complete
    return out


def layout(assets: Path, dest: Path) -> Path:
    """Lay downloaded release assets out as a dist/ directory (complete's back under complete/); return dest."""
    (dest / check_dist.COMPLETE).mkdir(parents=True, exist_ok=True)
    for path in assets.iterdir():
        name = path.name.replace("_complete.", ".")
        target = dest / check_dist.COMPLETE / name if "_complete." in path.name else dest / name
        shutil.copy2(path, target)
    return dest


def label(pub_id: str) -> str:
    """A publication id as people say it: 2026-3q → 3Q 2026, 2024-04 → April 2024."""
    year, part = pub_id.split("-")
    if part.endswith("q"):
        return f"{part.upper()} {year}"
    return f"{list(MONTHS)[int(part) - 1]} {year}"


def as_of(since: str | None) -> datetime.date | None:
    """The date notes start after: a publication id's as_of, an ISO date, or None for no lower bound."""
    if since is None:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", since):
        return datetime.date.fromisoformat(since)
    return datetime.date.fromisoformat(load_manifest(since).as_of)


def announcements(pub_id: str, since: datetime.date | None) -> set[str]:
    """The PSA announcement URLs of the publications after since, up to and including pub_id (their manifests)."""
    until = datetime.date.fromisoformat(load_manifest(pub_id).as_of)
    urls = set()
    for other in publications():
        manifest = load_manifest(other)
        when = datetime.date.fromisoformat(manifest.as_of)
        if (since is None or when > since) and when <= until:
            urls.add(manifest.announcement)
    return urls


def notes(changelog: str, pub_id: str, since: datetime.date | None) -> str:
    """A release's notes: the CHANGELOG.md rows of the publications after since up to this one (matched by their
    manifests' PSA announcement), and the data corrections made since; ending with the marker naming the
    publication."""
    urls = announcements(pub_id, since)
    rows = []
    for line in changelog.splitlines():
        m = re.match(r"^\| (\[.+\]\((.+)\)) \| (.+?) \| (.+) \|$", line)
        if m and m.group(2) in urls:
            status = re.sub(r"\s*\[\^\d+\]", "", m.group(4)).strip()  # its footnote is the README's, not here
            rows.append(f"- {m.group(1)} ({m.group(3)}): {status}")
    corrections = []
    for para in changelog.split("\n\n"):
        m = re.match(r"^\*\*(\w+) (\d{4}): ", para)
        if m and m.group(1) in MONTHS:
            month = datetime.date(int(m.group(2)), MONTHS[m.group(1)], 1)
            if since is None or month >= since.replace(day=1):
                corrections.append(para.strip())
    parts = [f"Philippine administrative boundaries matched to PSA's PSGC of {label(pub_id)}."]
    parts += ["## PSGC updates in this release", "\n".join(rows) or "None."]
    if corrections:
        parts += ["## Data corrections", "\n\n".join(corrections)]
    parts += [
        "Check the downloads against `SHA256SUMS`. See the README for the columns and the two Level 4 versions.",
        MARKER.format(pub_id),
    ]
    return "\n\n".join(parts) + "\n"


def latest_release() -> tuple[str, str] | None:
    """The latest published quarter's (tag, publication id), or None before the first."""
    rows = json.loads(gh("release", "list", "-R", REPO_SLUG, "--json", "tagName,isLatest").stdout or "[]")
    tag = next((r["tagName"] for r in rows if r["isLatest"] and r["tagName"] != SOURCES_TAG), None)
    if tag is None:
        return None
    body = json.loads(gh("release", "view", tag, "-R", REPO_SLUG, "--json", "body").stdout)["body"]
    m = re.search(MARKER.format(r"([\w-]+)"), body)
    return tag, (m.group(1) if m else "")


def verify_build(dist_dir: Path, release_path: Path) -> dict[str, Path]:
    """A build's assets, once it passes check_dist and, for the current release, its CSVs equal dist/'s."""
    problems = check_dist.check_dir(dist_dir, check_dist.psgc_codes_by_level(release_path))
    if problems:
        raise PublishError("the build fails check_dist:\n" + "\n".join(problems))
    assets = assets_of(dist_dir)
    if Path(release_path).resolve() == CURRENT.resolve():
        for name, path in assets.items():
            committed = REPO / "dist" / path.relative_to(dist_dir)
            if name.endswith(".csv") and (not committed.is_file() or committed.read_bytes() != path.read_bytes()):
                raise PublishError(f"{name} differs from the committed {committed.relative_to(REPO)}")
    return assets


def diff_previous(previous: tuple[str, str] | None, dist_dir: Path) -> list[str] | None:
    """check_dist diff of the latest published release's assets against the build; None if none is published."""
    if previous is None:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        gh("release", "download", previous[0], "-R", REPO_SLUG, "-D", f"{tmp}/assets", "-p", "PH_Adm*")
        return check_dist.diff_dirs(layout(Path(tmp) / "assets", Path(tmp) / "dist"), dist_dir)


def stage_assets(assets: dict[str, Path], stage: Path):
    """Stage the assets by their names (hard links where it can), and their SHA256SUMS."""
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    for name, path in assets.items():
        try:
            os.link(path, stage / name)
        except OSError:
            shutil.copy2(path, stage / name)
    (stage / "SHA256SUMS").write_text("".join(f"{sha256_of(stage / n)}  {n}\n" for n in sorted(assets)))


def prepare(out_dir: Path, release_path: Path, since: str | None, latest: bool, staging=STAGING) -> Path:
    """Check, diff and stage a build; print the summary; return the staging directory. Uploads nothing."""
    dist_dir = Path(out_dir) / "dist"
    pub_id = load_release(release_path, check_paths=False).psgc.publication
    assets = verify_build(dist_dir, release_path)
    previous = latest_release()
    diff = diff_previous(previous, dist_dir)
    stage = Path(staging) / pub_id
    stage_assets(assets, stage)
    since = since if since is not None else (previous[1] if previous else None)
    text = notes((REPO / "CHANGELOG.md").read_text(encoding="utf-8"), pub_id, as_of(since))
    (stage / "notes.md").write_text(text)
    meta = {"publication": pub_id, "release": str(release_path), "latest": latest}
    meta["sha256sums"] = sha256_of(stage / "SHA256SUMS")
    (stage / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"staged {stage}: PSGC {label(pub_id)}, {'latest' if latest else 'not latest'}")
    print("\n".join(f"  {n}  {(stage / n).stat().st_size / 1e6:,.1f} MB" for n in sorted(assets)))
    if diff is None:
        print("no release yet to compare with")
    else:
        print(f"against {previous[0]}: {len(diff)} difference(s)\n" + "\n".join(f"  {d}" for d in diff))
    print("\n" + text)
    print("nothing uploaded: say yes (CONTRACT 3), then `publish_release.py upload --tag <tag>`")
    return stage


def release_exists(tag: str) -> bool:
    """Whether the repo has a release for tag."""
    try:
        gh("release", "view", tag, "-R", REPO_SLUG, "--json", "tagName")
    except PublishError:
        return False
    return True


def remote_has_tag(tag: str) -> bool:
    """Whether the remote (origin) has tag."""
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-remote", "--tags", "origin", f"refs/tags/{tag}"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return bool(out.strip())


def upload(tag: str, pub_id: str, target: str | None, staging=STAGING) -> None:
    """Publish the staged release for pub_id under tag: the exact bytes prepare staged, nothing replaced."""
    stage = Path(staging) / pub_id
    meta = json.loads((stage / "meta.json").read_text())
    if sha256_of(stage / "SHA256SUMS") != meta["sha256sums"]:
        raise PublishError("SHA256SUMS changed since prepare; prepare again")
    for line in (stage / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        if sha256_of(stage / name) != digest:
            raise PublishError(f"{name} changed since prepare; prepare again")
    if target is None and not remote_has_tag(tag):
        raise PublishError(f"no tag {tag} on the remote: push it (/sdlc:publish does), or give --target")
    if not release_exists(tag):
        args = [
            "release",
            "create",
            tag,
            "-R",
            REPO_SLUG,
            "--title",
            f"PSGC {label(pub_id)} ({tag})",
            "--notes-file",
            str(stage / "notes.md"),
            f"--latest={'true' if meta['latest'] else 'false'}",
        ]
        gh(*args, *(["--target", target] if target else []))
    have = set(gh("release", "view", tag, "-R", REPO_SLUG, "--json", "assets", "-q", ".assets[].name").stdout.split())
    names = [line.split("  ", 1)[1] for line in (stage / "SHA256SUMS").read_text().splitlines()]
    for name in names + ["SHA256SUMS"]:
        if name in have:
            print(f"already there  {name}")
            continue
        gh("release", "upload", tag, "-R", REPO_SLUG, str(stage / name))
        print(f"uploaded       {name}")


def main(argv=None) -> int:
    """Run prepare or upload and return an exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("out_dir", type=Path)
    prep.add_argument("--release", type=Path, default=CURRENT)
    prep.add_argument("--since", default=None, help="the publication (or date) the notes start after")
    prep.add_argument("--latest", action="store_true")
    up = sub.add_parser("upload")
    up.add_argument("--tag", required=True)
    up.add_argument("--id", default=None, help="the staged publication (default: the current release's)")
    up.add_argument("--target", default=None, help="create the tag at this commit, if the remote lacks it")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            prepare(args.out_dir, args.release.resolve(), args.since, args.latest)
        else:
            pub_id = args.id or load_release(CURRENT, check_paths=False).psgc.publication
            upload(args.tag, pub_id, args.target)
    except PublishError as e:
        print(f"publish_release: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
