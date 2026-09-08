# Ghost Sync

## Purpose

One requirement, one scenario, one exclusion. The exclusion cites a PHPUnit
class by name. Whether that class exists here is the only thing that differs
between the two arms of this fixture.

## Requirements

### Requirement: Ghost reconciliation [MVP]
The system MUST drop a ghost row when its source object is gone.

#### Scenario: A ghost row is dropped when its source is gone
@e2e exclude reconciliation runs below the HTTP surface, asserted by GhostServiceTest::testGhostRowIsDropped
- **GIVEN** a ghost row whose source object has been deleted
- **WHEN** reconciliation runs
- **THEN** the ghost row MUST be dropped
