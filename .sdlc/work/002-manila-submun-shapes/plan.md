---
id: 002
slug: manila-submun-shapes
kind: plan
created: 2026-11-07
updated: 2026-11-07
---

# 002 — Give Manila's 14 sub-municipalities the shape of their barangays · plan

## Context

adm4 (`dist/PH_Adm4_BgySubMuns.*`, known and complete) has 14 `SubMun` rows (`1380601000`–`1380614000`)
with no shape, `geom_src = none` and zero measures; issue #1 asks for each to be the dissolve of its
barangays. The spec (`.sdlc/work/002-manila-submun-shapes/spec.md`, R1–R8) settles it: declare the 14 in
`[bgysubmuns] rebuild`, give each the union of its `Bgy` rows (by the barangay's own code's first 7 digits),
`geom_src = dissolved`, measures from the union; `check_dist` asserts each shaped SubMun's area equals its
barangays'. A scratch build of `main` showed Manila's 897 barangays never overlap (union = sum, to the m²).

## Steps

1. **Release file reading** — `src/ph_psgc_shape/release.py`
   - `Bgysubmuns` gains `rebuild: tuple[int, ...] = ()`.
   - `_bgysubmuns` reads `t.take("rebuild", "ints", [])`; fails via `t.fail(t.key("rebuild"), …)` on a
     repeated code, and on a code also in `shapeless` (same idiom as `_municities`' duplicate check).
2. **Match report** — `src/ph_psgc_shape/debug.py`, `matching.py`
   - `report_nulls(..., explained=(), rebuilt=())`: rows with a null `column_name` and a code in `rebuilt`
     print `MATCH REPORT: N PSGC rows are rebuilt from their barangays: [...]` and are dropped before the
     unmatched count, as `explained` rows are. Docstring updated.
   - `matching.report` passes `rebuilt=release.bgysubmuns.rebuild`.
3. **The rebuild** — `src/ph_psgc_shape/levels.py`
   - New `rebuild_submuns(gdf, codes)`: if `codes`, `children = gdf[gdf["geo_level"] == "Bgy"]` with
     `submun_psgc = psgc_code // 1000 * 1000`; call the existing `rebuild(gdf, children, "submun_psgc",
     codes, "name")` (reuses `geometry.rebuild_units` + `add_geometry_measures`); set those rows'
     `geom_src = "dissolved"`; return the frame. Docstring says why the parent is the code, not `adm3_psgc`.
   - In `bgysubmuns`, call it right after `fix_adm4_parents(joined, release)` and before `finish` /
     `approximate`, so complete inherits the shapes. Update `bgysubmuns`' docstring.
4. **check_dist** — `scripts/check_dist.py`
   - `check_submun_areas(name, df)`: for each `SubMun` row with `geom_src != "none"`, sum `area_crs` and
     count the `Bgy` rows with `adm4_psgc // 1000 * 1000 == code`; report when there are no such rows or
     `|area_crs - sum| > count`. Called in `check_dir` (adm4) and `check_complete`.
5. **Release data** — `releases/2026-3q.toml`
   - Add `rebuild = [1380601000, …, 1380614000]` to `[bgysubmuns]` with a comment (union of their
     barangays, after the passes; each barangay's sub-municipality from its own code).
   - Remove the 14 Manila entries from `shapeless`; drop Manila from its comment.
6. **Tests**
   - `tests/test_release.py`: extend `test_rebuilds_merges_shapeless_and_edits_are_read` with a
     `[bgysubmuns] rebuild`; new `test_a_repeated_bgysubmuns_rebuild_code_fails`,
     `test_a_code_both_rebuilt_and_shapeless_fails` (via `fails(path, "bgysubmuns.rebuild", …)`).
   - `tests/test_geometry.py`: `test_a_sub_municipality_is_the_union_of_its_barangays` (two adjoining
     10×10 `Bgy` squares coded under one SubMun, plus a barangay of another: area = 200, `len_crs` 60 <
     80, `geom_src` dissolved, the other barangay excluded); `test_a_sub_municipality_without_barangays_fails`
     and `test_a_rebuild_code_that_isnt_one_row_fails` (`GeometryEditError`);
     `test_rebuilt_rows_are_reported_but_not_counted` (report_nulls, as the shapeless test does).
   - `tests/test_check_dist.py`: `check_submun_areas` on small DataFrames: matching areas pass, an area off
     by more than the barangay count fails, a shaped SubMun with no barangays fails, a `none` SubMun skipped.
7. **Docs**
   - `README.md`: `dissolved` row → "the union of other shapes: barangays PSA has merged, and Manila's 14
     sub-municipalities (the union of their barangays)"; `none` row drops Manila. Under the parents list's
     Manila bullet (or after the `geom_src` table): sub-municipalities overlap their barangays within adm4, so
     area totals filter `geo_level == "Bgy"`; North Cemetery and Tutuban Mall belong to no sub-municipality,
     leaving notches between Tondo, Binondo and Santa Cruz.
   - `CHANGELOG.md` Data corrections, newest first: `**November 2026: Manila's sub-municipalities have
     shapes.** …` (14 rows, `none` → `dissolved`, measures from the union, the overlap note; closes #1).
   - `CLAUDE.md`: corrections list gains `[bgysubmuns] rebuild`; `shapeless` bullet drops Manila;
     flow step 4 mentions the rebuild after `fix_adm4_parents`.
8. **Regenerate `dist/`** — behind CONTRACT 3: run `commands.build` into a temp dir, show the diff (expected:
   the 14 rows in known and complete, nothing else), ask a literal yes/no, then copy only
   `PH_Adm4_BgySubMuns.csv` into `dist/` and `dist/complete/`.

## Verification

- Gate: `uv run --no-sync pytest && uv run --no-sync black --check src scripts && uv run --no-sync flake8 src
  scripts && uv run --no-sync pylint src scripts` (includes the no-PSGC-literal test).
- Build: `uv run --no-sync python scripts/regenerate.py <tmp>`: adm4's last report reads "14 PSGC rows are
  rebuilt…" and "All rows matched!"; `check_dist.py check <tmp>/dist` → 0 problems; `check_dist.py diff dist
  <tmp>/dist` → only the 14 SubMun rows (geom_src, len_crs, area_crs, len_km, area_km2) in known and complete.
  Spot-check Tondo I/II `area_crs` 10,919,396 and Santa Ana 3,383,488 (±14/±99).
- After the copy (step 8): `check_dist.py check dist --csv-only` → 0 problems; `uv run --no-sync pytest -m
  integration` passes.
- Save this plan as `.sdlc/work/002-manila-submun-shapes/plan.md` before building.
