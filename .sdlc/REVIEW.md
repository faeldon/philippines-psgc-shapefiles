# Review

> This repo's additions to the review guide, which `/sdlc:ship` reads with this file
> (`docs.review.guide` in `sdlc.py config`). Each block here, a heading or a `- **lead**` bullet,
> stands in for the guide's block of the same heading path, or lead, when it holds text of its
> own, and is read after its parent's block there when the guide has none like it. A heading with
> nothing under it only places what follows.

## Pass 1 — Correctness

### The ways this repo's code fails

The ways this repo's pipeline has failed, or is built to fail quietly:

- **A join that drops or nulls rows.** A left join on PSGC code, old code (`corr_code`) or name
  that misses leaves a null name rather than an error. Every pass the diff touches should still
  end in a `report_nulls` match report, and the change's notes should show "All rows matched!"
  or explain each unmatched row.
- **An override that moves more than it means to.** A release file's overrides (applied by
  `update_municities_psgc_code` and `update_bgysubmuns_psgc_code`, in file order) rewrite every
  row whose `psgc_code` equals the old code, and
  derive the parent `adm2_pcode`/`adm3_pcode` from the new one unless told otherwise. A new or
  changed override line: does the old code match exactly the intended rows, is the derived parent
  right (NCR cities go to districts, Davao City to Davao del Sur), and does a later override undo
  or re-apply it?
- **Codes changed, geometry not.** A merge or transfer applied to the attribute table but not
  dissolved in the geometry (or the reverse): counts look right over wrong boundaries.
- **A level that wasn't regenerated.** The CLI builds municities only unless `--levels` names
  more. A change to shared lookups that rebuilds one level leaves the others stale
  and their parent codes out of step.
- **Code types and grain.** PSGC codes are ints from `convert_adm_pcode`; a string or float code,
  a duplicated code, or a parent code missing from the level above breaks consumers' joins
  (CONTRACT 2).
- **Source data edited in place.** Any diff under `data/<year>/` or `data/psgc/`, or an existing
  `data/edit/<date>/` folder overwritten, breaks CONTRACT 1.
- **Path casing.** A path that matches the folder on disk only on macOS's case-insensitive
  filesystem (`ProvDists` vs `Provdists`).
