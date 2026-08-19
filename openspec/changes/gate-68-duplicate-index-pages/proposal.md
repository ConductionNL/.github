---
kind: code
---

## Why

ADR-097 (Navigation Budget, proposed 2026-08-19) Decision 5 names the rule but
no gate enforces it yet: "a second index over an already-indexed schema is a
role lens, not a page." Two `type:"index"` pages bound to the same
`(register, schema)` pair and differing only by a hardcoded filter, a default
filter, or column order are one page wearing two menu entries — the fix is a
`menu[].query` preset or an `authorization` `match` clause, both of which ship
today and neither of which the fleet uses for this.

hrmq's 64-entry menu (the finding that started ADR-097) carries 18 index pages
over 6 schemas for exactly this reason — `MijnUren` / `Timesheets` /
`TimesheetApproval` / `TeamUrengoedkeuring` are one query rendered four times
because row-level RBAC was never configured. ADR-097's own Context table
flagged shillinq and scholiq as "very likely the same shape at larger size,
neither has been measured for it." This change is that measurement, done
against a live 2026-08-19 checkout of shillinq
(`apps-extra/shillinq`, effective manifest = `src/manifest.json` + 81
`src/manifest.d/*.json` fragments): **27 of shillinq's schemas carry more than
one `type:"index"` page, 64 index pages total sit inside those 27 duplicate
groups, and the worst two are `Subsidie` (6 index pages: `RDSubsidies`,
`SubsidiesOverzicht`, `SubsidiesVerleend`, `SubsidiesTeruggevorderd`,
`SubsidieAanvragen`, `SubsidieTerugvorderingen`) and `InventoryStock` (4:
`StockLevels`, `StockByLocation`, `ReserveStock`, `StockLedger`)**. Computed
with `scripts/lib/build_effective_manifest.js` (the same assembly gate-53
already uses) so fragments count as rendered, not against the base manifest
alone.

The rule needs a gate for the reason ADR-097 §Context (3) gives for the whole
family: "the rule that stops regrowth is not the number." Without a mechanical
check, a future PR can add a 65th duplicate to shillinq's pile the same way
the first 64 arrived — one reasonable-looking index page at a time, each never
compared against its siblings.

## What Changes

- **NEW hydra gate 68** `duplicate-index-pages` in `scripts/run-hydra-gates.sh`
  (67 = `openregister-contract-parity` is the current highest sequential gate;
  82/83/84/93 are ADR-numbered exceptions — see design.md Decision 1 for why
  this gate does not take 97 or 65). For every `(register, schema)` pair
  referenced by a `type:"index"` page in the app's **effective** manifest
  (base + `manifest.d/*.json` fragments, per ADR-037 — `menu-layout.json`
  relocations/removals do not change this count, they only move menu
  entries), counts the index pages bound to it. More than one is a finding.
- **Ratchet, not a hard cap**, modeled on gate-52 `custom-widget-ratchet` and
  diff-scoped per ADR-020 the way gate-53 is: for each `(register, schema)`
  pair, if the PR's HEAD count exceeds the count at `BASE_REF`, that pair
  **FAILs** (a new duplicate, or a pre-existing duplicate that grew). If HEAD
  count is unchanged or lower than `BASE_REF` but still `>1`, that pair
  **WARNs** (pre-existing, not made worse by this PR). A full run with no
  resolvable base (`--scope-to-diff` unset, or no delta base) reports every
  `>1` pair as WARN — informational, never blocking, because "was this PR's
  doing" cannot be answered without a base to compare against.
- **shillinq's 27/64 baseline WARNs on day one**, not BLOCKs. The gate ships
  green against the fleet's current backlog; it starts blocking the moment a
  PR — on shillinq or any other app — pushes any one `(register, schema)`
  pair's index-page count higher than it already was. shillinq's
  nav-six-clusters change (in flight, see project memory) is the intended
  path to shrinking the 27/64 number; this gate's job is only to stop it
  growing in the meantime.
- **NEW builder primitive** `assembleAtRef(gitRoot, ref, appRelDir)` in
  `scripts/lib/build_effective_manifest.js` — materializes
  `src/manifest.json` + `src/manifest.d/*.json` + `src/menu-layout.json` as
  they existed at an arbitrary git ref (via `git archive <ref> -- <paths>`
  into a temp dir, then the existing `assembleFromDir`) and returns the
  effective manifest for that ref. Gate-52's `_base_content()` (Python,
  single-file `git show <ref>:<path>`) is the closest existing precedent but
  only ever diffs one file at a time; this gate is the first one that needs a
  whole manifest **directory tree** assembled at a non-HEAD ref, so the
  primitive is new. It is written to be reusable by ADR-097 Decision 1's own
  future gate (the top-level menu-entry-count ratchet), which will need the
  identical base-vs-head effective-manifest comparison.
- **NEW checker** `scripts/lib/check_duplicate_index_pages.js` — walks
  `pages[]` in the effective manifest (built via `assembleFromDir` for HEAD,
  `assembleAtRef` for `BASE_REF`), filters `type === "index"`, groups by
  literal `(config.register, config.schema)`, and applies the ratchet rule
  above per group.
