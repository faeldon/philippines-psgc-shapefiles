# Nits

> Small technical debt: findings ship approved unfixed, kept until a change fixes them or makes
> them moot. Each one is a `## NNN-n [theme] <title>` heading (the raising change's number and a
> count), then `- **raised:** YYYY-MM-DD by NNN-slug (pass)`, `- **paths:** a, b` and
> `- **cost:** S|M  **value:** med|low` lines, then a line or two on what's wrong. The process
> doc's rubric says what each cost and value means. `/sdlc:intent` and `/sdlc:spec` offer the ones
> a change touches, `/sdlc:ship` adds and retires entries, and `/sdlc:retro` counts them by theme
> and age; history keeps a retired one.

## 101-1 [release] check_source detects a listed source by text
- **raised:** 2026-10-25 by 101-distribution-budget (correctness)
- **paths:** src/ph_psgc_shape/release.py
- **cost:** S  **value:** low

`release.check_source` decides a missing path is a raw source by finding `path = "<rel>"` in
`data/sources.toml`'s text, which avoids importing `sources` (it imports `release`). A reformatted
manifest would drop the "run `sources.py fetch`" hint; the missing path still raises.

## 101-2 [release] sources upload can't keep its release from being Latest
- **raised:** 2026-10-25 by 101-distribution-budget (correctness)
- **paths:** scripts/sources.py
- **cost:** S  **value:** low

`sources.py upload` sets `--latest=false` with `gh release edit`, but GitHub marks `sources` Latest
while it's the only release. Nothing depends on it (`publish_release.py` skips `sources`), and the
first quarterly release published with `--latest` takes it over.

## 101-3 [cost] gh() and REPO_SLUG duplicated in the two release scripts
- **raised:** 2026-10-25 by 101-distribution-budget (cost)
- **paths:** scripts/sources.py, scripts/publish_release.py
- **cost:** S  **value:** low

Both scripts define their own `gh()` wrapper and `REPO_SLUG`. A shared helper would keep the repo
name and the error handling in one place.
