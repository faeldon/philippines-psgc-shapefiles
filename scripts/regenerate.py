#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Regenerate the dist/ levels into a scratch directory, never into the repo's dist/.

The pipeline reads the release's data/... paths and writes dist/... relative to the working directory,
so this makes <out_dir>/data a symlink to the repo's data/ and an empty <out_dir>/dist/, then runs from
<out_dir>.

    python scripts/regenerate.py <out_dir> [--release releases/2026-3q.toml] [--levels country region ...]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ALL_LEVELS = ("country", "region", "provdists", "municities", "bgysubmuns")
RELEASE = "releases/2026-3q.toml"


def refusal(out_dir: Path) -> str | None:
    """Say why out_dir can't be used, or None if it can."""
    resolved = out_dir.resolve()
    if resolved == REPO or REPO in resolved.parents:
        return f"{out_dir} is inside the repo; regenerate only into a directory outside it"
    dist = out_dir / "dist"
    if dist.exists() and any(dist.iterdir()):
        return f"{dist} already has files; use an empty or new directory"
    return None


def main(argv=None) -> int:
    """Regenerate the requested levels into out_dir/dist and return an exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--levels", nargs="+", default=list(ALL_LEVELS), choices=ALL_LEVELS)
    parser.add_argument("--release", default=RELEASE, help="release file, relative to the repo")
    args = parser.parse_args(argv)

    reason = refusal(args.out_dir)
    if reason:
        print(f"regenerate: refusing: {reason}", file=sys.stderr)
        return 2

    out_dir = args.out_dir.resolve()
    (out_dir / "dist").mkdir(parents=True, exist_ok=True)
    data = out_dir / "data"
    if not data.exists():
        data.symlink_to(REPO / "data", target_is_directory=True)

    release_path = (REPO / args.release).resolve()
    sys.path.insert(0, str(REPO / "src"))
    os.chdir(out_dir)
    # pylint: disable-next=import-outside-toplevel
    from ph_psgc_shape import pipeline, release

    pipeline.run(release.load_release(release_path), levels=tuple(args.levels))
    print(f"regenerate: wrote {', '.join(args.levels)} to {out_dir / 'dist'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
