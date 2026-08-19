# channel-parity

Spec for the base-ref delivery-channel fixture.

## Purpose

This spec exists to give gate-19 a subject in this fixture. The scenario below
carries NO traceability anchor and NO exclusion, so gate-19 must report it as
uncovered on any run that reads the whole tree — and must report it identically
whether the delta base arrived through `--base` or through the environment.

Do not add an anchor or an exclusion to this file. Either one makes the suite
that reads it vacuous: both arms would then agree at zero findings, and two arms
agreeing about nothing is exactly the shape `.github#416` hid behind.

## Requirements

### Requirement: the fixture declares one deliberately untraceable scenario

The scenario title below is unique in this package. It is what the suite greps
for, so a finding about any other subject cannot satisfy the assertion.

#### Scenario: ChannelParityUntracedScenario is reported by the whole-tree audit

- **GIVEN** a repository whose specs are unchanged from the delta base
- **WHEN** the gates run at full file scope with that base supplied
- **THEN** this scenario is reported as missing traceability, whichever channel carried the base
