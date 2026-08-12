# UNCOVERED.md — declared gates with no planted/clean acceptance bundle

This file is the **reasoned exception list** for the coverage ratchet in
`scripts/lib/test_gate_acceptance_matrix.sh`.

Every gate declared by `scripts/run-hydra-gates.sh` must EITHER have a
planted/clean fixture bundle under `scripts/test-fixtures/gate-acceptance/<bundle>/`
(with an `expect.conf` naming it), OR appear as a row below with a reason.
The driver reads this file by grepping `^\| *gate-[0-9]+` and extracting the
number, so the first column cell of every row must literally start with
`gate-<number>`.

**The list may only SHRINK.** Two conditions are hard CI failures:

* a gate listed here that has since gained a planted/clean bundle — delete its
  row, so CI enforces it from that point on;
* a declared gate that appears in neither place — a gate cannot be added to the
  runner and left untested in silence.

Gates already covered by a bundle in THIS directory are deliberately absent
too: **7** (`auth-guards/`, `authn-vs-authz/`, `publicpage-scope/`), **2** and
**21** (`debug-and-conflict/`), **35** and **36** (`a11y-noise/`), **25**
(`contract-coverage/`), **28** (`license-triangle/`), **49**
(`exception-translation/`), **54** (`relation-dialect/`), **19** and **26**
(`prose-not-proof/`), and — added 2026-08-12 — **6** and **9**
(`semantic-authz/`), **15** and **55** (`dashboard-and-detail/`), **18** and
**51** (`register-dialect/`), **62** and **63** (`manifest-planes/`), **64**
(`apphost-prelude/`).

Gates covered by a suite OUTSIDE this directory are listed in
`COVERED-ELSEWHERE.md`, which the driver counts identically. That file carries
forty rows, each quoting the assertion that proves the claim.

## ⚠️ 2026-08-12 — THIS FILE WAS WRONG ABOUT THIRTY-SIX GATES

Thirty-six rows were deleted on 2026-08-12. **Nine** of them gained a bundle in
this directory on the same day. The other **twenty-seven already had a planted
defect driven through the real wrapper**, in a suite under `scripts/lib/`, and
this file said `no-fixture-yet · Nothing blocks authoring this` about every one
of them.

Two of those rows — gates 46 and 50 — were provably false when written:
`test_gate_46_tests_scope.sh` and five gate-50 FAIL arms inside
`test_gate_45_to_55_acceptance.sh` had been in the package for some time. Two
independent registries of "what has been proven" disagreed with the code, in
the same direction — both understating coverage — and neither had been
cross-checked against it. **That mis-registration sent two agents to redo
finished work.**

🔑 **A registry of proven-ness is only as good as the store it was computed
from.** Coverage here was computed from `gate-acceptance/` bundles; the missing
arms lived in `scripts/lib/test_gate_*.sh`. A sweep of the wrong store returns
absence for free. **Before writing `no-fixture-yet` about a gate, grep
`scripts/lib/test_*` for its number and read what the hits assert** — the same
discipline as running a positive control before believing a zero.

## What the categories claim

A reason is a testable claim, so each row states which of five kinds it is.

* `no-fixture-yet` — nothing blocks it; a bundle simply has not been authored.
  The reason names roughly what the planted subject would be.
  **No gate currently qualifies.** The category is kept because it is the right
  answer for a gate added to the runner tomorrow — but it is also the label
  that was wrong thirty-six times, so writing it now requires the grep above.
* `partial-elsewhere` — a suite outside this directory ALREADY plants a defect
  and asserts the gate FAILs, but there is no anti-widening arm anywhere. The
  row names the suite, the assertion that exists, and the half that is missing.
  These gates are NOT in `COVERED-ELSEWHERE.md`, because that file's claim is
  "planted **and** clean" and half of it would be an overclaim.
* `needs-diff` — the gate is intrinsically diff-relative and needs a purpose-built
  git history, not just a directory of files.
* `needs-external` — the gate depends on something a fixture directory cannot
  cheaply supply. The exact dependency is named.
* `advisory-only` — the gate is WARN-only by design, so a planted arm cannot go
  red. **No gate currently qualifies**; the category is documented so that a
  future WARN-only gate is classified rather than mis-filed as `no-fixture-yet`.

Two notes on authoring, both measured rather than assumed:

