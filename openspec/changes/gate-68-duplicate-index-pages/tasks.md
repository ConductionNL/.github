## 1. `assembleAtRef` builder primitive

- [x] 1.1 Add `assembleAtRef(gitRoot, ref, appRelDir)` to
  `scripts/lib/build_effective_manifest.js`: `git archive <ref> --
  <appRelDir>/src/manifest.json <appRelDir>/src/manifest.d
  <appRelDir>/src/menu-layout.json` into a `mktemp -d` dir, then call the
  existing `assembleFromDir` against it unchanged. Missing paths at `ref` are
  absent inputs (git archive omits them), not errors — same contract
  `assembleFromDir` already has for a missing `manifest.d`/`menu-layout.json`
  on the live filesystem.
  - spec_ref: gate-duplicate-index-pages → "Base-ref effective-manifest
    assembly"
  - files: `scripts/lib/build_effective_manifest.js`
  - Clean up the temp dir on every exit path (success, thrown error).
  - Return shape matches `assembleFromDir`'s (`{ manifest, ... }`) so callers
    don't need to special-case which ref they assembled.
- [x] 1.2 Add a self-test for `assembleAtRef` against a small throwaway git
  repo fixture: assert it reproduces `assembleFromDir`'s output when pointed
  at a commit whose tree equals the live fixture directory, and that it
  correctly omits `manifest.d`/`menu-layout.json` when assembling a ref that
  predates their addition.
  - files: `scripts/lib/test_build_effective_manifest.js` (extend existing)
  - test: `node scripts/lib/test_build_effective_manifest.js` exits 0

## 2. Duplicate-index-pages checker

- [x] 2.1 Implement `scripts/lib/check_duplicate_index_pages.js`: given an
  effective manifest, walk `pages[]`, filter `type === "index"`, group by
  literal `(config.register, config.schema)` (reuse the
  `isLiteralSlug()`/sentinel-exclusion pattern from
  `check_manifest_crossref.js`, ported not imported), and return per-pair
  counts + page-id lists.
  - spec_ref: "Effective-manifest index-page grouping"
  - files: `scripts/lib/check_duplicate_index_pages.js`
- [x] 2.2 Implement the CLI/module entrypoint: `--app-dir DIR` (default CWD),
  `--base-ref REF` (optional — when given, assembles both HEAD via
  `assembleFromDir` and `REF` via `assembleAtRef` and computes the per-pair
  ratchet from task 2.3; when omitted, assembles HEAD only and reports every
  `>1` pair as WARN).
  - spec_ref: "Ratchet computation — per-pair FAIL/WARN split", "No
    resolvable base — every duplicate WARNs"
  - files: `scripts/lib/check_duplicate_index_pages.js`
- [x] 2.3 Implement the ratchet table from design.md Decision 3 (absent/1 →
  ≥2 = FAIL; ≥2 → grew = FAIL; ≥2 → shrank-but-still-≥2 = WARN; → ≤1 = no
  finding), keyed per `(register, schema)` pair.
  - spec_ref: "Ratchet computation — per-pair FAIL/WARN split"
- [x] 2.4 Emit the gate-22/gate-53 report shape: on findings, one
  machine-parseable JSON line per app then the JSON summary line, both on
  stdout; human `at <path>: <message>` (FAIL) / `at <path>: WARN <message>`
  (WARN) diagnostics on stderr. WARN findings never set the failure exit
  code. Print a `[duplicate-index-pages] findings=N` terminal marker (gate-52
  convention) so the wrapper can tell "ran and found N" from "did not
  finish."
  - spec_ref: "Gate report shape and exit codes"

## 3. Fixtures and self-tests

