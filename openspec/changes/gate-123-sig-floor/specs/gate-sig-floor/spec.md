## ADDED Requirements

### Requirement: A change keeps every floored 4-star check

The `sig-floor` gate SHALL measure the app at the head and at the merge base with gate 122's report and SHALL fail when a check in the floor is met at the base and missed at the head. The floor SHALL be the `checks` of `.github/sig-floor.json` read at the merge base, together with every 4-star check the merge base meets.

#### Scenario: A planted regression

- **GIVEN** opencatalogi's floor lists `php component_independence`
- **WHEN** a pull request lowers PHP component independence from 93.9% to 93.5%
- **THEN** the gate fails
- **AND** prints `php component_independence: 93.5% < limit 93.7%; met at the base (93.9%)`

#### Scenario: A refactor

- **WHEN** a pull request splits a unit and every check stays met
- **THEN** the gate passes and prints how many floored checks held

#### Scenario: A check met before the file lists it

- **GIVEN** development meets `php unit_size >60` and the floor file does not list it
- **WHEN** a pull request breaks it
- **THEN** the gate fails

### Requirement: The floor only rises

A pull request SHALL NOT lower the floor. The gate SHALL read the floor file from the base and SHALL fail when the head's file lacks a check the base's file lists. After a push to development that meets checks the file does not list, the workflow SHALL offer the raised file as a pull request that changes only that file.

#### Scenario: Removing a check from the file

- **WHEN** a pull request deletes `php unit_size >60` from `.github/sig-floor.json`
- **THEN** the gate fails and names the removed check

#### Scenario: Development meets one more check

- **WHEN** a push to development meets `php unit_size >15` for the first time
- **THEN** `sig-floor.proposed.json` lists it
- **AND** the `sig-floor-raise` job opens a pull request with the raised file

### Requirement: Inherited breaches do not fail unrelated changes

When the base already misses a floored check, the gate SHALL report it as inherited and SHALL NOT fail, unless the change makes that check's share worse.

#### Scenario: Development is already below its floor

- **GIVEN** development misses the floored `php unit_size >60`
- **WHEN** a pull request adds a small unit elsewhere
- **THEN** the gate passes and prints the check as inherited
- **WHEN** a pull request makes the largest unit longer
- **THEN** the gate fails

### Requirement: 5-star findings are reported and never block

The gate SHALL report every 5-star check (half of each 4-star limit) the head misses in its summary and in the step summary, and SHALL NOT fail on them.

#### Scenario: Between half the limit and the limit

- **WHEN** 8.3% of the PHP code is in units with 3 or more parameters
- **THEN** the 4-star check passes
- **AND** the summary lists `php unit_interfacing >2` as a 5-star finding

### Requirement: Scope and adoption

The gate SHALL measure exactly what gate 122 measures, including the app's `sigrid.yaml` excludes. Without a floor file the gate SHALL report NOT APPLICABLE and name the `write` command.

#### Scenario: No floor file

- **WHEN** the app has no `.github/sig-floor.json`
- **THEN** the gate reports NOT APPLICABLE

#### Scenario: An excluded directory

- **GIVEN** `sigrid.yaml` excludes `lib/Generated/`
- **WHEN** a pull request adds a 74-line unit there
- **THEN** the gate passes
