# Ideas

> Seeds, not a backlog: what someone thought worth doing, before anyone decided to. Each one is a
> `## [YYYY-MM-DD] [seed] <title>` heading, then a few lines on why and where it came from.
> `/sdlc:intent` promotes a seed into a change and tags it `[building]`; that change's commit
> deletes the entry, and history keeps it.

## [2026-10-24] [seed] pylint's overgeneral-exceptions setting is silently ignored

`[tool.pylint.'EXCEPTIONS'] overgeneral-exceptions = ["BaseException", "Exception"]` isn't a valid
value in pylint 3 (it wants `builtins.Exception`), so pylint warns on every run and never checks
broad excepts. Fixing the value turns on W0718 for the `except Exception` blocks in
`geo_utils.read_excel_file` and `read_shapefile`, which print and return None. Narrowing them
changes error handling, so it's its own change. Found while building 091. 092 showed the cost:
`read_shapefile`'s broad except hid a broken install (geopandas 0.14 on fiona 1.10) behind a
`NoneType` error several lines later.

## [2026-10-24] [seed] adm0 is one row per island, not one per country

`dist/PH_Adm0_Country.*` has 3640 rows, one per polygon of the singlepart country shapefile
(`phl_admbnda_adm0_singlepart_psa_namria_20231106.shp`), and no PSGC column, so CONTRACT 2's "one
row per PSGC code" doesn't hold for it. 092's `check_dist.py` accepts it as a named exception.
Dissolving to one multipolygon row changes a published output (Tier 2, CONTRACT 3). Related, from
the same change: `area_km2` is a float at every level (`area_crs // 1e6`), which CLAUDE.md now says.

## [2026-10-24] [seed] adm4's 14 Manila sub-municipality rows have no shape

`dist/PH_Adm4_BgySubMuns.*` has 14 `SubMun` rows (`1380601000`–`1380614000`, Tondo I/II to Santa Ana) with a
null geometry and `len_crs`/`area_crs` 0; their barangays hold the area, so a GIS shows 14 empty features.
099 documented them: `geom_src = none` and the README's `geom_src` table say why, and
`releases/2026-3q.toml` declares them `shapeless`. What's left is the option of giving each one the dissolve
of its barangays (a rebuild, like 099's `[municities] rebuild`, but within adm4), so a GIS draws them. That
changes a published output (Tier 2). Found while building 093; see work/093-dist-zip-layers/notes.md in 093's commit (in altcoder/philippines-psgc-shapefiles).

## [2026-10-24] [seed] A 2022 Changelogs row links the wrong PSA page

The `CHANGELOG.md` row "First Quarter 2022 PSGC Updates: Correction of the Names of Five Barangays"
(April 29, 2022) links `psa.gov.ph/classification/psgc/node/167762`, which PSA's listing now titles
"Second Quarter 2022 PSGC Updates: Correction of the Names of One Municipality and 26 Barangays".
Either the link or the row is wrong, and 2Q 2022 may be missing from the table. Found while reading
PSA's listing for 094.

## [2026-10-24] [seed] Review the questionable overrides in releases/2023-4q.toml

Copied from script.py as they were by 096, which couldn't change outputs, and copied again into
`releases/2026-3q.toml` by 099, which publishes from it. Tacloban moves 831600000 → 803747000 and
later 803747000 → 831600000 (net nothing unless the source also holds 803747000), and Angeles is
overridden from both 305401000 and 302401000: check each is intended. The bgysubmuns list also
repeats Kulimpang (1908702012) and Mataya (1908702017); removing the repeats changes no output. Any
change to an override is Tier 2. See work/096-modular-pipeline/notes.md in 096's commit (in altcoder/philippines-psgc-shapefiles).

## [2026-10-25] [seed] Recheck the past year's PSA files whenever a new quarter is downloaded

PSA can replace a file it has already published without changing its name or saying so. While
building 098, the 4Q 2023 datafile on PSA's announcement page turned out to be 3,882,190 bytes
against the 3,864,207-byte copy this repo committed earlier; the other 13 datafiles matched. So
when a new quarter is downloaded, also re-fetch the previous year or so of publications and compare
each with the SHA-256 in its `data/psgc/<id>/manifest.toml`, and report any that changed. Only the
newest quarter has to be processed; re-extracting or re-diffing a replaced historical file is
optional work, decided case by case. Raised by the originator during 098.

## [2026-10-25] [seed] Check a transfer's claimed new parent in the PSGC diff

`psgc_diff`'s transfer rule checks that the old code left and the new code arrived, not that the
unit now sits under the parent the claim names ("Transferred barangay … Municipality of Kapalawan").
A transfer that keeps its code, like April 2024's 63 BARMM barangays, is only checked for being in
both publications. Parsing the claim's parent from its name text, or from Mother Unit, and comparing
it with the code's adm3/adm2 prefix would close the gap. See `work/098-psgc-quarter-diff/notes.md`
in 098's commit (in altcoder/philippines-psgc-shapefiles).
