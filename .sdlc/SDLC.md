# Process

> This repo's answers to the process guide, which the skills read with this file
> (`docs.process.guide` in `sdlc.py config`). Each block here, a heading or a `- **lead**`
> bullet, stands in for the guide's block of the same heading path, or lead, when it holds text of
> its own, and is read after its parent's block there when the guide has none like it. A heading
> with nothing under it only places what follows. Copy any block of the guide here to change it
> for this repo; delete a prompt to keep what the guide says.

## The point of the process

### The failure it stops

A published file in `dist/` that is wrong without anything saying so: a barangay with a null
name, a city under the wrong province, counts that are right over boundaries that aren't.

The pipeline fails plausibly, not loudly. A left join that misses a row leaves a null, a manual
override in a release file moves a code and the map still renders, and a merge applied to
the codes but not the geometry gives correct-looking counts. Users join these files by PSGC code
and trust them, so everything below exists to put a checkable claim (the CONTRACTs in
`CLAUDE.md`) between a change and the people downloading `dist/`.

## Tiers: the overhead control

### Always Tier 2, whatever the size of the diff

- **Changing which source row maps to which PSGC code.** One override line in a release file
  (`releases/<id>.toml`) silently changes every join a consumer makes on that code.
- **Changing an output's columns, names or types.** People's joins and dashboards read `dist/`
  files directly.
- **Any regeneration of `dist/`**: a quarterly PSGC update, a geometry edit, a new source year.
  Each one rewrites what users download.

## Where a change is worked: one worktree per change

### What a worktree needs

A fresh worktree has no virtualenv, and the pinned deps (numpy 2.5, geopandas 1.2) don't
install on the newest Python, so `commands.worktree_setup` runs `uv sync --extra test --locked`
in it: `requires-python` (`>=3.12,<3.13`) makes uv pick 3.12, as CI runs, and the committed
`uv.lock` gives every worktree the same environment. The gate then runs with `uv run --no-sync`. The
setup then runs `scripts/sources.py fetch`, which hard-links the raw boundary sources (gitignored;
`data/sources.toml` lists them) from the main checkout, downloading from the `sources` release only
what the main checkout lacks, so a worktree can build. What it can't bring: anything else untracked
in the main checkout (such as `data/2026/`) is not in the worktree.

## Running the stages

### Stage 1 — Plan → `/sdlc:intent`

#### Push-backs at Stage 1

Push back on a tier that ignores the carve-outs above: a "one-line" override or a regeneration
of `dist/` is Tier 2. And ask which levels the change regenerates: the CLI rebuilds municities
only, and `scripts/regenerate.py --levels` names the rest, so the intent names them.

### Stage 4 — Test

#### The gate and the slower check

The gate here is `pytest`, `black --check`, `flake8` and `pylint` over `src` and `scripts`, run in
the worktree's `uv` environment: the unit tests for the level toggle, the runner, the adm4 parent
fixes and `check_dist`, on fixtures, with no raw sources. CI runs the same linters but only annotates
their findings, so the gate is what enforces them.

The slower check (`commands.build`, on changes under `src/`, `scripts/`, `data/`, `pyproject.toml`
or `uv.lock`) regenerates every level into a temp dir, runs `check_dist.py check` on it (CONTRACT 2:
unique non-null codes, every parent present a level up, codes against the PSGC table with the
known extras listed in the script) and `check_dist.py diff` against the committed `dist/`. Healthy
is "0 problem(s)" from both; a change meant to alter `dist/` commits the regenerated files, behind
CONTRACT 3's confirmation, so the diff comes back clean.

### Stage 5 — Ship → `/sdlc:ship`

#### The path to users

**Publishing a release is publishing.** Users download each PSGC quarter's GitHub release: its
zips, CSVs and `SHA256SUMS`, made by `scripts/publish_release.py` (`prepare`, then `upload` as
`release.publish`). Pushing `main` publishes `dist/`'s CSVs, which anyone reading the repository
sees at once. CONTRACT 3 in `CLAUDE.md` applies before `dist/` is regenerated at all and before a
release is published or added to; `CHANGELOG.md`'s PSGC updates table is what each release's notes
are made from. CI (`build.yml`) validates on push and PR; PR titles follow Conventional Commits.

### Stage 6 — Maintain → `/sdlc:health`

#### What the scans watch

`commands.scan` is the integration suite the gate leaves out (`pytest -m integration`): CONTRACT 2
over the committed `dist/` CSVs, every `data/psgc/` publication, 2026-3q's recodes against PSA's
transfers, and nothing tracked needing git-lfs. `.sdlc/HEALTH.md` routes what it finds. Not scanned:
`CHANGELOG.md` rows still ❌ Pending after PSA has published. (Source paths whose casing differs
from the folders on disk fail when a release file loads.)