- **NEW companion skill** `hydra-gate-duplicate-index-pages` (target repo:
  `hydra`, `.claude/skills/` — this clone only carries the `.github` half of
  the gate; see Impact), following the existing `hydra-gate-*` pattern.
- **Diff-scoped per ADR-020**: computed for every app that ships
  `src/manifest.json` on a full run; on a scoped run the gate still computes
  (the count is app-wide, not file-diff-scoped — same reasoning gate-52 uses
  for its ratchet half) but only the FAIL/WARN split depends on whether
  `BASE_REF` is resolvable.
- **Fail-closed** when the vendored builder or checker is unresolvable,
  matching gate-53's posture.

## Capabilities

### New Capabilities

- `gate-duplicate-index-pages`: gate 68 — for every `(register, schema)` pair
  referenced by a `type:"index"` page in an app's effective manifest (base +
  `manifest.d/*` fragments), counts index pages bound to it. A pair with
  `>1` index page is a finding, implementing ADR-097 Decision 5. Ratchet
  semantics (modeled on gate-52): a pair whose HEAD count exceeds its
  `BASE_REF` count FAILs; a pair that is `>1` but did not grow WARNs; with no
  resolvable base, every `>1` pair WARNs. Diff-scoped per ADR-020; fail-closed
  when the vendored builder or checker is unresolvable.

### Modified Capabilities

<!-- None. This introduces a new gate capability. Gate-53's contract
     (effective-manifest assembly, structural validation) is reused as-is via
     its existing build_effective_manifest.js / assembleFromDir; the new
     assembleAtRef() addition is additive to that module and does not change
     gate-53's or gate-60's or gate-62's or gate-63's existing behavior. -->

## Impact

### Hydra scripts / containers

- `scripts/run-hydra-gates.sh` — gains the gate-68 block (diff-scoped,
  following the gate-53 / gate-52 structure) and one new line in the
  centralized `_declare_na` table (the existing `[ -f src/manifest.json ]`
  group currently reads "gates 15 22 53" — becomes "gates 15 22 53 68").
  Copied into the builder + reviewer images at build time like every other
  gate.
- `scripts/lib/build_effective_manifest.js` — gains `assembleAtRef()`.
  Existing exports (`buildManifest`, `loadAppInputs`, `assembleFromDir`) are
  unchanged.
- `scripts/lib/check_duplicate_index_pages.js` — NEW.
- `scripts/lib/test_check_duplicate_index_pages.js` +
  `scripts/test-fixtures/duplicate-index-pages/{good,broken}/` — NEW
  checker-level self-test fixtures (mirrors gate-53's
  `test-fixtures/effective-manifest/{good,broken}` pattern).
- `scripts/test-fixtures/gate-acceptance/duplicate-index-pages/{clean,planted}/`
  + `expect.conf` — NEW end-to-end wrapper-level fixture bundle consumed by
  `scripts/lib/test_gate_acceptance_matrix.sh` (mirrors gate-93's bundle
  exactly).
- **`hydra` repo** (separate repo, NOT touched by this change or this clone):
  `.claude/skills/hydra-gate-duplicate-index-pages/SKILL.md` — NEW companion
  skill, and `openspec/architecture/adr-097-navigation-budget.md` needs a
  correction (see Open Questions in design.md — its §8 currently says
  "gate-65 `navigation-budget`", and gate-65 is already
  `coding-standard-adoption` on `main`).

### Target apps

No app code changes in this change. The gate surfaces shillinq's existing
27/64 backlog as WARN; per-app consolidation (shillinq's nav-six-clusters
change, and any other app the fleet dry-run surfaces) is separate, already
in-flight or follow-up work.

### Rollback

Pure additive hydra tooling. Reverting the commit removes the gate-68 block,
the `assembleAtRef()` addition, the checker, and the fixtures — no other gate
is affected. `assembleAtRef()` is a new export, not a change to an existing
one, so nothing else in the file can regress from it landing or being
reverted.

### Related ADRs / specs

- **ADR-097** (navigation budget, proposed 2026-08-19) — Decision 5 is the
  rule this gate implements; Decision 8 is the enforcement model (gate-52
  ratchet mechanics + gate-53 diff-scoping style) this gate follows, and the
  ADR text needs the gate-number correction noted above once this change's
  actual number is assigned.
- **ADR-096** (dashboard/index/detail norm) — establishes that a collection
  surface not on the landing page is an index page; this gate assumes that
  vocabulary (`type:"index"`) is the complete set of index surfaces to count.
- **ADR-037** (modular config fragments) — the `manifest.d/*.json` layer this
  gate's count is computed over.
- **ADR-020** (gate scope is the PR diff) — diff-scoping model.
- **`gate-effective-manifest-crossref`** (gate 53, sibling spec) — the
  effective-manifest assembly and `assembleFromDir` this gate reuses
  unchanged; `assembleAtRef` is additive to the same module.
- **`gate-custom-widget-ratchet`** (gate 52, sibling spec) — the base-vs-head
  ratchet mechanic this gate's FAIL/WARN split is modeled on.
