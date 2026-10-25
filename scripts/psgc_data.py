#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""Extract, check and diff PSA's PSGC publications under data/psgc/ (run from anywhere; paths are the repo's).

    python scripts/psgc_data.py extract (<id> ... | --all)
    python scripts/psgc_data.py check
    python scripts/psgc_data.py diff <old_id> <new_id>

extract writes data/psgc/<id>/'s CSVs from data/psgc/raw/<id>/, after checking each raw file's SHA-256
against the manifest. check re-extracts every publication whose raw files are present and exits 1 if
any committed file differs. diff writes data/psgc/<new_id>/diff-from-<old_id>.md and .csv.
"""
from __future__ import annotations

import argparse
import contextlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

# pylint: disable-next=wrong-import-position
from ph_psgc_shape import psgc_data, psgc_diff  # noqa: E402


def main(argv=None) -> int:
    """Run extract, check or diff and return an exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract")
    extract.add_argument("ids", nargs="*")
    extract.add_argument("--all", action="store_true")
    sub.add_parser("check")
    diff = sub.add_parser("diff")
    diff.add_argument("old")
    diff.add_argument("new")
    args = parser.parse_args(argv)

    with contextlib.chdir(REPO):
        if args.command == "extract":
            ids = psgc_data.publications() if args.all else args.ids
            if not ids:
                parser.error("extract needs publication ids or --all")
            for pub_id in ids:
                psgc_data.extract(psgc_data.load_manifest(pub_id))
                print(f"psgc_data extract: wrote data/psgc/{pub_id}/")
            return 0
        if args.command == "check":
            problems, skipped = psgc_data.check()
            for problem in problems:
                print(problem)
            if skipped:
                print(f"psgc_data check: skipped (no raw files): {', '.join(skipped)}")
            print(f"psgc_data check: {len(problems)} problem(s)")
            return 1 if problems else 0
        written = psgc_diff.diff(args.old, args.new)
        for path in written:
            print(f"psgc_data diff: wrote {path}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
