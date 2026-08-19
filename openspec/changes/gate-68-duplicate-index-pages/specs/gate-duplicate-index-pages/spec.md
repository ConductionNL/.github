## ADDED Requirements

### Requirement: Gate scope — computed app-wide, not file-diff-scoped

The `gate-duplicate-index-pages` hydra gate SHALL compute its per-`(register,
schema)` index-page counts for any app that ships `src/manifest.json`,
regardless of which specific files a scoped PR diff touches — the count
depends on the app's whole effective manifest, not on which file changed
(the same reasoning `gate-custom-widget-ratchet` (gate 52) applies to its own
ratchet half).

An app without `src/manifest.json` (Tier 0) SHALL be skipped silently, and
declared not-applicable in the centralized `_declare_na` table alongside
gates 15, 22, and 53.

#### Scenario: Scoped run with no manifest-touching files still computes

- **WHEN** a scoped run (`--scope-to-diff`) sees a PR diff that changes only
  `lib/Controller/FooController.php`
- **THEN** the gate SHALL still assemble the effective manifest and compute
  per-pair counts, because the app-wide count is unaffected by which file the
  diff happened to touch

#### Scenario: Tier-0 app is skipped

- **WHEN** an app has no `src/manifest.json`
- **THEN** the gate SHALL report not-applicable and SHALL NOT be counted
  against `--require-full-coverage`

### Requirement: Effective-manifest index-page grouping

For the HEAD effective manifest (base `src/manifest.json` + `src/manifest.d/*.json`
fragments, assembled per ADR-037 exactly as `build_effective_manifest.js`'s
existing `assembleFromDir` does — `menu-layout.json` relocations/removals do
not change this count), the gate SHALL walk `pages[]`, select every page with
`type === "index"`, and group the selected pages by the literal string pair
`(config.register, config.schema)`. A page whose `config.register` or
`config.schema` is not a literal slug (a runtime sentinel such as
`@resolve:*`, or a `{param}` token) SHALL be excluded from grouping rather
than treated as a distinct or matching pair.

A `(register, schema)` pair bound to more than one `type:"index"` page in this
grouping SHALL be a candidate finding, subject to the ratchet in the next
requirement.

#### Scenario: Two index pages over the same schema across fragments

- **WHEN** the base manifest declares a `type:"index"` page with
  `config.register: "shillinq"`, `config.schema: "Subsidie"`, and a
  `src/manifest.d/*.json` fragment declares a second, differently-`id`
  `type:"index"` page with the same `config.register`/`config.schema`
- **THEN** the grouping SHALL place both pages in the same
  `("shillinq", "Subsidie")` group with count 2

#### Scenario: Six index pages over one schema (shillinq Subsidie)

- **WHEN** the effective manifest declares six `type:"index"` pages
  (`RDSubsidies`, `SubsidiesOverzicht`, `SubsidiesVerleend`,
  `SubsidiesTeruggevorderd`, `SubsidieAanvragen`,
  `SubsidieTerugvorderingen`) all bound to `(register: "shillinq", schema:
  "Subsidie")`
- **THEN** the grouping SHALL report a count of 6 for that pair

#### Scenario: Runtime-bound sentinel register/schema is excluded

- **WHEN** a `type:"index"` page declares `config.register: "@resolve:tenantRegister"`
- **THEN** that page SHALL NOT be grouped with any other page by that value

#### Scenario: Non-index pages are never counted

- **WHEN** the effective manifest declares a `type:"detail"` page and a
  `type:"index"` page both bound to the same `(register, schema)` pair
- **THEN** the grouping SHALL count only the `type:"index"` page; a detail
  page never contributes to a pair's index-page count

### Requirement: Base-ref effective-manifest assembly

The gate SHALL be able to assemble the effective manifest as it existed at an
arbitrary git ref (`BASE_REF`), using the same merge semantics as the HEAD
assembly (base `src/manifest.json` + `src/manifest.d/*.json` fragments in
ascending filename order + `src/menu-layout.json`), via a new
`assembleAtRef(gitRoot, ref, appRelDir)` primitive. Manifest input paths that
do not exist at `ref` SHALL be treated as absent inputs, not errors,
identically to how a missing `manifest.d/` or `menu-layout.json` is treated
on the live filesystem.

