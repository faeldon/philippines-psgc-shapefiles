---
id: 002
slug: manila-submun-shapes
kind: spec
created: 2026-11-07
updated: 2026-11-07
---

# 002 — Give Manila's 14 sub-municipalities the shape of their barangays · spec

> Tier 2 only. Reads from intent.md; read by plan.md. If you can't write a testable requirement
> list, the intent isn't understood yet — go back to Stage 1 rather than designing around the fog.

## Requirements

1. `releases/2026-3q.toml` gains `[bgysubmuns] rebuild` listing `1380601000`–`1380614000`, and
   those 14 leave `shapeless` (its other entries stay). `release.load_release` reads `rebuild` as
   ints (default `()`) and raises `ReleaseError`, naming the file and key, for a repeated rebuild
   code or a code in both `rebuild` and `shapeless`. Tests cover the parse and both errors.
2. In adm4 (known), each rebuild code's shape is the union of the shapes of the `Bgy` rows whose
   `psgc_code // 1000 * 1000` equals it; its `geom_src` is `dissolved`; its `len_crs`,
   `area_crs`, `len_km` and `area_km2` come from `add_geometry_measures` on that union. A fixture
   test with two adjoining square barangays asserts the parent's area is their sum and its
   perimeter less than their sum.
3. A rebuild code that isn't exactly one row, or has no barangay with a shape, raises
   `GeometryEditError` (`geometry.rebuild_units`, reused); a test covers each.
4. The rebuild runs after `fix_adm4_parents` and before `approximate`, so known and complete
   carry the same 14 shapes, and `check_dist`'s complete-differs-only-in-`approximated` check
   still passes.
5. The match report lists the rebuild codes apart from the shapeless ones (they have no source
   shape and get one after the join), on their own line: "N PSGC rows are rebuilt from their
   barangays: […]". An adm4 run still ends "MATCH REPORT: All rows matched!".
6. `check_dist` checks, in known and complete, that each `SubMun` row with a shape has `area_crs`
   within one m² per barangay (each is an int) of the sum of `area_crs` over the `Bgy` rows
   sharing its first 7 digits. A `SubMun` row with `geom_src = none` is skipped. A `check_dist`
   test asserts a mismatched area is reported and the real figures pass.
7. On the regenerated `dist/`: `check_dist.py check` reports 0 problems; `check_dist.py diff dist
   <out>/dist` lists exactly the 14 `SubMun` rows changed, in known and complete, in `geom_src`
   (`none` → `dissolved`) and the four measures; adm0–3 are unchanged. Each row's `area_crs`
   equals the sum measured on the 2026-11-07 build (e.g. Tondo I/II 10,919,396; Santa Ana
   3,383,488), and their adm4 zip features are non-null.
