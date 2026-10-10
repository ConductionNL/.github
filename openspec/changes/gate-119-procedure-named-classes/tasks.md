# Tasks: gate-119 procedure-named-classes

Building is a separate step from this spec (refactor lane R10).

## 1. Vocabulary and helper

- [ ] 1.1 Add `hydra-gates/contracts/procedure-vocabulary.json` with the two lists from design.md
- [ ] 1.2 Add `hydra-gates/scripts/lib/check_procedure_named_classes.py`: tokenise paths, count at head and at `HYDRA_GATE_BASE_REF` (via `git ls-tree`, no checkout), compare with `.hydra/procedure-names.json`
- [ ] 1.3 `--write-baseline` and `--shrinkable` modes
- [ ] 1.4 Honour `@procedure-name exclude <reason>` through `exclusion_reason.is_reason_bearing()`

## 2. Tests and fixtures

- [ ] 2.1 `test_check_procedure_named_classes.py`: new file fails, rename fails, re-added deleted file fails on the count, move passes with a negative delta, JSON under `lib/Settings/` is ignored, standards file warns, bare exclusion marker counts
- [ ] 2.2 Planted fixture under `scripts/test-fixtures/` with one procedure file outside the baseline; the gate must fail on it

## 3. Wiring

- [ ] 3.1 Register gate-119 in `run-hydra-gates.sh`, with NOT APPLICABLE for repos without `lib/` and `src/`
- [ ] 3.2 Add the skill `hydra-gate-procedure-named-classes` to hydra `.claude/skills/`
- [ ] 3.3 Document the gate in `hydra-gates/README.md`

## 4. Adoption

- [ ] 4.1 One pull request per core app with `.hydra/procedure-names.json` from `--write-baseline`
- [ ] 4.2 Bump `conduction/hydra-gates` in each app after 4.1 lands
