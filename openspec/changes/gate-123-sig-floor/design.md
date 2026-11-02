# Design: gate-123 sig-floor

## Checks

A check is one row of gate 122's report, named as `checks_of()` names it, per language: `unit_size >15/>30/>60`, `unit_complexity >5/>10/>25`, `unit_interfacing >2/>4/>6` (3+, 5+, 7+ parameters), `duplication`, and for PHP and Python `module_coupling >10/>20/>50` and `component_independence`. These are the checks the fleet measurement (M7, M8) counts, so a floor file and a fleet table speak the same names. Entanglement has no 4-star verdict in gate 122 and is not a check.

The measurement is gate 122's `build_report` with the same scope: tracked files, Sigrid's default excludes, test code, Nextcloud `js/` and `l10n/`, and the app's `sigrid.yaml` excludes. The jscpd cross-check feeds no check, so the floor skips it. The sigarch extension used by the fleet scripts adds informational numbers only and is not part of any check.

## The floor

```
floor = committed(.github/sig-floor.json at the merge base) ∪ met(merge base)
```

- Reading the file at the base means a pull request cannot lower its own floor.
- Adding the checks the base meets means a check development reaches is guarded at once, before any raise is merged. "The floor only rises" holds even while the raise pull request is open.
- On the adoption pull request the base has no file, and the head's file is the committed floor.
- On a run with no base (the drift sweep's dispatch), the floor is the file alone and every miss fails.

## Verdict

For each floored check the head misses:

| at the base | head versus base | verdict |
|---|---|---|
| met | any | FAIL: this change breaks it |
| missed (only possible via the file) | worse | FAIL: it erodes a floor development already breaks |
| missed | not worse | inherited: printed, not counted |

A check that disappears from the head (its language left the measured scope) fails, because nothing proves it is still met. A pull request that removes a check from the floor file fails as well.

Inherited breaches exist only after an admin merge past a red gate. They do not fail unrelated pull requests, in line with the inherited-debt rule; development fixes them forward.

## Raising the floor

The org ruleset requires a pull request with review on development, so a workflow cannot commit to it. After a push to development the gate writes `sig-floor.proposed.json` when the head meets checks the file does not list and nothing failed. The `sig-floor-raise` job opens `bot/sig-floor-<sha>` with that file as the only change and closes older raise pull requests.

The job declares no `permissions:` and inherits the caller's grant. A caller caps the permissions a called job may declare, and a job that asks for more makes the whole call fail to start. humaniq grants only contents and actions, so there the job pushes the branch and warns that it cannot open the pull request.

A pull request opened with `GITHUB_TOKEN` starts no workflow, so the raise carries no checks and an admin merges it. Nothing is lost while it waits, because the measured base already guards the new checks.

## Speed

lizard is the slow part (about 20 s for opencatalogi's 467 files on a loaded machine). Units are cached in `sig-units.json`, keyed by lizard version, extension, language and content. The base and the head share almost every file, so the base costs only the files the change touched. `actions/cache` restores the newest cache of the repository; only pushes save one, so pull requests read development's cache and add nothing to the cache store. The pinned lizard and jscpd install into the same cached directory.

## Output

- `[gate-123] sig-floor: PASS: N floored check(s) held; ...` or `FAIL: N floored check(s) lost ...`, with one line per lost check.
- `sig-floor.md`: a table of every check at base and head, its 4-star limit, whether it is floored, and its 5-star verdict. The workflow appends it to the step summary.
- `sig-floor.json`: the same as data.
