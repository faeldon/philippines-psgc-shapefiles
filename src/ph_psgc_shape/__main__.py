#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Build dist/ levels from a release file, writing dist/ under the working directory.

    python -m ph_psgc_shape releases/2023-4q.toml [--levels country region provdists municities bgysubmuns]
"""
from __future__ import annotations

import argparse
import sys

from .pipeline import LEVELS, run
from .release import ReleaseError, load_release


def main(argv=None) -> int:
    """Run the release's levels (municities only by default) and return an exit code."""
    parser = argparse.ArgumentParser(prog="python -m ph_psgc_shape", description=__doc__.splitlines()[0])
    parser.add_argument("release", help="release file, e.g. releases/2023-4q.toml")
    parser.add_argument("--levels", nargs="+", default=["municities"], choices=list(LEVELS))
    args = parser.parse_args(argv)
    try:
        release = load_release(args.release)
    except ReleaseError as e:
        print(f"ph_psgc_shape: {e}", file=sys.stderr)
        return 2
    run(release, levels=tuple(args.levels))
    return 0


if __name__ == "__main__":
    sys.exit(main())