1. ~~`scripts/test-fixtures/gate-acceptance/auth-guards/` exists but carries no
   `expect.conf` and no source files beyond `appinfo/info.xml`, so it currently
   contributes **zero** covered gates. It is a stub, not coverage.~~
   ⚠️ **Superseded, corrected 2026-08-12.** `auth-guards/` is now a real bundle
   (gate-7, `#353` — verb-object guard predicates) with an `expect.conf` and a
   controller/service pair in both arms, and `authn-vs-authz/` joins it (gate-7,
   `#365` — an authentication check is not an authorisation guard). Two bundles
   assert the same gate from opposite directions on purpose: `auth-guards`
   pins that a real guard is RECOGNISED (the false-positive failure mode),
   `authn-vs-authz` pins that a non-guard is REFUSED (the false-negative one).
   A single bundle could be passed by a checker that is broken in the other
   direction — which is exactly how `#365` survived `#353` and `#360`.

   **The general point the struck-through text was making still stands, which
   is why it is struck through rather than deleted** — a fixture directory with
   no `expect.conf` is not coverage, and the ratchet counts directories, so an
   empty bundle would otherwise read as progress. The driver enforces it
   directly: a bundle without an `expect.conf`, or missing either arm, is a
   hard failure.
2. `_enum_tracked` prefers `git ls-files`, and a fixture directory sits inside
   this repository's own work tree — so a planted file must be **committed** to
   be enumerated at all. An untracked plant reproduces the very silence these
   bundles exist to expose.
3. **Added 2026-08-12.** A bundle's arms are run through the WHOLE runner, so a
   fixture arms every gate whose ingredients it happens to ship. Check what
   yours arms before landing it: the four manifests added on 2026-08-12 were
   all invalid against the v2 schema on first write, and would have put
   gate-22 into a permanent FAIL on eight new arms. Harmless while every
   bundle grades PER-GATE expectations — and the moment any suite adds a
   run-level-green or exhaustive-FAIL-set assertion, it detonates. Standing
   exposure across the corpus, measured: gate-25 fires in 27 of 58 roots,
   gate-1 in 27, gate-7 in 13, gate-65 in 4.

## The list

| gate | name | category | reason |
|---|---|---|---|
| gate-4 | composer-audit | needs-external | Requires the `composer` binary on PATH **and** a network round-trip to the Packagist security-advisories API, since `composer audit --locked` resolves advisories remotely. A planted arm would additionally need a lock pinning a package with a live published CVE, which rots as advisories are superseded. |
| gate-12 | nc-input-labels | partial-elsewhere | `test_gate_a11y_helper_wiring.sh` plants a defect and asserts *"positive control: gate-12 FAILS on the fixture app"*, driven through the real wrapper — so this gate is NOT blind. What is missing is the anti-widening half: no suite asserts that a CORRECT `<NcSelect>` is silent. `test_gate_a11y_markup_scope.sh` has exactly that arm for twelve a11y gates and gate-12 is not among them, because its subject is a Vue component prop rather than PHP-template markup. A bundle would plant a multi-line `<NcSelect>` written after a `:reduce="(o) => o.id"` prop — the shape that defeated the old `[^>]*` extractor — and give the clean arm one carrying `inputLabel`. |
| gate-22 | manifest-validation | needs-external | ⚠️ **Reason corrected 2026-08-12; the previous one had rotted.** It read *"no `node_modules` ships anywhere in this package, so the clean arm cannot go green"*. That is no longer true of CI: `.github/workflows/hydra-gates-package.yml` runs `npm install --no-save ajv ajv-formats` BEFORE the helper-suite step, precisely so gates 22 and 53 validate with the real Ajv. Verified on 2026-08-12 that a schema-valid manifest returns clean and an invalid one returns thirteen errors. What actually blocks a bundle is different and is about the DRIVER: `test_gate_acceptance_matrix.sh` has no ajv preflight, so on a developer machine without ajv gate-22 reports `SKIPPED (wiring)` on both arms and the planted-arm assertion would report a WIRING fault as a gate defect. `test_gate_45_to_55_acceptance.sh` solves this for gate-53 with a preflight that aborts with exit 2 and says so; the acceptance driver needs the same before gate-22 can be bundled here. |
| gate-41 | html-lang | partial-elsewhere | `test_gate_a11y_helper_wiring.sh` plants a defect and asserts *"positive control: gate-41 FAILS on the fixture app"* through the real wrapper. The missing half is anti-widening: `test_gate_a11y_markup_scope.sh`'s clean PHP template emits no `<html>` element at all, so nothing anywhere asserts that a template WITH `lang=` is silent. A bundle would plant a `templates/standalone.php` emitting `<html>` with no `lang`, give the clean arm the same template with `lang`, and add a second clean template whose PHP COMMENT merely mentions `<html>` — pinning `php_template_scope.emitted_markup`. |
| gate-52 | custom-widget-ratchet | partial-elsewhere | `test_gate_45_to_55_acceptance.sh` plants a `kind:"widget"` component-registry entry with no `_note` and asserts *"gate-52 still catches a kind:\"widget\" entry with no `_note` → FAIL"*, plus a crashed-helper arm asserting `SKIPPED (wiring)` and *"gate-52 invents no finding count when the helper did not finish"*. The missing half is anti-widening: no arm asserts that a registry entry WITH a `_note` is silent, so a gate-52 widened to flag every widget would pass everything that exists today. A bundle would supply exactly that clean arm. The count-ratchet half of the gate additionally needs a base ref and stays out of scope for a fixture pair. |
