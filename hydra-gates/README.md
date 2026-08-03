# conduction/hydra-gates

The 61 mechanical quality gates, packaged so **any** repo can run them against
its own diff — without hydra, without hydra's containers, and without
credentials.

This directory is the **single source of truth** for the gate runner
(`scripts/run-hydra-gates.sh`), its ~25 Python/JS helpers (`scripts/lib/`), its
vendored schemas (`scripts/schemas/`) and the distributable entry point
(`bin/hydra-gates`). `ConductionNL/hydra` no longer carries a copy — it
delegates here (see [Why it lives in `.github`](#why-it-lives-in-github)).

---

## Adopting it in a repo

### Option A — the shared CI workflow (no composer needed)

If your repo already calls the shared quality workflow, set one input:

```yaml
jobs:
  quality:
    uses: ConductionNL/.github/.github/workflows/quality.yml@main
    with:
      app-name: yourapp
      enable-hydra-gates: true
```

The `hydra-gates` job checks this repository out, resolves the PR's real base
branch, and runs the gates. It works for any repo — PHP or not.

**It is opt-in and defaults to `false`.** A hard gate switched on for the whole
fleet at once would turn many repos red simultaneously; each repo enables it
when its own diffs are clean.

### Option B — `composer require-dev` (gates inside `check:strict`)

Three edits to `composer.json`, then one `composer update`.

**1. Point composer at this repository.** It is **public**, so this needs no
credentials in any repo or CI runner. `"no-api": true` makes composer clone over
git rather than the GitHub API, so a rate-limited unauthenticated runner cannot
turn into a failed install:

```json
"repositories": [
    {
        "type": "vcs",
        "url": "https://github.com/ConductionNL/.github.git",
        "no-api": true
    }
]
```

**2. Require it:**

```json
"require-dev": {
    "conduction/hydra-gates": "^1.0"
}
```

**3. Add the scripts, and put `gates` in `check:strict`:**

```json
"gates":      "hydra-gates --app-dir .",
"gates:full": "hydra-gates --app-dir . --full"
```

Then `composer update conduction/hydra-gates`.

`vendor/conduction/hydra-gates` lands at about 1.2 MB. The org profile, the
website and the docs tree are `export-ignore`d and do not follow.

---

## What it needs at runtime

`bash`, `git`, `python3` (about twenty gates are Python helpers) and `node`
(gates 22 and 53 only, and they additionally want `ajv` resolvable). PHP is
required only because composer is one of the two delivery mechanisms; **no gate
executes PHP**.

**No gate needs a Nextcloud runtime.** Nothing under `scripts/` loads
`../../lib/base.php` — that constraint belongs to `phpunit`, not to the gates,
so a repo can gate itself without an instance.

Anything missing is named on stderr along with what it left uncovered. There is
no `|| echo '...skipping'` anywhere in this package: a missing prerequisite is a
loud, visible, stated skip, and a gate that could not run is **never** counted
toward a green.

---

## The exit code

**The exit code is the number of failing gates.** It is not collapsed to 0/1,
because flows route on the count.

| Code | Meaning |
| --- | --- |
| `0` | every gate that ran passed |
| `1`..`n` | that many gates failed |
| `98` | passed, but coverage was incomplete — only with `--require-full-coverage` |
| `99` | **the gates could not run at all** — unresolvable base ref, missing runner, not a git repo |

`99` sits deliberately outside the gate-count range so a configuration error can
never be misread as 99 failing gates.

A caller that wraps this in a 0/1 contract (`composer check:strict`) must
capture and report the gate exit code separately, so a `99` stays visibly
distinct from a gate failure. Nothing was gated is not the same as nothing was
wrong.

---

## Diff scoping and the base ref

The gates are diff-scoped per ADR-020: a PR is judged on what it changed, not on
what it inherited. This matters — openbuild fails 16 gates on a full-repo run
today and passes when scoped to a real diff. `composer gates:full` gives the
audit view and is deliberately not what `check:strict` runs.

Diff scoping is only as trustworthy as the base ref, and a base that resolves to
nothing produces a report of zero failures that is indistinguishable from a
clean one. So:

- The base is resolved from a stated precedence chain and **printed** every run:
  `--base` → `$HYDRA_GATE_BASE_REF` → `origin/HEAD` → `origin/development` →
  `origin/main` → `origin/master`.
- **An unresolvable base stops the run with exit 99.** It is never treated as an
  empty diff, and no green is printed.
- **A base you named explicitly is never silently replaced.** Substituting a
  different one would scope the run to something you did not ask for and would
  not read about.
- **There is no `HEAD~1` fallback.** On a squash-merged mainline `HEAD~1` is the
  previous release, so it would silently scope a PR against the wrong tree.
- **`@{upstream}` is deliberately excluded, and must never be added back.** The
  tracking branch of a feature branch is that same branch on the remote, so
  diffing against it compares the branch to itself and returns an empty set the
  moment the branch is pushed — which is exactly when CI runs. This was not
  theoretical: the first end-to-end run of this package reported **58 gates
  green over 0 changed files**.
- A base that resolves to the **same commit as HEAD** is warned about loudly. It
  is a valid ref, so nothing else rejects it; it just makes the diff empty by
  construction.
- A genuinely empty diff is **stated as empty** rather than reported as a pass.

---

## Reading a green

A green from this package says how much it covers, because a green that
overstates its coverage is the same defect as `|| echo '...skipping'` one layer
up. The runner's own closing line reads `ALL 61 GATES GREEN` regardless of how
many gates ran; measured on openbuild, 59 of 61 report and gates 24 and 33 skip
silently when their prerequisites are absent. So every run ends with:

```
[hydra-gates] COVERAGE: 59 of 61 declared gates reported a result.
[hydra-gates] GATES THAT DID NOT RUN: 24 33
[hydra-gates] RESULT: ALL GATES PASSED — EXCEPT GATES 24 33, WHICH DID NOT RUN.
[hydra-gates] This green covers 59 gates. It says NOTHING about gates 24 33.
```

The inventory is read out of the runner itself rather than hardcoded, so adding
gate 62 does not silently leave the coverage check measuring against a stale 61.

### Waivers

Gates 16, 19 and 26 honour reason-bearing `@spec exclude`, `@e2e exclude` and
`@visual exclude` tags. That is a better mechanism than a baseline file, because
the justification lives at the point of use — but it shares the failure mode of
`decidesk/phpmd.baseline.xml`, which suppresses nothing while reading as
protection. So every run states how many waivers it honoured:

```
[hydra-gates] WAIVERS: 1 file(s) carry an '@spec exclude <reason>' tag.
[hydra-gates] WAIVERS: 92 file(s) carry an '@e2e exclude <reason>' tag.
```

A green earned by passing is then distinguishable from one earned by waiving.

---

## Testing the package

```
bash hydra-gates/tests/test-hydra-gates-bin.sh     # or: composer test:package
```

Asserts the four invariants — exit-code-is-count, loud unresolvable base, stated
empty diff, self-describing coverage — against a synthesized fixture repo. The
positive control runs in **both** directions: the injected violation must be
*named* by the gate that catches it, and the same fixture must go green once it
is removed. A one-directional control cannot distinguish "the check caught it"
from "the check never ran".

CI for this package lives in
[`.github/workflows/hydra-gates-package.yml`](../.github/workflows/hydra-gates-package.yml):
it runs the suite, and installs the package from this repository's VCS URL into
a scratch project in a **clean `php:8.3-cli` container** — proving the published
location is installable without credentials, rather than proving a local path
works.

---

## Why it lives in `.github`

The gates need to be **public** to be distributable: `ConductionNL/hydra` is
private, so a `vcs` repository pointed at it would need credentials in every
consuming repo and every CI runner. `ConductionNL/.github` is public, and it
already owns the shared workflows every repo calls — so the same move that
solves distribution also puts the gates into the default checks.

**hydra delegates; it does not keep a copy.** `hydra/scripts/run-hydra-gates.sh`
is now a resolver that locates this package and `exec`s it, and fails closed
(exit 99, no green) when it cannot. Two copies that drift is precisely the
failure mode these gates exist to catch.

The git history was **not** imported. A subtree split would have published the
private orchestrator's commit history into a public repository. The provenance
is recorded here instead: this code was developed in `ConductionNL/hydra` and
packaged in [hydra#504](https://github.com/ConductionNL/hydra/pull/504).
