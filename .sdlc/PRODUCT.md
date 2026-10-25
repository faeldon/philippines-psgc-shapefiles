# Product

> What this repo's product is for, and the outcomes it is after. Every change names the
> outcomes it serves on its intent's `serves:` line (or `none`), and `/sdlc:retro` scores each
> outcome against the evidence `retro.evidence` prints. The plugin reads only the outcome ids
> and their short names, which the skills show beside each id; the rest is yours.
>
> Outcomes keep their ids from one retrospective to the next, and end done, dropped or revised,
> never silently gone: `sdlc.py retro-commit` refuses a doc that drops an open one. The forms:
>
> ```
> - O1. **Unaided setup.** A new user finishes setup without help. Measured by: setups finished / started
> - ~~O2. Exports open in a spreadsheet~~ Done: 0 failed-export reports since 1.4.0
> - ~~O3. Teams share drafts~~ Revised → O4: they share links, not drafts
> ```
>
> Evidence commands, set in `.sdlc/config.toml` under `[retro] evidence`, print counts and
> summaries: never a person's name, address or message. What they print stays in the session
> that ran the retrospective.

## Users

Analysts, researchers, journalists and developers who need Philippine administrative boundaries
(country down to barangay) that they can join to PSA statistics by PSGC code: to map census or
survey figures, build dashboards, or geocode records to a barangay.

## Problem

The public boundary files (OCHA/HDX) lag the PSA's quarterly PSGC changes and carry their own
codes and spellings, so the codes and names don't line up with the PSA's tables. Without this,
every user re-does the matching by hand: chasing renamed barangays, merged or transferred
areas, NCR districts and special cases, and finding the misses only when a map has holes or a
total is off.

## Outcomes

- O1. **Joins just work.** A user joins any `dist/` level to PSA data by PSGC code and every row
  matches, with nothing silently null or misplaced. Measured by: data-error issues filed per
  release; levels regenerated with every CONTRACT 2 check passing.
- O2. **Current with PSA.** `dist/` reflects the latest PSGC quarter PSA has published. Measured
  by: days from a PSA release to its `CHANGELOG.md` row turning ✅; ❌ Pending rows in `CHANGELOG.md`.
- O3. **Downloadable files.** A user who clones the repo gets real shapefiles and CSVs, not LFS
  pointer files or a bandwidth-quota error. Measured by: issues about downloading or LFS; clone
  counts.

## Bets

- Users join on PSGC code rather than name, so code correctness (O1) matters more than name
  spelling, and a wrong code is worse than a missing one.
- Keeping up with each PSA quarter (O2) is what users value most; a stale quarter sends them back
  to doing the matching themselves.
- git-lfs over a git clone is an acceptable way to deliver multi-GB files to these users (O3);
  issues about downloads would say otherwise.