- [x] 3.1 Checker-level fixtures under
  `scripts/test-fixtures/duplicate-index-pages/{good,broken}/` (mirrors
  gate-53's `effective-manifest/{good,broken}` pattern): `good/` has zero
  `(register, schema)` pairs with more than one `type:"index"` page across
  base + fragments; `broken/` has at least one pair with 3 index pages across
  a base + two fragments, exercising the fragment-merge path (not just a
  single-file manifest). Safe placeholder values only.
  - files: `scripts/test-fixtures/duplicate-index-pages/good/src/manifest.json`,
    `.../good/src/manifest.d/*.json`,
    `.../broken/src/manifest.json`, `.../broken/src/manifest.d/*.json`
- [x] 3.2 `scripts/lib/test_check_duplicate_index_pages.js` — asserts `good/`
  produces zero findings and `broken/` produces the expected per-pair count
  and page-id list, no `--base-ref` given (WARN-only mode, since there's no
  git history in a fixture directory). EXTENDED beyond the literal task: also
  asserts `case-varied/` (orchestrator ruling — case-normalized grouping key)
  and five real two-commit git fixtures covering every row of design.md
  Decision 3's ratchet table via `--base-ref` (the checker-level equivalent
  of gate-83's `test_check_contract_surface_shift.sh`).
  - test: `node scripts/lib/test_check_duplicate_index_pages.js` exits 0 —
    31 assertions, all PASS (verified)
- [~] 3.3 DEVIATED FROM THE LITERAL TASK, DOCUMENTED — see
  `scripts/test-fixtures/gate-acceptance/UNCOVERED.md`'s new `gate-68` row
  (`needs-diff` category, same as gate-83). MEASURED, not assumed:
  `test_gate_acceptance_matrix.sh`'s `_run` helper never passes
  `--scope-to-diff` or `--base` to `run-hydra-gates.sh` (confirmed by reading
  the driver and by `register-dialect/expect.conf`'s own note that "the
  acceptance driver runs unscoped"), and gate-68's shell block only passes
  `--base-ref` to the checker when `SCOPE_TO_DIFF=1` — so a `{clean,planted}`
  bundle run through this specific driver could NEVER exercise the ratchet's
  FAIL half; every `>1` pair would report WARN in both arms regardless of
  planted git history, exactly the gap gate-52's own UNCOVERED.md row already
  records for its count-ratchet half. Built the equivalent, stronger coverage
  instead: `scripts/lib/test_check_duplicate_index_pages.js`'s ratchet layer
  (5 real two-commit git fixtures, checker driven directly with
  `--base-ref`), PLUS ad hoc verification of the exact same FAIL/WARN split
  through the REAL shell wrapper (`run-hydra-gates.sh --scope-to-diff --base
  <ref>`) against both a synthetic fixture and the live shillinq checkout
  (see the change's verification notes / final report). Not turned into a
  permanent `gate-acceptance/{clean,planted}` bundle, because — per the
  measurement above — that specific driver cannot make the two arms differ in
  outcome for THIS gate. Left for the orchestrator to accept this
  substitution or direct otherwise.
- [x] 3.4 SUPERSEDED by the 3.3 deviation — no bundle was added, so ran
  `scripts/lib/test_gate_acceptance_matrix.sh` instead to confirm gate 68 is
  correctly declared and resolved via its new `UNCOVERED.md` row (not left
  as a silently-untested declared gate). VERIFIED: "declared gates: 72,
  with planted/clean: 65" (72-65=7 matches exactly the 7 rows in
  UNCOVERED.md — 4, 12, 22, 41, 52, 68, 83), "coverage ratchet intact —
  every declared gate is either fixtured or listed with a reason", 169
  passed / 0 failed, "ALL gate acceptance controls PASSED".

## 4. Gate registration

- [x] 4.1 Add the gate-68 block to `scripts/run-hydra-gates.sh` (identifier
  `duplicate-index-pages`), placed near the existing manifest-family gates
  (53/60/62/63). Diff-scope posture: computed on every full run and on every
  scoped run where `src/manifest.json` exists (the count is app-wide, per
  gate-52's own reasoning for why its ratchet isn't filtered by
  `_in_scope`); resolves `BASE_REF` via the same mechanism gate-52 already
  uses (`HYDRA_GATE_BASE_REF`) and passes `--base-ref` to the checker when
  `SCOPE_TO_DIFF=1` and a base is resolvable, omits it otherwise.
  - spec_ref: "Gate scope", "Ratchet computation — per-pair FAIL/WARN split",
    "Integration with run-hydra-gates.sh"
  - files: `scripts/run-hydra-gates.sh`
- [x] 4.2 Add gate `68` to the centralized `_declare_na` line currently
  reading `[ -f src/manifest.json ] || _declare_na "..." 15 22 53` →
  `15 22 53 68`, so a Tier-0 app with no manifest is declared not-applicable
  rather than silently missing from `--require-full-coverage`.
  - spec_ref: "Applicability declaration for Tier-0 apps"
  - files: `scripts/run-hydra-gates.sh`
- [x] 4.3 Confirm the `[hydra-gates] ALL ${_declared_n} GATES GREEN` banner
  and the `COVERAGE: N of M declared gates reported a result` line pick up
  gate 68 automatically (both are derived by grepping this file's own
  `_pass`/`_fail`/`_skip N "name"` calls) — no hardcoded count to edit.
  Verify by running the full suite and reading the printed `M` before/after
  this change.
  - test: `bash scripts/run-hydra-gates.sh <fixture-app-dir>` — COVERAGE line
    reads one higher than before this change

## 5. Companion skill and ADR correction (separate repo — tracked here, executed there)

- [ ] 5.1 Author `hydra-gate-duplicate-index-pages/SKILL.md` in the `hydra`
  repo's `.claude/skills/`, following the existing `hydra-gate-*` pattern
  (assemble effective manifest at HEAD and, when available, `BASE_REF`; group
  by `(register, schema)`; apply the ratchet; return the gate report shape).
  - spec_ref: "Companion skill definition"
  - Not part of this `.github` clone's diff — files live in the sibling
    `hydra` repo.
- [ ] 5.2 File a doc-correction PR against
  `hydra/openspec/architecture/adr-097-navigation-budget.md` §8, replacing
  "gate-65 `navigation-budget`" with the correct reference once this gate's
  actual number is confirmed at merge time, and noting that Decision 5 is
  implemented by gate-68 while Decision 1 (top-level cap) remains
  unimplemented and needs its own number.
  - Not part of this `.github` clone's diff — files live in the sibling
    `hydra` repo.

## 6. Validate, dry-run, and follow-ups

- [x] 6.1 Run the gate as a fleet dry-run (`--scope-to-diff` unset, no
  `--base-ref`) against shillinq and confirm it reproduces 27 groups / 64
  pages as WARN findings, matching the number measured in design.md.
  - test: `bash scripts/run-hydra-gates.sh <shillinq-checkout>` — gate-68
    findings count and worst-offenders (`Subsidie` 6, `InventoryStock` 4)
    match
- [ ] 6.2 NOT DONE — outside the orchestrator's explicit verification list for
  this apply pass; hrmq checkout not confirmed available in this environment.
  Left as a follow-up cross-check, not blocking. Run the gate against hrmq
  and confirm it reproduces ADR-097's
  already-cited "18 index pages over 6 schemas," as a second live check that
  the counting logic agrees with a number someone else already measured by
  hand.
  - test: `bash scripts/run-hydra-gates.sh <hrmq-checkout>` — gate-68 finds 6
    groups summing to 18 pages
- [ ] 6.3 NOT DONE — the nav-six-clusters branch does not exist yet (per
  project memory, that work is separately in-flight). Nothing to compare
  against today; re-run once that branch lands. Run the gate against a
  same-sha PR-vs-push pair on shillinq's
  in-flight nav-six-clusters branch (once it exists) to confirm the ratchet
  reports the consolidation as a count DECREASE (no false FAIL on a PR that
  only removes duplicate index pages).
- [x] 6.4 Deduplication Check: confirm no existing gate already counts index
  pages per schema (gate-53's cross-reference checks resolve register/schema
  slugs against declared registers but never group or count by page `type`;
  gate-60/62/63 read the manifest for icon vocabulary, store-plane naming,
  and settings placement respectively — none overlaps this capability).
- [x] 6.5 `openspec validate gate-68-duplicate-index-pages --strict` passes.

## Verification

- All checkboxes complete; `assembleAtRef` self-test and the checker
  self-test pass; the `gate-acceptance` bundle's clean arm PASSes and planted
  arm FAILs with the expected pair named; a full dry-run against shillinq
  reproduces the 27/64 baseline as WARN; a full dry-run against hrmq
  reproduces ADR-097's cited 18/6 as a live cross-check.

## Tests (company-wide ADR-009)

- Checker-level self-test (task 3.2) and `gate-acceptance` bundle (task 3.3)
  are the executable spec scenarios. No live Nextcloud required — static
  analysis over manifest JSON plus a throwaway two-commit git fixture for the
  ratchet's base-vs-head axis.

## Documentation (company-wide ADR-010)

- The companion SKILL.md (task 5.1, sibling repo) documents invocation; the
  gate-68 block's header comment in `run-hydra-gates.sh` documents behaviour,
  mirroring gates 52 and 53.

## i18n (company-wide ADR-005)

- N/A — CI tooling with no user-facing strings; gate output is
  machine-parseable JSON plus English diagnostics on stderr.