#### Scenario: Base ref predates manifest.d fragments

- **WHEN** `BASE_REF` is a commit before an app adopted `src/manifest.d/`
- **THEN** `assembleAtRef` SHALL assemble the base-ref effective manifest from
  `src/manifest.json` alone, with no error

#### Scenario: Base-ref assembly matches live-filesystem assembly at the same tree

- **WHEN** `assembleAtRef` is pointed at a commit whose tree is byte-identical
  to a live fixture directory
- **THEN** its output SHALL equal `assembleFromDir`'s output for that
  directory

### Requirement: Ratchet computation — per-pair FAIL/WARN split

When a resolvable `BASE_REF` is available, the gate SHALL compute, for every
`(register, schema)` pair present in the HEAD grouping with a count greater
than 1, the same pair's count in the `BASE_REF` grouping (0 when the pair does
not appear at `BASE_REF`), and SHALL classify each such pair as follows:

- HEAD count greater than `BASE_REF` count — **FAIL** (a new duplicate was
  introduced by this change, or an existing duplicate grew).
- HEAD count less than or equal to `BASE_REF` count, and still greater than 1
  — **WARN** (pre-existing duplication that this change did not worsen).

A pair present at `BASE_REF` with a count greater than 1 that is not present,
or has a count of 1 or fewer, in the HEAD grouping SHALL NOT be reported (the
duplication was resolved by this change).

#### Scenario: PR adds a duplicate to a previously-clean schema

- **WHEN** `BASE_REF`'s grouping has `(register: "hrmq", schema: "Timesheets")`
  at count 1, and HEAD's grouping has the same pair at count 2
- **THEN** the gate SHALL emit a FAIL for that pair
- **THEN** the gate SHALL exit non-zero

#### Scenario: PR grows an already-duplicated schema further

