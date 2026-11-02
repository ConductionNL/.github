# Tasks: gate-123 sig-floor

## 1. Helper

- [x] 1.1 `hydra-gates/scripts/lib/check_sig_floor.py` with `check` and `write`, reusing gate 122's `build_report`, scope and check names
- [x] 1.2 `build_report` takes an optional unit reader and runs without jscpd
- [x] 1.3 Content-keyed unit cache (`--cache`)
- [x] 1.4 5-star rows in the summary, never blocking

## 2. Tests

- [x] 2.1 `test_check_sig_floor.py`: write, planted regression, refactor, base-met guard, inherited breach, lowered file, floor read from the base, no file, unrelated base, sigrid.yaml, 5-star, raise proposal, cache
- [x] 2.2 `test_gate123_sig_floor_scope.sh` through the real runner, registered in `COVERED-ELSEWHERE.md`

## 3. Wiring

- [x] 3.1 Gate 123 in `run-hydra-gates.sh`
- [x] 3.2 `quality.yml`: restore and save the measuring cache, publish `sig-floor.md` on every run, `sig-floor-raise` job
- [x] 3.3 Allowlist `sig-floor-raise` in the two shared-workflow guards (it renders no verdict)

## 4. Adoption

- [ ] 4.1 One pull request per fleet app with `.github/sig-floor.json` from its development head, together with `hydra-gates-sig-blocking: true`
