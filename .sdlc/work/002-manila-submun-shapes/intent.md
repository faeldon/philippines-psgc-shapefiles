---
id: 002
slug: manila-submun-shapes
tier: 2
impact: minor
stage: shipped
created: 2026-11-07
updated: 2026-11-07
shipped: 2026-11-07
idea: 2026-10-24-3
depends_on:
closes: [1]
serves: [O1]
---

# 002 — Give Manila's 14 sub-municipalities the shape of their barangays

> Stage 1: why this change is worth making, in its originator's words. Read by `/sdlc:spec` at
> Tier 2, or by plan mode at Tier 1; `/sdlc:status` counts the open questions not yet struck.

## Problem

`dist/PH_Adm4_BgySubMuns.*` (and `dist/complete/`) has 14 `SubMun` rows, `1380601000` (Tondo I/II)
to `1380614000` (Santa Ana), with no geometry, `geom_src = none`, and `len_crs`, `area_crs`,
`len_km`, `area_km2` all 0. Their barangays hold the area, so a GIS that opens adm4 shows 14 empty
features, and a user joining PSA figures on a sub-municipality's code gets a row with nothing to
draw and an area of 0. 099 documented the gap (`releases/2026-3q.toml:322-335` declares them
`shapeless`; `README.md:73` says why) but didn't fill it. Recorded as inbox entry 2026-10-24-3
while building 093, and asked for by a user in issue #1: dissolve the child barangays' geometry and
give each sub-municipality the resulting measures.

## Outcome

- In both distributions, each of the 14 `SubMun` rows has a shape: the union of its barangays'
  shapes from the same run, with `len_crs`, `area_crs`, `len_km`, `area_km2` measured from that
  shape (not summed: a summed perimeter would count the barangays' shared inner borders).
- Each sub-municipality's `area_crs` equals the sum of its barangays' `area_crs` within rounding,
  asserted by a test or `check_dist`.
- The 14 codes leave the release's `shapeless` list; the match report no longer lists them apart.
- `check_dist.py check` on the regenerated adm4 reports 0 problems, and `check_dist.py diff dist
  <out>/dist` shows exactly these 14 rows changed in each distribution, nothing else.
- **Moves O1:** a user joining adm4 by PSGC code gets a drawable shape and real measures for every
  Manila sub-municipality, not 14 empty features with area 0; issue #1 closes.

## Affected

- **Area:** the adm4 (`bgysubmuns`) level of the pipeline and the release file.
- **Files & components:** `src/ph_psgc_shape/levels.py`, `geometry.py` (`rebuild_units` or an
  adm4-internal counterpart), `release.py` (if a new release key), `releases/2026-3q.toml`
  (`shapeless`, possibly a rebuild key), `scripts/check_dist.py` (the `geom_src` rule for these
  rows), tests, `README.md`'s `geom_src` table, `CHANGELOG.md`'s data corrections, and the
  regenerated adm4 CSVs in `dist/` and `dist/complete/`. **Levels regenerated:** adm4 only (known
  and complete); adm0–3 unchanged.
- **Downstream:** everyone who downloads `PH_Adm4_BgySubMuns` from a release or reads its CSVs in
  `dist/`. Sub-municipalities and their barangays will overlap within adm4, so a user summing
  `area_km2` over all of adm4 would count central Manila twice (~42 km²) unless they filter on
  `geo_level` or `geom_src`.
- **Contracts:** CONTRACT 2 (one row per code; adm4's `geom_src` rules: "no shape exactly when
  `none`" still holds, and complete still differs from known only in `approximated` rows), CONTRACT
  3 (regenerating `dist/` needs its yes/no), and the always-Tier-2 rule on an output column's
  meaning if `geom_src` gains a value or a value's meaning widens.

## Constraints

- adm4's codes, row count, columns and their types stay the same; only these 14 rows' geometry,
  measures and `geom_src` change. No barangay's shape or measures change.
- The shape comes from the same run's barangays, after merges, plotted splits and
  `fix_adm4_parents`, so parent and children can't drift; none of Manila's barangays is
  approximated, so known and complete get the same 14 shapes.
- No PSGC code literal in the package: which units are rebuilt comes from the release file or from
  `geo_level`, never from code.
- adm4 still ends with "MATCH REPORT: All rows matched!", now without the 14 Manila codes explained
  as shapeless.

## Open questions

- ~~Which `geom_src` do the 14 rows carry: reuse `dissolved` (today: barangays PSA merged), or a
  new value such as `rebuilt`?~~ Resolved: `dissolved`, whose README meaning widens to "the union
  of other shapes" (spec R2, R8).
- ~~Is the rebuild declared in the release file (a `[bgysubmuns] rebuild`, like `[municities]
  rebuild`), or derived from `geo_level == "SubMun"` and each barangay's code?~~ Resolved: declared
  as `[bgysubmuns] rebuild`; each barangay's sub-municipality comes from its own code's first 7
  digits (spec R1, R2).
- ~~Should the README warn that sub-municipalities overlap their barangays within adm4, so area
  sums should filter on `geo_level`?~~ Resolved: yes, with the notches North Cemetery and Tutuban
  Mall leave (spec R8).
- ~~Is the shapefile change worth a line in the next release's notes, or is a CHANGELOG data
  correction enough?~~ Resolved: the CHANGELOG data correction is enough;
  `publish_release.notes` carries it into the next release's notes (spec R8).