8. Docs: `README.md`'s `geom_src` table widens `dissolved` to "the union of other shapes:
   barangays PSA has merged, and Manila's 14 sub-municipalities (the union of their barangays)",
   and its `none` row drops Manila. The README adds that sub-municipalities overlap their own
   barangays within adm4 (so an area total filters on `geo_level == "Bgy"`), and that North
   Cemetery and Tutuban Mall belong to no sub-municipality, leaving notches between Tondo,
   Binondo and Santa Cruz. `CHANGELOG.md`'s Data corrections gains a `**November 2026: …**`
   paragraph, which `publish_release.notes` carries into the next release's notes. CLAUDE.md's
   corrections list gains `[bgysubmuns] rebuild`, and its `shapeless` line drops Manila. The
   release file's `shapeless` comment drops Manila; `geometry.GEOM_SOURCES`'s comment ("the union
   of other shapes") stays true as written.

## Design

- **`release.py`**: `Bgysubmuns` gains `rebuild: tuple[int, ...] = ()`, read with
  `t.take("rebuild", "ints", [])` as `[municities]` does; the repeat and both-lists checks sit
  with the existing repeat checks.
- **`levels.bgysubmuns`**: after `fix_adm4_parents`, if `corrections.rebuild` is set, build
  `children` as the joined frame's `Bgy` rows with a computed parent column
  `submun_psgc = psgc_code // 1000 * 1000`, and call the existing
  `levels.rebuild(joined, children, "submun_psgc", corrections.rebuild, "name")`, which runs
  `rebuild_units` and re-measures (`name` is already set, so its new-unit naming does nothing).
  Then set those rows' `geom_src = "dissolved"`. `approximate` copies `joined` afterwards, so
  complete inherits the shapes. The parent comes from the barangay's own code, not `adm3_psgc`,
  because `fix_adm4_parents` deliberately puts Manila's barangays under the City (`1380600000`).
- **`matching.report` / `debug.report_nulls`**: a `rebuilt` collection beside `explained`; its
  rows are printed on their own line and not counted as unmatched, as shapeless ones are.
- **`check_dist.py`**: `check_submun_areas(name, df)`, called from `check_dir` for adm4 and from
  `check_complete`; CSV-only, so CI runs it.
- **What the data holds** (scratch adm4 built from `main` on 2026-11-07): Manila's 897
  barangays all have shapes and never overlap (union area = sum, to the m², for all 14). Paco's
  union has one hole, Barangay 808 of Santa Ana (an exclave); Pandacan and Santa Ana are two parts
  each: the barangays' own geometry, kept. North Cemetery (`1303901906`) and Tutuban Mall
  (`1303901907`) overlap no barangay and sit on the Tondo/Santa Cruz and Tondo/Binondo borders.

## Contracts touched

- **CONTRACT 1**: nothing under `data/` is touched; the correction is in the release file, one of
  the two places corrections go.
- **CONTRACT 2**: codes, row count and parents unchanged; "All rows matched!" still printed (R5);
  `none` still means exactly "no shape" (the 14 rows leave `none` as they gain a shape); known
  never `approximated`; complete differs from known only in `approximated` rows (R4). New: a
  shaped `SubMun` row's area matches its barangays' (R6).
- **CONTRACT 3**: regenerating `dist/`'s adm4 CSVs (known and complete) gets its own yes/no at
  build time, with R7's expected diff. v1.0.0 (3Q 2026) is published and not replaced: the shapes
  reach release users with the next release, and `dist/`'s CSV readers when this lands on `main`.
- **Always Tier 2**: no column, name or type changes, but the meaning of `dissolved` widens and
  `none` covers less; the README and CHANGELOG say so (R8). No source row's code mapping changes.

## Alternatives rejected

- **Summing the barangays' measures** (issue #1's wording): right for area, wrong for perimeter,
  which would count every shared inner border (2–3× too long). Measuring the union is right for
  both.
- **A new `geom_src` value, `rebuilt`**: a sixth value in a published column for 14 rows; the
  `geo_level == "SubMun"` filter already tells them apart for area totals.
- **Deriving the rebuild from `geo_level`**: nothing in the release file would say it happens, and
  a future `SubMun` row would change unreviewed.
- **Counting North Cemetery and Tutuban Mall into a sub-municipality**: no source places them
  (Tutuban is "claimed by five barangays of Tondo"; the cemetery borders Tondo and Santa Cruz).
  Assigning either would invent a boundary.
- **Dropping the 14 `SubMun` rows**: breaks one-row-per-PSGC-code (CONTRACT 2) and users' joins.
- **Rebuilding in `matching` or before the join**: the barangays' final codes and shapes exist
  only after the passes and `fix_adm4_parents`.

## Verification

- Gate: `uv run --no-sync pytest && uv run --no-sync black --check src scripts && uv run --no-sync
  flake8 src scripts && uv run --no-sync pylint src scripts`: the new tests for R1–R3 and R6, and
  the existing no-PSGC-literal test.
- Build: `regenerate.py <tmp>` ends adm4 with "All rows matched!" and the rebuilt line;
  `check_dist.py check <tmp>/dist` → 0 problems; `check_dist.py diff dist <tmp>/dist` → exactly
  the 14 rows in known and complete, nothing at adm0–3.
- Then, behind CONTRACT 3's yes/no, the adm4 CSVs copied into `dist/` and `dist/complete/`;
  `check_dist.py check dist --csv-only` → 0 problems, and `pytest -m integration` passes.
