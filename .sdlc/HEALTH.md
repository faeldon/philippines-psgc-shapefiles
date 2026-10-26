# Health

> What each finding this repo's scans (`commands.scan`) can report means, and the response tier
> it usually gets: 1 report it, 2 fix it inline, 3 write an intent. `/sdlc:health` reads
> this once per run, routing every finding by the table ahead of its own rules, and the blind
> spots say what a clean scan can't vouch for.

## Findings

The scan is `pytest -m integration`. A finding is a failing (or skipped) test, named as pytest
prints it.

| finding | what it means here | tier | why |
|---|---|---|---|
| `test_dist_contract.py::test_published_csvs_meet_contract_2` fails | a committed `dist/` CSV breaks CONTRACT 2: a null or repeated code, an orphan parent, a count off the PSGC table, a bad `geom_src`, or complete/ differing from known outside its `approximated` rows | 3 | it's what users download and join on; fixing it regenerates `dist/` (Tier 2, CONTRACT 3) |
| `test_release_2026_3q.py::test_every_transfer_is_one_of_the_releases_prefix_moves` fails | a PSA transfer in 2026-3q's Summary of Changes isn't covered by a `[recode] prefixes` line | 3 | which source row maps to which code is always Tier 2 |
| `test_release_2026_3q.py::test_every_recode_moves_something` fails | a recode prefix matches no source code: dead, or a typo in the prefix | 3 | removing or fixing it is a code-assignment change (Tier 2) |
| `test_release_2026_3q.py::test_the_edit_files_are_what_their_scripts_make` fails | a committed `plotted.geojson`/`approximated.geojson` (or its report) differs from what `plot_traverse.py`/`approximate_split.py` now make of the `.toml`s in `data/edit/20261025/` | 3 | a geometry edit, and it changes the shapes in `dist/` (Tier 2) |
| `test_psgc_datafiles.py::test_each_publication_reads_with_its_codes_names_and_levels` or `test_4q_2023_keeps_every_row` fails | a committed `data/psgc/<id>/` extract no longer reads through its manifest's `[layout]` with unique codes, NCR's row and the four NCR district codes, or 4Q 2023 no longer has its 43,762 rows | 3 | the input of record (CONTRACT 1) and every count CONTRACT 2 checks against |
| `test_psgc_datafiles.py::test_the_extracts_match_their_raw_files` fails | a committed extract differs from re-extracting PSA's raw file named by SHA-256 in its manifest | 3 | CONTRACT 1: the extract must equal what PSA published |
| `test_psgc_datafiles.py::test_every_publication_has_a_folder` fails | the folders under `data/psgc/` differ from the test's list of publications: one added without the test, or one missing | 2 when a quarter's change added the folder and the list wasn't updated; 3 when a committed publication is gone | the list is a guard against a lost publication, so a missing one is investigated, not edited away |
| `test_psgc_datafiles.py::test_no_excel_file_is_tracked_under_data_psgc` or `test_raw_downloads_are_ignored` fails | a PSA Excel file is tracked, or `data/psgc/raw/` isn't gitignored | 2 | `git rm --cached` or a `.gitignore` line, with no output changed |
| `test_no_lfs.py::test_no_file_is_stored_through_git_lfs` fails | `.gitattributes` has an LFS rule again | 2 | delete the rule; nothing here needs git-lfs |
| `test_no_lfs.py::test_no_raw_source_or_shapefile_zip_is_tracked` or `test_every_tracked_file_fits_in_plain_git` fails | a raw boundary source, a `dist/*.shp.zip`, or a file over 100 MiB is tracked | 3 | it belongs in the `sources` release or a quarter's release, and an upload is behind CONTRACT 3 |
| `test_no_lfs.py::test_every_source_a_release_reads_is_listed` fails | a `releases/*.toml` reads a source `data/sources.toml` doesn't list, so a clean clone can't fetch it | 3 | listing it means `sources.py manifest` and `upload` (CONTRACT 3) |
| any test **skipped** | the check didn't run: see the blind spots | 1 | a skip is not a pass; say which and why |

## Blind spots

- **The zips.** The scan reads the committed CSVs only. The `.shp.zip`s are release assets, so it
  never checks their geometry, CRS, or that their attributes equal the CSVs. Only the slower check
  (`commands.build`) does, on a fresh build, and `publish_release.py prepare` on what gets uploaded.
- **The raw sources.** `test_the_edit_files_are_what_their_scripts_make` skips when the boundary
  sources aren't fetched (`scripts/sources.py fetch`), and `test_the_extracts_match_their_raw_files`
  skips when `data/psgc/raw/` is empty. CI has neither, so a green CI run vouches for neither.
  Neither is the scan proving the fetched files equal `data/sources.toml`'s SHA-256s: that's
  `scripts/sources.py check`.
- **Datafile history.** `test_the_manifest_hash_is_the_datafile_git_once_held` needs a commit that
  held each datafile. None has in this repository since it restarted on 2026-10-25 (that history is
  in altcoder/philippines-psgc-shapefiles), so it always skips here.
- **Only 2026-3q's recodes.** The transfer checks cover `releases/2026-3q.toml` alone. An older
  release file, or a new quarter's, has no such test until one is written.
- **Not the regeneration.** A clean scan says the committed `dist/` is internally consistent, not
  that the pipeline still produces it. That's `check_dist.py diff` in the slower check.
