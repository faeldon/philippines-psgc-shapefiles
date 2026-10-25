#   ---------------------------------------------------------------------------------
#   Copyright (c) James Faeldon. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------
"""CONTRACT 2 over the committed dist/ CSVs and the PSA datafile: what users download, not fixtures.

Marked integration because it reads the published files, so plain `pytest` skips it and CI's
`-m integration` job runs it. CI's checkout has no git-lfs, so the zips are pointer files there: this
checks the CSVs alone (zips=False). `check_dist.py check dist`, and the build check, cover the zips.
"""
from __future__ import annotations

import pytest

import check_dist

pytestmark = pytest.mark.integration


def test_published_csvs_meet_contract_2():
    psgc_codes = check_dist.psgc_codes_by_level(check_dist.RELEASE)
    problems = check_dist.check_dir(check_dist.REPO / "dist", psgc_codes, zips=False)
    assert not problems, "\n".join(problems)
