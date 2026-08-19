## Context

ADR-097 measured the fleet's navigation on 2026-08-19 and found 10 of 18 apps
over a 6-entry top-level menu budget. Its Context section names a specific
mechanism behind part of that: "hrmq's 64 entries include 18 index pages over
6 schemas — the same list rendered once per role, with the filter hardcoded in
the manifest." Decision 5 generalizes this into a rule ("a second index over
an already-indexed schema is a role lens, not a page") and Decision 8 names
the enforcement shape ("gate-65 `navigation-budget`, as a ratchet... modeled
on gate-52"). No such gate exists on `main` today, and — separately —
**gate-65 is already taken**: it is `coding-standard-adoption`, documented in
`docs/hydra/README.md` and `docs/hydra/pipeline-overview.md`, exercised by
`scripts/lib/test_check_coding_standard_adoption.sh`, and listed in
`scripts/test-fixtures/gate-acceptance/COVERED-ELSEWHERE.md`. ADR-097's
gate-65 reference is stale the moment it was written; see Open Questions.

This change scopes to Decision 5 only — the per-schema duplicate-index-page
count — not the full navigation-budget gate (Decision 1's top-level-entry
cap, or Decisions 2/3/4's exemption and domain-naming judgment calls). Decision
5 is a self-contained, mechanically countable rule (group `type:"index"` pages
by `(register, schema)`, count) that does not need the top-level `menu[]`
walk Decision 1 needs. Splitting it out lets it ship and start ratcheting
shillinq's already-measured 27/64 backlog without waiting on the harder
judgment calls (Decisions 4/5's WARN-then-promote path, the personal-surface
verification in Decisions 2/3) that the rest of ADR-097 still needs.

The 27/64 baseline was measured directly against a live 2026-08-19 checkout
of `apps-extra/shillinq` using the vendored `build_effective_manifest.js`
(same tool gate-53 already uses), not assumed from the task description: 595
total pages, 276 of `type:"index"`, grouped by `(config.register,
config.schema)` — 27 groups with more than one page, summing to 64 pages
across those groups, worst two `Subsidie` (6) and `InventoryStock` (4). This
matches the number given at task assignment exactly, which is worth stating
because ADR-097 itself flagged shillinq as *unmeasured* for this ("very
likely the same shape... neither has been measured for it") — this change is
that measurement landing.

## Goals / Non-Goals

**Goals:**

- Count, per app, per `(register, schema)` pair, how many `type:"index"`
  pages in the **effective** manifest (base + `manifest.d/*` fragments) are
  bound to it.
- Ratchet the count per pair: growth beyond the `BASE_REF` count FAILs;
  standing duplication that did not grow WARNs; no resolvable base ⇒ WARN
  everything (fail-safe — never block on a comparison the gate could not
  make).
- Reuse gate-53's effective-manifest assembly (`assembleFromDir`) unchanged
  for HEAD; add the minimum new primitive (`assembleAtRef`) needed to also
  assemble at `BASE_REF`.
- Register as gate 68, ship checker-level fixtures (mirrors gate-53) AND a
  `gate-acceptance` planted/clean bundle (mirrors gate-93) so the gate is
  exercised at both the checker layer and the full wrapper layer.
- Land shillinq's 27/64 baseline as the ratchet's floor, per the "committed
  before the gate lands" principle ADR-097 §8 states for its own ratchet.

**Non-Goals:**

- ADR-097 Decision 1 (the 6-entry top-level cap) and Decisions 2/3/4 (personal
  surface exemption verification, domain-naming judgment) — separate gate(s),
  separate change(s), once ADR-097 itself is Accepted and its gate-number
  collision (Open Questions) is resolved.
- Fixing shillinq's 27/64 backlog — that is the in-flight nav-six-clusters
  change; this gate only stops the number from growing while that work lands.
- Distinguishing a "legitimate" second index (e.g., a genuinely separate
  product surface that happens to share a schema) from a role-lens duplicate.
  The gate counts; it does not judge intent — same posture as gate-52, which
  counts custom widgets without judging whether each one is "good." See
  Decision 4 below for the escape hatch this implies.
- Expanding `pageTemplates[]` / `pageInstances[]` (entity-scaffold
  templating) before counting. See Risks.

## Decisions

### Decision 1: Gate number 68, not 65 and not 97

Sequential numbering (1 through 67, no gaps) is exhausted through gate-67
(`openregister-contract-parity`). Since then the fleet has shipped four gates
numbered after their governing ADR instead — 82 (`public-endpoint-throttling`,
ADR-082), 83 (`contract-surface-shift`, ADR-083), 84
(`npm-supply-chain-config`, ADR-084), 93 (`composer-cooldown-config`,
ADR-093) — each a 1:1 gate-per-ADR mapping.

This gate does not fit that convention cleanly: it implements one Decision
(5) out of an eight-decision ADR (097) whose other decisions need their own,
separate gate work later. Numbering it 97 would misstate it as "the
navigation-budget gate," which it is not — Decision 1's top-level-entry cap
still needs its own implementation and, per the ADR-097 gate-65 collision
below, its own correctly-chosen number. Numbering it 65 is simply wrong: that
number is taken. The next free sequential number, 68, is used instead, with
an explicit cross-reference to ADR-097 Decision 5 carried in the gate's log
messages and the companion skill, so the ADR linkage is discoverable without
depending on the number matching.

**Alternative considered:** wait for ADR-097 to be Accepted and its gate
numbering resolved, then number this gate whatever ADR-097's text ends up
saying. Rejected for this change — the measurement (27/64) and the rule
(Decision 5) are independent of how the rest of the ADR's numbering shakes
out, and shillinq's backlog grows every week this waits. The Open Questions
section below flags the ADR text for correction; this change does not block
on that correction landing first.

### Decision 2: Reuse `assembleFromDir` for HEAD, add `assembleAtRef` for `BASE_REF`

Gate-53's `build_effective_manifest.js` already assembles the effective
manifest from the **live filesystem** (`assembleFromDir(appDir)` — reads
`fs.readFileSync` against whatever is checked out). That is sufficient for
every existing manifest gate (53, 60, 62, 63) because none of them compares
two points in history — they only ever validate what is checked out right
now, informationally noting when the diff didn't touch a manifest input.

This gate is the first that needs the effective manifest **as it existed at
an earlier commit**, because the ratchet compares a per-pair count at
`BASE_REF` against the same count at HEAD. Gate-52's
`check_custom_widget_ratchet.py` solves an adjacent problem
(`_base_content(file_path, base_ref)`, a single `git show
<base_ref>:<path>` call) but only ever diffs ONE file's content, not a
directory tree that has to be re-merged (base manifest + N fragments +
menu-layout, ADR-037/ADR-044 order) before it means anything.

`assembleAtRef(gitRoot, ref, appRelDir)` is added to
`build_effective_manifest.js`:

1. `git archive <ref> -- <appRelDir>/src/manifest.json
   <appRelDir>/src/manifest.d <appRelDir>/src/menu-layout.json` piped into a
   `tar -x` against a `mktemp -d` directory. Paths that don't exist at `ref`
   are silently absent from the archive (git archive's normal behavior for a
   non-existent pathspec component) — `manifest.d` or `menu-layout.json`
   newly added since `BASE_REF`, or deleted since, are both handled for free
   by feeding the result straight into the existing "missing manifest.d /
   menu-layout.json is an absent input, not an error" branch of
   `assembleFromDir`.
2. Call the existing `assembleFromDir(tmpdir/appRelDir)` unchanged.
3. Clean up the temp dir on any exit path (success, thrown error, or the
   caller's own error) — same discipline gate-30's design doc requires of its
   temp-file handoff to `check_manifest.js`.

This reuses 100% of the existing merge-order logic (Decision in gate-30's own
design.md, §Decisions #1: "vendor the pipeline once, do not re-implement
it") rather than writing a second, parallel "assemble from strings instead of
files" code path that could drift from `assembleFromDir`'s behavior.

**Alternative considered:** `git show <ref>:<path>` per file, read into
memory, and pass the three strings into a new
`buildManifestFromStrings(baseStr, fragmentStrs, layoutStr)` variant of the
existing `buildManifest()`. Rejected: `buildManifest()` already takes parsed
objects, not strings, and `assembleFromDir`'s existing file-discovery logic
(glob the `manifest.d/` directory, ascending filename order, detect presence
of `menu-layout.json`) would have to be duplicated against `git ls-tree`
output instead of `fs.readdirSync`. The `git archive` approach makes
`assembleFromDir` the ONLY discovery/merge code path that ever runs,
regardless of which ref is being assembled.

**Alternative considered:** `git worktree add` a detached worktree at
`BASE_REF` and run `assembleFromDir` against it directly, no archive/tar step.
Rejected — creates a second working tree with its own lock file inside the
already-checked-out repo, more expensive and more state to clean up than an
archive-to-tempdir for what is a handful of small JSON files.

**Forward-looking note:** this primitive is exactly what ADR-097 Decision
1's own future gate (top-level `menu[]` entry count, base vs head) will also
need. It is written generically (`gitRoot`, `ref`, `appRelDir` — no
Decision-5-specific assumptions) so that gate can reuse it rather than
re-deriving the same `git archive` dance.

### Decision 3: The ratchet is per-`(register, schema)` pair, not one fleet-wide scalar

Gate-52's ratchet compares ONE number app-wide (`base` total custom widgets vs
`head` total). This gate's task framing is explicit that the comparison is
per-pair: "pre-existing duplicates WARN, a change that ADDS a duplicate index
page BLOCKS" — read literally, "a duplicate index page" is scoped to whichever
`(register, schema)` pair it was added to, not to the fleet-wide sum.

A single scalar total would let a PR shrink `Subsidie` from 6 to 5 while
growing `InventoryStock` from 4 to 5 and still show a flat or falling total —
exactly the kind of aggregate-hides-the-regression failure mode ADR-097 §
Alternatives-considered rejects for its own top-level cap ("it punishes an
app... and would make shillinq's 122 [total entries] the headline when the
real finding is probably duplication"). Per-pair comparison means each
schema's count can only ratchet one direction (down or flat), independent of
what every other schema in the app is doing.

Concretely, for a pair present in both assemblies:

| BASE_REF count | HEAD count | Verdict |
|---:|---:|---|
| 1 (or absent) | 1 (or absent) | no finding |
| 1 (or absent) | ≥2 | **FAIL** — new duplicate introduced |
| ≥2 | > BASE_REF count | **FAIL** — existing duplicate grew |
| ≥2 | ≤ BASE_REF count, still ≥2 | **WARN** — pre-existing, not worsened |
| ≥2 | ≤1 | no finding — consolidated |

A pair that exists only in the base assembly (schema/page removed) is not
evaluated — nothing to warn or fail about a pair the HEAD manifest no longer
references.

### Decision 4: No exclude-reason escape hatch, unlike gate-16/19/52

Gates 16 (`spec-coverage`), 19 (`e2e-coverage`) and 52
(`custom-widget-ratchet`) all carry a reason-bearing `@<gate> exclude
{reason}` marker an author can attach to suppress a specific finding.
ADR-097 Decision 5 does not offer an equivalent for this rule — it names the
two sanctioned fixes explicitly (`menu[].query` for a preset filter, an
`authorization` `match` clause for a scoped filter) rather than a
please-look-past-this annotation, and both mechanisms "ship today" per the
ADR text.

This gate follows that: no exclude marker. A team that believes a second
index page is a genuinely distinct product surface, not a role lens, has two
honest paths — recharacterize one of the pages (a different `register` or
`schema` if they truly are different data; there is then no shared pair to
count), or accept the WARN and let review settle whether Decision 4's
"single tool" / "record type" reasoning from ADR-097 applies. Silently
suppressing the count would reintroduce exactly the blind spot Decision 5
exists to close.

**Open question**, not resolved by this change: if real-world use turns up a
case where two index pages over one schema are legitimately different
surfaces (e.g., an "Archive" index with a different action set and no
create/edit — closer to a `logs`-typed page in spirit but modeled as
`type:"index"` for column-grid reuse), the fleet may want the escape hatch
after all. Ship without one; add it in a follow-up change if review pressure
demonstrates the need, rather than pre-building an exemption path for a case
that has not been observed on the fleet yet.

### Decision 5: Checker-level fixtures AND a gate-acceptance bundle

Gate-53 tests itself with `test_check_manifest_crossref.js` against
`good`/`broken` app-shaped fixture directories — a checker-level test that
never goes through `run-hydra-gates.sh`'s shell wrapper. Gate-93 tests itself
with a `gate-acceptance/composer-cooldown-config/{clean,planted}` bundle plus
an `expect.conf` row consumed by `test_gate_acceptance_matrix.sh` — an
end-to-end test that DOES exercise the shell wrapper, and which also feeds
the coverage ratchet that makes "every gate has a planted/clean pair" a
checked property of the whole package (`COVERED-ELSEWHERE.md`,
`UNCOVERED.md`).

This gate does both (tasks.md §3), because the ratchet mechanic (Decision 3)
has a base-vs-head axis neither existing single-snapshot fixture style
exercises on its own:

- The checker-level `duplicate-index-pages/{good,broken}` fixtures pin the
  **counting and grouping logic** (does `(register, schema)` pair extraction
  and grouping produce the right numbers) against a single manifest snapshot,
  cheap to reason about and to extend.
- The `gate-acceptance/duplicate-index-pages/{clean,planted}` bundle, with
  `clean/` as two git-committed states (an initial commit at "BASE_REF" and a
  second commit at "HEAD" that adds a duplicate only in `planted/`), pins the
  **ratchet's FAIL/WARN split** end-to-end through the actual gate-68 shell
  block — this is the part a checker-only test cannot see, because the
  checker only knows what `run-hydra-gates.sh` tells it about `BASE_REF`; the
  wrapper's job of resolving `BASE_REF` and calling the checker twice is
  itself part of what needs a positive/negative control.

## Reuse Analysis

- `scripts/lib/build_effective_manifest.js` — `assembleFromDir` reused
  verbatim for HEAD; `assembleAtRef` is a new, additive export.
- `scripts/lib/check_manifest_crossref.js`'s `isLiteralSlug()` /
  `slugify()` pattern for treating sentinel/token register-schema values
  (`@resolve:*`, `{param}`) as unresolvable-and-skipped rather than a false
  finding — reused (ported, not imported — the file is a checker for a
  different gate) into `check_duplicate_index_pages.js`.
- Gate-52's `_git()` / `_base_content()` shell-out pattern
  (`check_custom_widget_ratchet.py`) — the design precedent for "diff a file
  at BASE_REF" that Decision 2 generalizes to a directory tree; not reused
  as code (Python vs. this gate's Node checker), reused as the shape of the
  solution.
- Gate-53's block in `run-hydra-gates.sh` (~line 8852) and gate-52's block
  (~line 8735) — the diff-scope / helper-missing / fail-closed shell
  structure gate-68 copies.
- `scripts/lib/test_gate_acceptance_matrix.sh` +
  `scripts/test-fixtures/gate-acceptance/composer-cooldown-config/` — the
  `expect.conf` bundle format gate-68's end-to-end fixture copies (Decision
  5).

## Declarative-vs-Imperative (ADR-031)

**Out of scope.** This change is hydra CI tooling (bash + vendored Node
helpers), not app business logic or an OpenRegister schema surface.

## Seed Data

**Not applicable** — CI tooling plus markdown/fixtures; no OpenRegister
schemas or register objects introduced.

## Container / script impact

- **Builder + reviewer images:** gain gate 68 and the `assembleAtRef`
  addition at build time, exactly as existing gates are copied. Security
  image unaffected (mechanical, non-security gate).
- **`scripts/run-hydra-gates.sh`:** new gate-68 block after gate-67 (placed
  near gate-53's manifest-reading block for readability, per the file's
  existing "manifest family" grouping — gates 15/22/53/60/62/63 already sit
  near each other); the `[ -f src/manifest.json ]` `_declare_na` line gains
  `68`. The `[hydra-gates] ALL ${_declared_n} GATES GREEN` banner is
  auto-derived from `_pass/_fail/_skip N "name"` calls already in the file
  (confirmed against `main` — this is NOT the gate-30-era hardcoded "ALL 30
  GATES GREEN" string; that was fixed since), so no manual banner-count edit
  is needed — adding the gate's `_pass`/`_fail`/`_skip` calls updates the
  count for free.
- **CLAUDE.md:** no agent-behaviour change — mechanical gate, invoked by the
  existing Rule-0b wrapper.

## Risks / Trade-offs

- **[`assembleAtRef`'s `git archive` requires the repo to have `BASE_REF`
  fetched/reachable]** → same precondition every other diff-scoped gate
  already has (`BASE_REF` resolution is a pre-existing `run-hydra-gates.sh`
  concern, documented under "The base ref" in the package README); this gate
  adds no new failure mode here, but see the next risk for what happens when
  it's unmet.
- **[`BASE_REF` unresolvable (shallow clone, orphan branch, no delta base)]**
  → per Decision 3's table, the gate cannot compute a per-pair delta and
  falls back to WARN-everything, matching gate-53's and gate-52's own
  "no base ⇒ informational only" posture. Never a false FAIL, never a false
  PASS — the >1 findings still print, they just don't block.
- **[`pageTemplates[]` / `pageInstances[]` entity-scaffold templating is not
  expanded by `assembleFromDir`]** → pre-existing limitation shared with
  gate-53 (its cross-reference checks have the identical blind spot), not
  introduced by this change. Confirmed shillinq does not use
  `pageTemplates`/`pageInstances` (grepped the live checkout, 2026-08-19), so
  the 27/64 baseline is not undercounted by this gap today. If a fleet app
  adopts entity-scaffold templating for index pages, this gate (and gate-53)
  both need the expander wired in — tracked as a shared follow-up, not
  duplicated here.
- **[Per-pair ratchet needs the pair to be identifiable across the two
  assemblies]** → identified by the literal `(register, schema)` string pair,
  same as gate-53's slug-resolution check. A PR that renames a schema slug
  in the same change it touches index pages could misattribute a count
  change (the old slug's group looks like it shrank to zero, the new slug's
  group looks new). Accepted: schema renames are rare, are themselves a data
  migration under this org's own convention ("a property OR value rename is
  a DATA MIGRATION" — project memory), and a reviewer already has to look
  hard at that PR regardless of this gate.
- **[Checker cannot distinguish a role-lens duplicate from a legitimately
  distinct index]** → by design (Decision 4); the WARN is advisory-strength
  on this axis even when it's a FAIL on the ratchet axis. A human still
  decides whether Decision 4's domain test applies.

## Migration Plan

1. **This change** (hydra-gates package, `kind: code`): `assembleAtRef` +
   checker + gate-68 block + fixtures + self-tests.
   `openspec validate --strict` passes; the self-tests pass; a fleet dry-run
   (`--scope-to-diff` unset) against shillinq reproduces the 27-group /
   64-page baseline as WARN findings, committed as the ratchet's floor
   (mirrors ADR-097 §8's "the census is committed as the ratchet's floor
   before the gate lands").
2. **Companion skill + ADR-097 correction** (separate change, `hydra` repo):
   `hydra-gate-duplicate-index-pages/SKILL.md`, and a doc fix to ADR-097 §8
   replacing its stale "gate-65" reference with "gate-68 (this change)" for
   Decision 5's enforcement, leaving Decision 1's own gate number an open
   slot for whoever implements it.
3. **Per-app follow-up** (already in flight for shillinq): the
   nav-six-clusters change consolidates shillinq's 27/64 duplicates using
   `menu[].query` / `authorization` per Decision 5's sanctioned fixes. Other
   apps flagged by the dry-run (hrmq's 18/6 is already known from ADR-097's
   own Context; scholiq is unmeasured) get their own follow-up changes filed
   at planning time.

**Rollback:** revert the commit — removes the gate-68 block, the
`assembleAtRef` addition, the checker, and the fixtures. The ratchet's
fail-safe default (no base ⇒ WARN only) means a full-fleet dry run never
blocked anything before the per-app follow-ups landed.

## Open Questions

- **ADR-097 §8's "gate-65" reference is wrong on the day the ADR was
  written.** Gate-65 is `coding-standard-adoption`, shipped, documented, and
  tested. This needs a doc correction in `hydra/openspec/architecture/adr-097-navigation-budget.md`
  regardless of what happens with this change — flagged here because this
  change's own numbering (Decision 1) depends on the reader not assuming
  ADR-097's text is authoritative on the number. Whoever accepts ADR-097
  should resolve this — and separately decide whether Decision 1's own
  top-level-count gate becomes 69 (next sequential after this change lands)
  or an ADR-numbered exception (`gate-97`, following the 82/83/84/93
  convention) once it exists.
- **Escape hatch (Decision 4):** ship without one; revisit if review finds a
  real legitimately-distinct-surface case the WARN can't resolve on its own.
- **Where the per-app ratchet floor is recorded**, mirroring gate-53's own
  open question about its baseline: this change's dry-run produces
  shillinq's initial 27/64; whether hydra persists that number anywhere
  durable (vs. re-deriving it from `git log` each time) is deferred — the
  gate itself is diff-scoped and stateless, same posture gate-53 shipped
  with.
- **Grouping key canonicalization:** `check_manifest_crossref.js`'s
  `isLiteralSlug()` already excludes sentinel/token values
  (`@resolve:*`, `{param}`) from being treated as a real slug. Should two
  pages whose `register`/`schema` differ only by case (`"Subsidie"` vs
  `"subsidie"`) be treated as the same pair? gate-53's own register/schema
  discovery lower-cases everything (`discoverDeclaredSlugs`); this gate's
  design should probably match that rather than introduce a second
  case-sensitivity convention, but it is called out here rather than
  silently assumed, since the shillinq baseline above was computed
  case-sensitively (exact string match) and did not need lower-casing to
  reproduce the cited numbers — worth confirming against a wider fleet
  sample before the implementation change locks it in.
