---
kind: code
---

## Why

ADR-118 (hydra, `openspec/architecture/adr-118-procedures-are-configuration.md`) records decisions 182, 184 and 185: a Dutch procedure ships as configuration, and code is generic and named by what it does. Decision 182 says a gate will refuse new classes named after a procedure.

On 10 October 2026 dossiq carried 229 procedure-named files and 109 standards-named files under `lib/` and `src/`. learniq, humaniq, shillinq, pipelinq, portaliq and filinq carry 28 procedure-named files between them. Each one arrived as a reasonable-looking class in a reasonable-looking pull request. Without a mechanical check the 230th arrives the same way, while the refactor programme is moving the first 229 out.

## What changes

- A new gate, **gate-119 `procedure-named-classes`**, in `conduction/hydra-gates`.
- A shared vocabulary at `hydra-gates/contracts/procedure-vocabulary.json` with two lists: procedure tokens and standard tokens.
- A per-app baseline file, `.hydra/procedure-names.json`, listing the procedure-named files that exist when the app adopts the gate, and the standards adapters the app is allowed to keep.
- The gate fails when a pull request adds a procedure-named file that is not in the baseline, or when the head count exceeds the base count.
- The gate reports standards-named files in a leaf app as a warning, and names integriq or filinq as their home.
- A `--write-baseline` mode generates the file, and a `--shrinkable` report lists baseline entries that no longer exist.

## Impact

- Every app with `lib/` or `src/` runs it. decidiq, integriq and openregister start at zero procedure-named files.
- dossiq starts at 229. The refactor lanes shrink the baseline as they delete classes.
- No existing file fails on adoption: the baseline is the current tree.

## Numbering

gate-117 is open in #782 and gate-118 in #836. This change takes 119. ADR-118 is the hydra ADR it enforces.
