## ADDED Requirements

### Requirement: A new procedure-named file fails the gate

The `procedure-named-classes` gate SHALL fail when a file under `lib/` or `src/` with a procedure token in its path exists at head and is not listed in the app's `.hydra/procedure-names.json` `procedure` array. JSON, `lib/Settings/`, `lib/Migration/` and `src/manifest*` SHALL NOT be counted.

#### Scenario: A new Woo service

- **GIVEN** dossiq's baseline does not list `lib/Service/WooThroughputService.php`
- **WHEN** a pull request adds that file
- **THEN** the gate fails
- **AND** prints the path and the token `woo`
- **AND** points at ADR-118

#### Scenario: Procedure names in a package are fine

- **WHEN** a pull request adds `lib/Settings/packages/woo-verzoek/terms.json`
- **THEN** the gate does not count it

#### Scenario: A rename keeps the procedure name

- **GIVEN** `lib/Service/WOODecisionService.php` is in the baseline
- **WHEN** a pull request moves it to `lib/Service/Woo/DecisionService.php`
- **THEN** the gate fails on the new path

### Requirement: The procedure count does not grow

The gate SHALL count procedure-named files at head and at `HYDRA_GATE_BASE_REF`. It SHALL fail when the head count is higher, and SHALL print base, head and delta on every run.

#### Scenario: A deleted file comes back

- **GIVEN** a previous pull request deleted `lib/Service/WOORedactionService.php` and left it in the baseline
- **WHEN** a later pull request adds the file again
- **THEN** the gate fails on the count, base 228 and head 229

#### Scenario: A move shrinks the count

- **WHEN** a pull request deletes eight bezwaar hearing classes and adds `lib/Service/Session/SessionService.php`
- **THEN** the gate passes and prints a delta of minus eight

### Requirement: Standards adapters are reported, not refused

A file with only a standard token SHALL NOT count as procedure. In a repo other than integriq, a standards file that is not in the baseline `standard` array SHALL produce a warning that names integriq, or filinq for signing, as its home. The warning SHALL NOT fail the gate.

#### Scenario: A new StUF class in dossiq

- **WHEN** a pull request adds `lib/Service/Stuf/StufAckParser.php` to dossiq
- **THEN** the gate warns that StUF adapters belong in integriq
- **AND** passes

### Requirement: Baseline tooling

The gate SHALL offer `--write-baseline`, which writes `.hydra/procedure-names.json` from the current tree, sorted, and `--shrinkable`, which lists baseline entries that no longer exist. Without a baseline file, the gate SHALL pass when the app has no procedure-named file, and SHALL fail with an instruction to run `--write-baseline` otherwise.

#### Scenario: First adoption

- **GIVEN** humaniq has no baseline file and 8 procedure-named files
- **WHEN** the gate runs
- **THEN** it fails and prints the `--write-baseline` command
- **WHEN** the lane runs `--write-baseline` and commits the file
- **THEN** the gate passes

### Requirement: A reason-bearing exclusion

A file carrying `@procedure-name exclude <reason>` in its first docblock or leading comment SHALL be left out of the head count and the new-file check. The reason SHALL pass `exclusion_reason.is_reason_bearing()`. A bare marker SHALL NOT count.

#### Scenario: A one-release shim

- **WHEN** `lib/Service/TermijnService.php` forwards to `lib/Service/Term/TermService.php` and carries `@procedure-name exclude forwards to TermService for one release, removed in 0.5`
- **THEN** the gate leaves it out of the count

### Requirement: Applicability

The gate SHALL report NOT APPLICABLE when the app has neither `lib/` nor `src/`. It SHALL be listed in `run-hydra-gates.sh` as gate-119 and SHALL take part in the COVERAGE line.

#### Scenario: A Python ExApp

- **WHEN** the gate runs on a repo with no `lib/` and no `src/`
- **THEN** it reports NOT APPLICABLE with that reason
