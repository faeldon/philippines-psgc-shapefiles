# Review

> What `/sdlc:ship` works through on every change before it commits: three passes over the diff,
> then how findings are reported. The passes as written name only the mistakes every change can
> make; a repo's own copy (`[docs] review` in `.sdlc/config.toml`) adds under Correctness the ways
> its code has actually failed.

**Scope:** the diff, and only the diff. Three passes, in order. Stop at the first pass that produces
a blocking finding — fix it and re-run rather than accumulating a long list.

## Pass 1 — Correctness

Does the change do what `intent.md` (Tier 1) or `spec.md`'s numbered requirements (Tier 2) said?
Walk the requirements one at a time; **a requirement with no corresponding code is a finding.** A
requirement with code but no test that would fail without it is one too, unless only a revert
could fail it and the change's `checks.md` holds the check that proves it (`notes.md` when it
can't run).

Then look for the failures that don't announce themselves:

- **An error swallowed.** A `try` that catches everything, a default returned where a failure was
  meant, a check that passes when the thing it checks is missing.
- **An edge case the requirements name and the code doesn't handle:** empty input, a missing file,
  a second run of something meant to run once.
- **A test that can't fail.** A glob that matches nothing, an assertion on a mock of the thing under
  test, a case skipped by a condition that is always true.
- **A test only a revert can fail.** A test in the suite that checks a file moved, a key renamed or
  a line added: nothing but undoing the change breaks it, so it is an acceptance check, kept in
  the change's `checks.md` (or `notes.md` when it can't run).
- **Behaviour changed where the diff doesn't say so:** a default, an order, a rename that something
  else still reads by its old name.
- **Bad input that crashes.** Input a person or another system can get wrong (a config file, a
  frontmatter line, a request body) raises a traceback where the code promises to report it.
- **Works only here.** A change that passes because of what this machine or checkout has: a local
  file, an environment variable, a tool on `PATH`, a network service the tests happen to reach.
- **A destructive operation where a safe one exists:** a force flag, a recursive delete, a
  migration or overwrite with no way back, run without the check that makes it safe.

And the ways this repo's pipeline has failed, or is built to fail quietly:

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

## Pass 2 — Contract

Does the change stay inside the invariants the host's policy doc (`[docs] policy`, `CLAUDE.md`, or
`AGENTS.md` when that is the only one) declares? Check each one the diff comes near. If the change
genuinely *needs* one to move, that's an edit to the policy with its own reasoning in `spec.md`,
not a quiet exception.

Two apply everywhere:

- **Confirm before writing.** Any new path that writes something real drafts it, shows it, and
  waits for a yes. Approval is per-invocation, never standing. A write path that doesn't gate is
  blocking.
- **No secrets in the repo.** A key, token or password committed in any form is blocking.

## Pass 3 — Cost and simplification

- **Reuse over reimplementation.** An existing function or tool before a new one.
- **Nothing speculative.** Configuration nobody sets, a layer with one caller, a flag for a case
  that doesn't exist yet.
- **A shim with no removal version.** Code kept for compatibility (an old key still read, an old
  name still accepted) that doesn't name the version that removes it, or a compatibility test that
  outlives its shim.
- **Altitude:** does the new code sit at the same level of abstraction as its neighbours?

## Reporting rules

- Findings are ranked **Important** or **Nit**. Important = wrong behaviour, a broken contract, or a
  requirement with no code or no test. Everything else is a Nit.
- **Cap nits at 5.** If there are more, the change is too big — that's the finding.
- Tag each finding with its pass: `[correctness]`, `[contract]`, `[cost]`.
- **Out of scope, never reported:** generated files, and formatting a formatter already fixes.
