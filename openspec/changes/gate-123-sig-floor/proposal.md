---
kind: code
---

## Why

Gate 122 (sig-maintainability) judges single units: a unit a change adds or makes worse must stay under NLOC 60, McCabe 10 and 5 parameters. It does not see the app's whole risk profile. A change can keep every unit under those bounds and still push an app over a 4-star limit, for example by adding many 40-line units (unit size >30), by exposing more code across components (component independence), or by copying a fragment that jscpd's 30-token minimum misses.

On 2 November 2026 Ruben decided that every SIG 4-star check an app already meets must still be met after each pull request, and that this floor only rises. Replaying today's opencatalogi development shows why: merge #2283 lowered PHP component independence from 93.9% to 93.5%, under the 93.7% limit, and no check noticed.

## What changes

- A new gate, **gate-123 `sig-floor`**, in `conduction/hydra-gates`, helper `scripts/lib/check_sig_floor.py`.
- A committed floor file per app, `.github/sig-floor.json`, listing the 4-star checks the app meets, under gate 122's check names. `check_sig_floor.py write .` generates it.
- On every run the gate measures the head and the merge base with gate 122's report. The floor is the committed file read at the base, plus every check the base meets. A floored check the head misses fails the gate and is named with its share and limit.
- The 5-star checks (gate 122's five-star profile, half of every 4-star limit) are reported in the step summary and never block.
- A `sig-floor-raise` job in `quality.yml` opens a pull request with the raised floor file after a push to development that meets more checks.
- A unit cache keyed by file content, restored by `actions/cache`, so a pull request re-reads only the files it changed.

## Impact

- Apps without a floor file: NOT APPLICABLE, nothing changes.
- The 20 fleet apps get a floor file in one small pull request each, generated from their development head.
- The hydra-gates job gains one measurement of the head and one of the merge base, without jscpd.
