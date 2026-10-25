# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A data project, not a library. It publishes Philippine administrative-boundary shapefiles (levels 0–4) whose codes and names are matched to the PSA's latest PSGC publication. The deliverables are each PSGC quarter's GitHub release (`PH_Adm{0-4}_*.shp.zip`, a geometry-free `.csv` of each, and `SHA256SUMS`), and the latest quarter's CSVs in `dist/`. The Python code in `src/ph_psgc_shape/` is the pipeline that produces them.

Nothing is stored in git-lfs. This repository started on 2026-10-25 from the tree of [altcoder/philippines-psgc-shapefiles](https://github.com/altcoder/philippines-psgc-shapefiles) (archived), which holds the history before it: changes 001–101 and their `work/` folders, and the git-lfs files they used. Files too big for git live in GitHub releases: the published zips in each quarter's release, and the raw sources in the `sources` release, which `data/sources.toml` lists with their SHA-256 and `scripts/sources.py fetch` puts in place (gitignored).

## Why the process is heavier than the code looks

**This pipeline fails plausibly, not loudly.** A left join that misses a barangay leaves a null name, not an exception. A wrong manual code override moves a city into the wrong province, and the map still renders. A merge applied to the codes but not to the geometry gives correct-looking counts over wrong boundaries. Nobody gets an error. A downstream user gets a wrong map and trusts it, because these files are published and joined by PSGC code.

The CONTRACTs below put a checkable claim between a change and the people using `dist/`.

## Changing this repo

Changes are sized by tier:

- **Tier 0** (a typo, a comment, README wording): just make the change.
- **Tier 1** (a single name correction, a debug or utility tweak): a short `intent.md` saying what changes and how it will be verified.
- **Tier 2** (a quarterly PSGC update, a geometry edit, a new source year, any change to output columns or code-assignment logic): also a `spec.md` and a `plan.md` before code.

Two things are **always Tier 2, however small the diff**:
- **Changing which source row maps to which PSGC code.** One override line in a release file (`releases/<id>.toml`) silently changes every join a consumer makes on that code.
- **Changing an output's columns, names, or types.** People's joins and dashboards read these files directly.

Change folders go under `work/NNN-slug/`. Each one is committed on the change's own branch with the code it describes, and `/sdlc:close` removes it from `main` in a commit of its own, so history keeps it and `main` doesn't. When a change ships, carry what lasts into the commit message, `CHANGELOG.md`, or this file. Each change is worked in its own branch, in a worktree under `.claude/worktrees/NNN-slug`, using the `sdlc` plugin (`/sdlc:status`, `/sdlc:intent`, `/sdlc:spec`, plan mode, `/sdlc:ship`, `/sdlc:close`, `/sdlc:health`). The process is in `.sdlc/SDLC.md`.

Commits and pull requests carry no AI attribution lines: no `Co-Authored-By` naming Claude, no `Claude-Session` link, no "Generated with Claude Code". The README's "AI assistance" section is the disclosure for the whole repository, and `.claude/settings.json` turns the attribution off (`attribution`). The sdlc plugin's `Sdlc-*` trailers stay.

## The CONTRACTs

### Source data is the input of record — CONTRACT 1

Raw downloads under `data/<year>/` and `data/psgc/raw/` are **never edited**: they are exactly what OCHA/HDX and PSA published. For PSA's files, the input of record is the committed extract under `data/psgc/<id>/`, which `scripts/psgc_data.py check` proves equal to the raw files its `manifest.toml` names by SHA-256. `data/psgc/raw/` is gitignored, so new quarters don't add PSA's Excel files to git, and a clean clone still rebuilds everything from the extracts. The boundary sources (`data/2011`, `data/2015`, `data/2023`, and the shapefile edit `data/edit/20240210`) are gitignored too: their input of record is `data/sources.toml`'s SHA-256s, and `scripts/sources.py check` proves the fetched files equal to them. Corrections go in one of two places, where they are visible and reviewable:
- the **release file** (`releases/<id>.toml`: code overrides, renames and special cases), or
- a **new dated folder** under `data/edit/<date>/` for geometry edits. An existing edit folder is never overwritten; a newer edit gets a new date. Small text inputs (TOML, GeoJSON) are committed; a shapefile edit too big for git goes in the `sources` release, with its entries added to `data/sources.toml` (`sources.py manifest`, then `upload`, behind CONTRACT 3).

### Every output declares its grain — CONTRACT 2

**The most important rule here.** Each `dist/PH_AdmN_*` file has **one row per PSGC code at that level**. A change is not done until, for every level it regenerates:
- the run prints "MATCH REPORT: All rows matched!" (or every remaining unmatched row is explained in the change's notes, or is one of the release's `bgysubmuns.shapeless` codes, which the report lists apart);
- the level's PSGC code is unique and not null;
- every parent code (`adm1_psgc`, `adm2_psgc`, …) exists in the level above;
- the row count equals the PSGC table's count for that level's `geo_level` values, or the difference is explained (special cases like the NCR districts and City of Isabela are handled by hand in the release file);
- adm4's `geom_src` says where each shape came from (`source`, `dissolved`, `plotted`, `approximated`, `none`): a row has no shape exactly when it's `none`, `dist/` (the **known** distribution) never has `approximated`, and `dist/complete/PH_Adm4_BgySubMuns.*` (**complete**, published as `PH_Adm4_BgySubMuns_complete.*`) has known's rows, codes and columns and differs from it only in rows it marks `approximated`. adm0–3 are the same for both, so complete has adm4 only.

### Confirm before you overwrite published files — CONTRACT 3

Users download each quarter's GitHub release, and `dist/`'s CSVs. Before regenerating or replacing anything in `dist/`, publishing a release or adding to one (`publish_release.py upload`), or uploading to the `sources` release (`sources.py upload --yes`):
1. say what will be written or sent and what is expected to change (levels, row counts, codes affected; for a release, the assets and `publish_release.py prepare`'s summary);
2. ask a literal yes/no question;
3. **wait** for the answer, and only then run.

Approval covers that one run, never the next. A published release isn't replaced: a mistake is fixed by the next release.

## Commands

```bash
pip install -e ".[test]"                      # Python 3.12; deps pinned exactly (numpy 2.5, pandas 3.1, geopandas 1.2)

# The raw boundary sources (not in git): assets of the `sources` release, listed with their SHA-256 in data/sources.toml.
python scripts/sources.py fetch                # put each in place: hard-linked from the main checkout when it has it, else downloaded (gh)
python scripts/sources.py check                # the files present against data/sources.toml; 1 on a difference
python scripts/sources.py manifest             # rewrite data/sources.toml from the files on disk (a new source), then:
python scripts/sources.py upload --target SHA  # what would go to the `sources` release; --yes sends it (CONTRACT 3)

# Regenerate into a scratch dir, never dist/ (refuses a dir inside the repo); --levels picks levels.
python scripts/regenerate.py /tmp/out          # all five levels of releases/2026-3q.toml (--release picks another), and adm4's complete in /tmp/out/dist/complete/; ~4 minutes, needs the fetched sources
python scripts/check_dist.py check /tmp/out/dist   # against the same release's PSGC table (--release); CONTRACT 2 (grain, parents, counts vs the PSGC table, geom_src), trimmed names, each zip: one EPSG:32651 layer named for its level, attributes equal to its CSV; and complete/ against known
python scripts/check_dist.py check dist --csv-only     # the committed dist/: its CSVs alone (the zips are release assets)
python scripts/check_dist.py diff dist /tmp/out/dist   # every difference from the committed CSVs, complete/ included; zip geometry (1 mm) only when both sides have zips

# The split geometry in data/edit/20261025/ (see each .toml's header). Each writes its .geojson and a -report.md; 1 if a check fails.
python scripts/plot_traverse.py data/edit/20261025       # plot traverses.toml's laws, check closure and area (1%), fit and clip to their mothers
python scripts/approximate_split.py data/edit/20261025   # cut approximations.toml's barangays to their target areas (1%), for complete only

# PSA's publications under data/psgc/ (run from anywhere). extract needs data/psgc/raw/<id>/; check and diff don't.
python scripts/psgc_data.py extract 2026-3q    # (or --all) checks the raw files' SHA-256, writes data/psgc/<id>/*.csv
python scripts/psgc_data.py check              # re-extracts every publication whose raw files are here; 1 if a committed file differs
python scripts/psgc_data.py diff 2026-2q 2026-3q   # writes data/psgc/2026-3q/diff-from-2026-2q.md and .csv: PSA's claims checked against the data

# Publishing a quarter, from the main checkout after its changes close. Each zip is byte-reproducible (dated the publication's as_of).
python scripts/regenerate.py /tmp/out && python scripts/publish_release.py prepare /tmp/out --latest [--since 2023-4q]
#   checks the build, requires its CSVs equal dist/'s, diffs it against the latest release, stages release-staging/<id>/
#   (assets, SHA256SUMS, notes) and prints the summary for CONTRACT 3's yes/no; uploads nothing. Then /sdlc:release
#   (bumps pyproject.toml's version, tags vX.Y.Z) and /sdlc:publish (pushes, then runs release.publish,
#   `publish_release.py upload --tag {tag}`: the staged bytes exactly, never replacing an asset, safe to rerun).
python scripts/publish_release.py upload --tag psgc-2023-4q --id 2023-4q --target <sha>   # an older quarter, tagged at sha

# The CLI writes dist/ under the working directory (CONTRACT 3), municities only unless --levels names others.
python -m ph_psgc_shape releases/2026-3q.toml [--levels country region provdists municities bgysubmuns]

pytest                                        # excludes `integration` marker by default (see addopts)
pytest -m integration                         # CONTRACT 2 over the committed dist/ CSVs (both distributions), every data/psgc/ publication, and 2026-3q's recodes against PSA's transfers; no raw sources needed (CI's integration job; the edit files' rerun is skipped without them); also checks nothing tracked needs git-lfs
pytest tests/test_levels.py::test_default_runs_municities_only   # single test
black --check src scripts && flake8 src scripts && pylint src scripts   # line length 120
pre-commit run --all-files                    # isort (adds `from __future__ import annotations`), pyupgrade, codespell

# The ship gate, in a uv env. requires-python (>=3.12,<3.13) makes uv pick 3.12, as CI runs; the
# pinned deps don't install on the system Python (3.14). uv.lock is committed: --locked refuses a stale one.
uv sync --extra test --locked
uv run --no-sync pytest && uv run --no-sync black --check src scripts && uv run --no-sync flake8 src scripts && uv run --no-sync pylint src scripts

# No git-lfs is needed.
```

CI (`.github/workflows/build.yml`) delegates to the shared `altcoder/action-python` validation workflow. PR titles must follow Conventional Commits (`check-pr.yml`), e.g. `fix:`, `feat:`, `ci:`.

## Pipeline architecture

`ph_psgc_shape` is a package run with `python -m ph_psgc_shape <release.toml>`. Everything specific to one release lives in its release file, `releases/<id>.toml`, and none of it in the code: the PSGC publication it joins to (`[psgc] publication`, whose manifest gives the datafile's column layout), each level's source shapefile and its columns, and every correction. A test fails if a 9- or 10-digit integer (a PSGC code) appears in the package. Overrides apply in the order the file lists them, because one can move a row onto a code a later one moves again.

A release's corrections, besides the overrides and `city_adm2`:
- `[psgc] names`: typos in PSA's datafile, corrected as the table is read (2026-3q: Lucena).
- `[recode] prefixes`: a province moved to another region. Every source code under the five-digit `from` prefix moves to `to`, at adm2–4, before any override, and its parent pcodes follow (2026-3q: the Negros Island Region and Sulu, 1,849 transfers in five lines). Matching stage 2 recodes the old code it derives from `corr_code` the same way.
- `[region] rebuild`, `[municities] rebuild`: units whose members changed, given the union of their children's shapes from the same run (`geometry.rebuild_units`); every other unit keeps its source shape.
- `[bgysubmuns] merges`: barangays merged into one, dissolved in the source before matching.
- `[edits] plotted` and `approximated`: split GeoJSONs in `data/edit/<date>/`. Plotted daughters are cut from their mothers in the source before matching (both distributions); approximated ones are cut after the join, for complete only.
- `[bgysubmuns] shapeless`: PSGC rows with no shape (Manila's sub-municipalities, and known's unsurveyed new barangays), which the match report lists apart.

Flow:
1. `release.load_release(path)` reads and checks the release file: an unknown or missing key, a code that isn't an int, a repeated municities override or name correction, a recode prefix that isn't five digits, repeats, or lands on another, an override or `city_adm2` code under a recoded prefix (it would never match), or a path that doesn't exist with exactly that casing (checked segment by segment, so macOS fails as Linux would) raises `ReleaseError` naming the file and the key, before anything else is read.
2. `pipeline.run(release, levels=("municities",))` calls `psgc.load_psgc_table(release)`, which reads the release's publication, `data/psgc/<id>/psgc.csv` (PSA's `PSGC` sheet, cell for cell), and names its columns by position as the publication's manifest `[layout]` says (it must name `psgc_code`, `name`, `corr_code` and `geo_level`, the only ones the levels read; `corr_code` is read as a float, as `matching.py` expects). It drops the columns the layout lists and PSA's nameless blank and footnote rows, sets the codes of the NCR district rows that have none (`district_codes`) and appends the rows the datafile lacks (`add_rows`). Anything that doesn't fit raises `PsgcTableError`: a column count that differs, a district name that isn't exactly one row, an added code already present, a row left without a numeric code. `scripts/check_dist.py` counts against the same `load_psgc_table`. It then builds each level named in `levels`, in `LEVELS` order (`country`, `region`, `provdists`, `municities`, `bgysubmuns`), except that a level with rebuilds has the level below built first, and built but not written unless it's named too (`pipeline.build_order`); an unknown name raises before anything is read. So the CLI's municities-only default also builds adm4 for a release that rebuilds municipalities. `scripts/regenerate.py` runs all five.
3. Each level in `levels.py` reads its source shapefile (`read_source`), joins it to the PSGC table, and applies the release's corrections: the recodes, the provdists overrides (City of Isabela, the BARMM interim province), the municities overrides (`overrides.apply_municities_overrides`), `city_adm2`, which gives each city PSA places under no province its NCR district or geographic province, in adm3 and (through `fix_adm4_parents`) for its barangays in adm4, and the rebuilds. It returns its frames keyed by the folder under `dist/` each goes to (`""`, and `"complete"` for adm4's complete). `pipeline.run` writes each with `write_level`: `{out_dir}/{stem}.shp.zip` and `.csv` from one frame, relative to the working directory, trimming whitespace from text columns (a shapefile can't hold trailing spaces); names are trimmed only there, so the matching passes see them untrimmed.
4. Barangays (adm4) take `psgc.barangay_table` (each barangay with its adm3 and adm2). The source, in UTM 51N, gets the recodes, the merges and the plotted splits (`levels.add_daughters`), then runs the passes in `matching.py`, in order: exact code and name, the release's overrides, old code (`corr_code`), municipality name, special geographic areas, then `adm3_en`. `run_passes` prints a stage header before each and a `report_nulls` match report (in `debug.py`) after it. `fix_adm4_parents` then puts Manila's sub-municipalities and their barangays under the City of Manila, gives a row with no source shape its parents from its own code, and names the release's non-barangay source polygons. Complete is that frame with the approximated splits (`levels.approximate`).

Conventions in the outputs:
- PSGC codes use the PSA's 10-digit structure and are stored as **ints**. Source `admN_pcode` strings (prefixed with `PH`) are converted with `convert_adm_pcode(code, zero_suffix)` (in `geo_utils.py`).
- Each level also stores its parent levels' PSGC codes (`adm1_psgc`, `adm2_psgc`, …) so tables can be joined across levels.
- `add_geometry_measures(gdf, epsg_code=32651)` reprojects to UTM 51N and adds `len_crs`, `area_crs` and `len_km` as ints, and `area_km2` as a float (`area_crs // 1e6`).
- adm0 is one row per polygon of the singlepart country shapefile (3640), with no PSGC column.

## Data layout

- `data/<year>/` holds the raw source boundaries, fetched (gitignored) from the `sources` release by `scripts/sources.py` and listed in `data/sources.toml`. 2011 and 2015 are legacy zips. 2023 and 2026 have one folder per level: `Country`, `Regions`, `Provdists`, `Municities`, `BgySubMuns`. 2023 comes from OCHA/HDX (`phl_admbnda_admN_psa_namria_20231106.*`); 2026 (untracked, not used) is OCHA's v03 of May 2026 (`phl_adminN.*`, `valid_on` 2025-02-13, plus `AdminLines`/`AdminPoints`): the same shapes and units as 20231106 in OCHA's new schema, still at the PSGC of 4Q 2023 (see work/099-psgc-2026-3q in its commit, in altcoder/philippines-psgc-shapefiles).
- `data/edit/<date>/` holds geometry edits. `20240210/` is a hand-edited adm4 shapefile (QGIS), a fetched source like `data/2023/`, which the adm4 pipeline reads instead of the raw 2023 BgySubMuns file. `20261025/` holds small inputs read at run time: `traverses.toml` (RA 11986 and RA 11993's technical descriptions, with each correction to the law's text) and `approximations.toml` (the cut rules for the barangays no published boundary describes), and what `scripts/plot_traverse.py` and `scripts/approximate_split.py` make of them (`plotted.geojson`, `approximated.geojson` and their reports; a test reruns both).
- `data/psgc/<id>/` is one PSA publication (`2023-4q` … `2026-3q`; the two off-cycle ones are `2024-04` and `2025-07`), committed: its `manifest.toml` (each raw file's PSA URL and SHA-256, the datafile's sheets and column `[layout]`, and the Summary of Changes `sections` that are this publication's), the extracts `psgc.csv`, `national-summary.csv`, `prov-summary.csv` and `summary-of-changes.csv`, and any `diff-from-<id>.md`/`.csv`. `src/ph_psgc_shape/psgc_data.py` reads and extracts them; `psgc_diff.py` diffs them.
- `data/psgc/raw/<id>/` (gitignored) holds PSA's downloads under PSA's own names: the datafile and the Summary of Changes. PSA's `Summary-of-Changes.xlsx` is a cumulative log since 2001 that PSA rewrites between versions, so each publication's own version is kept and only its own sections extracted. The `National-and-Provincial-Summary.xlsx` isn't downloaded: it's the datafile's `Prov Sum`. PSA's announcement pages are behind Cloudflare, so downloads go through a browser.
- The datafile's layout changes: 13 columns in 4Q 2023, 11 from 1Q 2024 (no 2015 population pair), 12 from 3Q 2026 (a blank first column), and no NCR district rows from 1Q 2024 (their manifests list the four under `add_rows`). PSA has also replaced a published file under the same name: its 4Q 2023 link now serves a different datafile than the one `dist/` was built from (see that manifest's `note`).

## Updating for a new PSGC release

When PSA publishes quarterly changes, the table in `CHANGELOG.md` records each update and its status (✅ / ✅ (NC) / ❌ Pending). Add a row for each new update, and turn rows ✅ along with the regenerated `dist/` CSVs; the quarter reaches users when its release is published (`publish_release.py prepare`, `/sdlc:release`, `/sdlc:publish`). A new quarter starts with its publication: download its datafile and Summary of Changes into `data/psgc/raw/<id>/`, write `data/psgc/<id>/manifest.toml` (copy the latest and edit), run `scripts/psgc_data.py extract <id>`, then `diff <previous> <id>` for the worklist: PSA's claims checked against the data, and every change no claim explains. Its release file starts as a copy of the latest `releases/<id>.toml` under a new id, naming the new publication and edited for the quarter's corrections. When `dist/` moves to a new boundary release, update the README's Sources section.