- **WHEN** `BASE_REF`'s grouping has `(register: "shillinq", schema:
  "Subsidie")` at count 6, and HEAD's grouping has the same pair at count 7
- **THEN** the gate SHALL emit a FAIL for that pair
- **THEN** the gate SHALL exit non-zero

#### Scenario: PR leaves a pre-existing duplicate unchanged

- **WHEN** `BASE_REF`'s grouping has `(register: "shillinq", schema:
  "Subsidie")` at count 6, and HEAD's grouping has the same pair still at
  count 6
- **THEN** the gate SHALL emit a WARN for that pair
- **THEN** the WARN SHALL NOT set the failure exit code

#### Scenario: PR shrinks a pre-existing duplicate but does not fully resolve it

- **WHEN** `BASE_REF`'s grouping has a pair at count 4, and HEAD's grouping
  has the same pair at count 3
- **THEN** the gate SHALL emit a WARN for that pair (still greater than 1),
  not a FAIL
- **THEN** the WARN SHALL NOT set the failure exit code

#### Scenario: PR fully resolves a pre-existing duplicate

- **WHEN** `BASE_REF`'s grouping has a pair at count 2, and HEAD's grouping
  has the same pair at count 1
- **THEN** the gate SHALL NOT report that pair at all

### Requirement: No resolvable base — every duplicate WARNs

When `--scope-to-diff` is unset, or is set but no `BASE_REF` is resolvable
(no delta base available), the gate SHALL NOT compute the per-pair ratchet.
Instead, every `(register, schema)` pair in the HEAD grouping with a count
greater than 1 SHALL be reported as WARN. The gate SHALL NOT fail on any
pair when no base comparison was possible — the gate never blocks on a
comparison it could not make.

#### Scenario: Full run (fleet sweep) against shillinq

- **WHEN** the gate runs with `--scope-to-diff` unset against shillinq's
  checkout
- **THEN** the gate SHALL report all 27 `(register, schema)` pairs with a
  count greater than 1 as WARN, summing to 64 index pages across those pairs
- **THEN** the gate SHALL exit with code 0 (WARN-only never fails)

#### Scenario: Scoped run with no delta base available

- **WHEN** `--scope-to-diff` is set but the run has no resolvable delta base
  (e.g. an orphan branch, or the base ref cannot be fetched)
- **THEN** the gate SHALL fall back to WARN-only reporting for every `>1`
  pair
- **THEN** the gate SHALL NOT exit non-zero on account of any such pair

### Requirement: Gate report shape and exit codes

The gate SHALL emit, on findings, one machine-parseable JSON line naming the
app and its per-pair findings, then a final JSON summary line, both on
stdout, with every stdout line valid JSON. Human-readable `at <path>:
<message>` diagnostics (FAIL) and `at <path>: WARN <message>` diagnostics
(WARN) SHALL go to stderr. The gate SHALL print a terminal
`[duplicate-index-pages] findings=N` marker on every completed run
(succeeded or found violations) so the wrapper can distinguish "ran and found
N findings" from "did not finish."

The gate SHALL exit with code 0 when no pair is classified FAIL (WARN-only
findings, or no findings at all). The gate SHALL exit non-zero when at least
one pair is classified FAIL.

#### Scenario: Findings-only report is machine-parseable

- **WHEN** a consumer reads the gate's stdout line by line
- **THEN** each line SHALL be valid JSON

#### Scenario: FAIL pair sets the exit code, WARN pairs alone do not

- **WHEN** a run has one FAIL-classified pair and three WARN-classified pairs
- **THEN** the gate SHALL exit non-zero
- **THEN** all four pairs SHALL appear in the JSON report, WARN pairs marked
  with `"severity": "warn"`

#### Scenario: Terminal marker distinguishes completion from a crash

- **WHEN** the checker completes without crashing, even with zero findings
- **THEN** stdout SHALL contain a `[duplicate-index-pages] findings=0` line
- **WHEN** the wrapper does not see this marker
- **THEN** the wrapper SHALL treat the run as unfinished (wiring failure),
  never as a pass

### Requirement: Fail-closed when the builder or checker is unavailable

The gate SHALL NOT pass silently when its tooling is unavailable. If
`build_effective_manifest.js` (including its `assembleAtRef` export) or
`check_duplicate_index_pages.js` cannot be resolved in the execution
environment, the gate SHALL fail (or emit an error status line and exit
non-zero), mirroring gate-53's fail-closed posture.

#### Scenario: A vendored helper is missing

- **WHEN** `scripts/lib/check_duplicate_index_pages.js` is missing from the
  execution environment
- **THEN** the gate SHALL surface the misconfiguration as a failure
- **THEN** the gate SHALL exit non-zero

### Requirement: Integration with run-hydra-gates.sh

The gate SHALL be registered as gate 68 in `scripts/run-hydra-gates.sh` with
identifier `duplicate-index-pages`, following the diff-scope and
helper-invocation structure of gate 52 and gate 53. The centralized
`_declare_na` line covering `[ -f src/manifest.json ]` (currently declaring
gates 15, 22, 53 not-applicable when the file is absent) SHALL be extended to
include gate 68.

#### Scenario: Gate registered as 68

- **WHEN** `scripts/run-hydra-gates.sh` is inspected
- **THEN** there SHALL be a gate-68 block with identifier
  `duplicate-index-pages`

#### Scenario: Tier-0 app declares gate 68 not-applicable

- **WHEN** the gate runs against an app with no `src/manifest.json`
- **THEN** gate 68 SHALL be declared not-applicable via the shared
  `_declare_na` line, not silently absent from the coverage count

#### Scenario: Coverage count reflects the new gate automatically

- **WHEN** the full gate suite runs after this gate is added
- **THEN** the `COVERAGE: N of M declared gates reported a result` line's `M`
  SHALL be one higher than before this gate existed, with no manual banner
  edit required (the count is derived by scanning the runner's own
  `_pass`/`_fail`/`_skip` call sites)

### Requirement: Companion skill definition

A skill `hydra-gate-duplicate-index-pages` SHALL be created (in the `hydra`
repo, following the existing `hydra-gate-*` pattern) that assembles the
effective manifest at HEAD and, when a base is available, at `BASE_REF`,
groups `type:"index"` pages by `(register, schema)`, applies the ratchet, and
returns the pass/warn/fail verdict per the exit-code requirement above.

#### Scenario: Skill follows the gate report shape

- **WHEN** the `hydra-gate-duplicate-index-pages` skill runs
- **THEN** its output SHALL conform to the gate report shape defined above
- **THEN** the skill SHALL be callable from `scripts/run-hydra-gates.sh` via
  the standard gate dispatch
