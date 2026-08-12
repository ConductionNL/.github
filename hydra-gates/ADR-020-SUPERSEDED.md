<!-- SPDX-License-Identifier: EUPL-1.2 -->

# ADR-020 is superseded: the gates scan the whole tree by default

**Status:** accepted · **Date:** 2026-08-12 · **Decided by:** Ruben van der Linde
**Supersedes:** ADR-020 (diff-scoped gates) · **Applies to:** all 18 fleet apps at once
**Canonical ADR home:** the numbered ADR registry lives in `hydra/openspec/`, not in
this repository. This file is the decision record for the **gate package**, and it is
what `run-hydra-gates.sh` and `bin/hydra-gates` cite. Allocating a superseding ADR
number in `hydra/openspec/` is a follow-up, not a precondition.

---

## The decision

**The Hydra gates scan the ENTIRE tracked codebase by default. Diff scoping is now
opt-in (`--scope-to-diff` / `--diff` / `HYDRA_GATE_SCOPE=diff`).**

Until now it was the other way round: `bin/hydra-gates` defaulted to
`--scope-to-diff` and `--full` was the audit-only escape hatch.

In Ruben's words:

> if a gate changes or is added we want the next push to beta to fail unless the old
> code is fixed to the new standard. This will force developers to take updates to
> the gates along in their new releases.

## What ADR-020 decided, and why it was right at the time

ADR-020 scoped every gate to the PR's diff so that **inherited debt could never block
a PR**. That was a deliberate, defensible trade: a gate that blocks legitimate work
gets switched off, and a switched-off control is worth less than a loud one. It is why
`enable-hydra-gates` could be turned on repo by repo at all.

## Why it is being reversed

Diff scoping means a gate only ever judges code written **after** the gate landed.
The consequences are structural, not incidental:

1. **Tightening a gate has no effect on existing code.** The new rule applies to the
   next hunk anyone happens to touch. Nobody is ever asked to bring old code up to the
   new standard, so the standard is only aspirational for everything already shipped.
2. **The debt is unowned and unmeasured.** It is visible only to a `--full` audit that
   nothing gates on, so it accumulates without a moment at which anyone must look at it.
3. **The empty-diff failure modes are endless.** This package's own history is mostly a
   list of them: `#242`, `#240`, `#258`, `#268`, `#276`, `#347`, `#361`, `#364`, `#371`,
   `#374`. Every one is a variation on *a gate that had nothing to look at printed the
   same word as a gate that looked and found nothing.* Full scope removes the empty set
   in the common case. (It does **not** remove the fall-through — see below.)

## What this costs, stated up front

**The first `development → beta` run after this lands will surface the entire backlog
at once.** The last fleet-wide wide-scope measurement was **~3,900 findings**. That is
the point of the change, and it is also the whole risk in it: 18 repos change verdict
simultaneously.

Two things follow, and they are part of the decision rather than caveats to it:

- **This is a sequencing problem, not a correctness one.** Every finding it surfaces
  was already true. Nothing about the code changed.
- **The number is a FLOOR, not a total.** It predates several gate fixes that make
  gates stricter, and several gates are still `no-fixture-yet`. Quote it as a floor.

## What did NOT change: delta gates keep their base

Five gates ask what a **change** did, and a whole tree cannot answer that:

| gate | name | the question |
|---|---|---|
| 16 | spec-coverage | which methods did this change add or modify without an `@spec` anchor? |
| 29 | gitignore-then-commit | did this change add an ignore rule over already-tracked files? |
| 47 | security-change-has-tests | did this change touch security code without touching a test? |
| 48 | csrf-cochange | did this change REMOVE `@NoCSRFRequired`? |
| 61 | listener-work-placement | did this change add a post-event listener doing work in the wrong plane? |

Keying those on the file scope would have **silently retired all five on every PR in
the fleet** the moment this default flipped — trading the gates that protect the change
in front of you for coverage they cannot use. So the scope is now **two independent,
named inputs**:

| input | controls | default |
|---|---|---|
| `SCOPE_TO_DIFF` / `HYDRA_GATE_SCOPE` | which files the **state** gates open | `full` |
| the resolved **delta base** (`--base`, `$HYDRA_GATE_BASE_REF`, auto-detect, `github.event.before`) | what the **delta** gates compare against | resolved whenever possible |

A PR therefore gets **whole-tree state coverage AND every delta gate**. A
`workflow_dispatch` has no base, and those five report `NOT APPLICABLE` **by name, with
a reason** — never `PASS`, and never counted as one.

This also closes a defect the old conflation caused: *"I ran it with no base" was never
a scope.* gate-19 swept the whole tree while gate-16 fell back to a hardcoded
`origin/development` and printed `PASS` over nothing (`#361`), and gate-61 declined
citing a diff the run had never computed (`#347`) — one package answering one question
two ways. `BASE_REF` now starts **empty**; a base is stated or it does not exist.

**An unresolvable base is no longer fatal at full scope.** On a diff-scoped run it still
exits 99, because without a base there is no scope at all. On a full run it costs five
gates out of 64, so refusing would discard 59 real verdicts to punish one bad input.

## What did NOT change: the empty-scope fall-through is still a bug

Full scope removes the empty set in the common case. It does **not** make the
fall-through safe, and treating it as the fix would have been the mistake:
`--scope-to-diff` still exists, and a repo can genuinely ship no `src/`.

So the fall-through is fixed **at the fall-through** (`_skip_empty_scope` in
`run-hydra-gates.sh`), across **eighteen** gates — the sixteen `#374` enumerates plus
**14** and **20**, found by sweeping the table rather than from the issue. And the
property is now enforced by
`scripts/lib/test_gate_empty_scope_never_passes.sh` **ARM 6**, gate-agnostically over
the whole package, instead of by seven gates named one at a time.

## Rollout

1. **Do not merge this alongside anything else.** It changes the verdict for 18 repos
   simultaneously; the next fleet measurement must be attributable to exactly one cause.
2. **Capture a wide-scope baseline per app first.** The standing `development → beta`
   PR already runs a wide-scope job and its log carries the full table — no
   `workflow_dispatch` needed, and dispatching one cancels that very run.
3. **Expect `--require-full-coverage` to be the loudest change**, not the gate findings:
   a `PASS` that was really an unopened scope now reports `NOT APPLICABLE`, so
   `COVERAGE: N of 64` drops in some repos. That is the line getting *more* honest, not
   coverage getting worse.

## How to get the old behaviour

```bash
hydra-gates --scope-to-diff --base origin/development   # ADR-020, explicitly
HYDRA_GATE_SCOPE=diff hydra-gates                       # the same, via the environment
```

Both print `SCOPE-MODE: diff` and say what they are not judging.
