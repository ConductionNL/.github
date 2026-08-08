#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Prove the spec-to-test coverage gate CAN FAIL, and fails for the right reasons.

WHY
---
#189: `playwright-coverage-threshold` had never gated anything. Below-threshold
emitted `::warning::` and returned zero, so the job stayed green. pipelinq
declared a floor of 75, its run printed 28%, and the run passed. The issue's
closing requirement is the reason this file exists:

    "it needs a test that shows the gate CAN fail — a fixture with coverage
     below the threshold that turns the job red. Right now no such run can
     exist."

Two further defects are covered here because they are the reason the number was
not worth gating on in the first place:

  * the metric was `count(test() calls) / count(scenario headings)` — two
    independent totals. Ten unrelated tests raised it exactly as much as
    covering ten scenarios. `test_unrelated_tests_do_not_raise_coverage`
    pins that they no longer do.
  * zero scenarios scored **100%**, so the worst-covered repo and the best
    produced the same number. `test_zero_scenarios_is_not_a_pass` pins that
    it is now a failure to measure.

WHAT IS UNDER TEST
------------------
Not a copy of the program — THE program. The Node source is extracted out of
`.github/workflows/quality.yml` at run time (the `cat > … <<'SPEC_COVERAGE_JS'`
heredoc inside the "Generate spec-to-test coverage report" step) and executed.
A test against a transcription would pass happily while the shipped workflow
did something else; that is the failure mode this whole issue is about.

Usage:  test-spec-coverage-gate.py [workflow.yml]
        test-spec-coverage-gate.py --positive-control [workflow.yml]
Exit:   0 all assertions hold, 1 at least one failed.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

STEP_NAME = "Generate spec-to-test coverage report"
HEREDOC_OPEN = "<<'SPEC_COVERAGE_JS'"
HEREDOC_CLOSE = "SPEC_COVERAGE_JS"

FAILURES: list[str] = []
PASSES: list[str] = []


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
def extract_program(workflow: Path) -> str:
    """Pull the Node program out of the shipped workflow's heredoc."""
    data = yaml.safe_load(workflow.read_text())
    steps = data["jobs"]["playwright"]["steps"]
    run = None
    for step in steps:
        if step.get("name") == STEP_NAME:
            run = step.get("run")
            break
    if run is None:
        raise SystemExit(f"FATAL: no step named {STEP_NAME!r} in the playwright job")
    if HEREDOC_OPEN not in run:
        raise SystemExit(
            f"FATAL: step {STEP_NAME!r} no longer opens a {HEREDOC_OPEN} heredoc. "
            "If the program moved, move this extractor with it — a test that "
            "cannot find its subject must not report success."
        )

    lines = run.split("\n")
    start = next(i for i, ln in enumerate(lines) if HEREDOC_OPEN in ln) + 1
    end = next(i for i in range(start, len(lines)) if lines[i].strip() == HEREDOC_CLOSE)
    program = "\n".join(lines[start:end])
    if "process.exit(1)" not in program:
        raise SystemExit(
            "FATAL: the extracted program contains no `process.exit(1)`. A "
            "coverage gate with no non-zero exit is exactly the defect #189 "
            "reports; refusing to pretend this is testable."
        )
    return program


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def make_repo(root: Path, specs: dict[str, str], tests: dict[str, str]) -> None:
    for name, body in specs.items():
        write(root / "openspec" / "specs" / name / "spec.md", body)
    for name, body in tests.items():
        write(root / "tests" / "e2e" / name, body)


def run_program(program: str, repo: Path, threshold: str) -> tuple[int, str]:
    js = repo / "_spec-coverage.js"
    js.write_text(program)
    env = dict(os.environ)
    env["SPEC_COVERAGE_THRESHOLD"] = threshold
    env["PLAYWRIGHT_TEST_PATH"] = "tests/e2e"
    env["SPEC_COVERAGE_OUT"] = "playwright-coverage.json"
    proc = subprocess.run(
        ["node", str(js)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def report_json(repo: Path) -> dict:
    return json.loads((repo / "playwright-coverage.json").read_text())


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSES.append(label)
        print(f"  PASS  {label}")
    else:
        FAILURES.append(f"{label}{(' — ' + detail) if detail else ''}")
        print(f"  FAIL  {label}{(' — ' + detail) if detail else ''}")


# Four scenarios in one spec; exactly ONE carries an @e2e reference.
SPEC_FOUR = """# Widget spec

## Purpose
Four scenarios, one of them referenced from a test.

### Requirement: Widget behaviour

#### Scenario: Widget renders on the dashboard
- WHEN the dashboard loads
- THEN the widget is visible

#### Scenario: Widget refreshes on demand
- WHEN the refresh button is pressed
- THEN the widget reloads

#### Scenario: Widget shows an empty state
- WHEN there is no data
- THEN an empty state is shown

#### Scenario: Widget survives a failed request
- WHEN the request fails
- THEN an error is shown
"""

TEST_ONE_REF = """import { test, expect } from '@playwright/test';

// @e2e widget::widget-renders-on-the-dashboard
test('widget renders', async ({ page }) => {
  await page.goto('/');
});
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_below_threshold_fails(program: str, tmp: Path) -> None:
    """THE headline assertion of #189: below-threshold turns the job red."""
    repo = tmp / "below"
    make_repo(repo, {"widget": SPEC_FOUR}, {"widget.spec.ts": TEST_ONE_REF})
    code, out = run_program(program, repo, "75")
    rep = report_json(repo)

    check("below-threshold: exits NON-ZERO (the gate can fail)", code == 1, f"exit={code}")
    check("below-threshold: emits ::error:: not ::warning::",
          "::error::" in out and "::warning::" not in out)
    check("below-threshold: coverage is 25% (1 of 4 scenarios referenced)",
          rep["coverage"] == 25, f"got {rep['coverage']}")
    check("below-threshold: names the uncovered scenarios",
          "widget#widget-refreshes-on-demand" in out)


def test_at_threshold_passes(program: str, tmp: Path) -> None:
    """The same fixture must PASS under a floor it meets — or the gate is just
    a way of always failing, which is not a gate either."""
    repo = tmp / "at"
    make_repo(repo, {"widget": SPEC_FOUR}, {"widget.spec.ts": TEST_ONE_REF})
    code, out = run_program(program, repo, "25")
    check("at-threshold: exits ZERO", code == 0, f"exit={code}")
    check("at-threshold: says it meets the threshold",
          "meets the threshold" in out)


def test_zero_scenarios_is_not_a_pass(program: str, tmp: Path) -> None:
    """#189 defect 3: `scenarios.length === 0 ? … : 100` scored an unmeasured
    repo at 100%. It must now be a failure to measure."""
    repo = tmp / "zero"
    make_repo(repo, {}, {"smoke.spec.ts": "test('smoke', async () => {});\n"})
    (repo / "openspec" / "specs").mkdir(parents=True, exist_ok=True)
    code, out = run_program(program, repo, "0")
    rep = report_json(repo)

    check("zero-scenarios: exits NON-ZERO", code == 1, f"exit={code}")
    check("zero-scenarios: does NOT score 100", rep["coverage"] != 100,
          f"coverage={rep['coverage']}")
    check("zero-scenarios: coverage is null, not a number", rep["coverage"] is None)
    check("zero-scenarios: reports NOT MEASURABLE in words",
          "NOT MEASURABLE" in out)
    check("zero-scenarios: fails even at threshold 0",
          code == 1,
          "a threshold of 0 must not turn 'could not measure' into a pass")


def test_unrelated_tests_do_not_raise_coverage(program: str, tmp: Path) -> None:
    """#189 defect 2: under the old formula, ten unrelated `test()` calls raised
    the number exactly as much as covering ten scenarios. Pin that they do not."""
    baseline = tmp / "unrelated-a"
    make_repo(baseline, {"widget": SPEC_FOUR}, {"widget.spec.ts": TEST_ONE_REF})
    run_program(program, baseline, "0")
    before = report_json(baseline)["coverage"]

    padded = tmp / "unrelated-b"
    noise = "\n".join(
        f"test('unrelated noise {i}', async () => {{}});" for i in range(10)
    )
    make_repo(
        padded,
        {"widget": SPEC_FOUR},
        {"widget.spec.ts": TEST_ONE_REF, "noise.spec.ts": noise + "\n"},
    )
    run_program(program, padded, "0")
    after_rep = report_json(padded)

    check("unrelated tests: real coverage is UNCHANGED by 10 noise tests",
          before == after_rep["coverage"] == 25,
          f"before={before} after={after_rep['coverage']}")
    check("unrelated tests: the old ratio DID move (proving the fixture bites)",
          after_rep["testsPerScenarioPercent"] > 25,
          f"testsPerScenarioPercent={after_rep['testsPerScenarioPercent']}")
    check("unrelated tests: the old ratio is reported under an honest name",
          "testsPerScenarioPercent" in after_rep and "coverage" in after_rep)


def test_exclusions_leave_the_denominator(program: str, tmp: Path) -> None:
    """A reason-bearing `@e2e exclude` is the documented way out (gate-19's
    dialect). It must remove the scenario from the denominator, not count as
    covered — otherwise excluding everything would read as 100% tested."""
    spec = SPEC_FOUR.replace(
        "#### Scenario: Widget refreshes on demand\n",
        "#### Scenario: Widget refreshes on demand\n<!-- @e2e exclude server-side, covered by PHPUnit -->\n",
    )
    repo = tmp / "excl"
    make_repo(repo, {"widget": spec}, {"widget.spec.ts": TEST_ONE_REF})
    run_program(program, repo, "0")
    rep = report_json(repo)

    check("exclusions: one scenario is excluded", rep["excludedScenarios"] == 1,
          f"got {rep['excludedScenarios']}")
    check("exclusions: denominator drops to 3", rep["enforceableScenarios"] == 3,
          f"got {rep['enforceableScenarios']}")
    check("exclusions: coverage rises to 33% (1 of 3), not to 'covered'",
          rep["coverage"] == 33, f"got {rep['coverage']}")


def test_whole_spec_exclusion(program: str, tmp: Path) -> None:
    """A whole-spec exclusion voids every scenario in the file — and with only
    that spec present, the result must be NOT MEASURABLE rather than 100%."""
    spec = SPEC_FOUR.replace(
        "## Purpose\n",
        "## Purpose\n\n@e2e exclude pure backend spec, covered by PHPUnit\n",
    )
    repo = tmp / "whole"
    make_repo(repo, {"widget": spec}, {"widget.spec.ts": TEST_ONE_REF})
    code, out = run_program(program, repo, "0")
    rep = report_json(repo)

    check("whole-spec exclude: all 4 scenarios excluded",
          rep["excludedScenarios"] == 4, f"got {rep['excludedScenarios']}")
    check("whole-spec exclude: nothing enforceable left is NOT MEASURABLE",
          rep["measurable"] is False and code == 1 and "NOT MEASURABLE" in out)


def test_format_b_numbered_scenarios(program: str, tmp: Path) -> None:
    """gate-19's Format B: numbered GIVEN/WHEN items under a `**Scenarios:**`
    marker, addressed as `<req-slug>-scenario-<n>`."""
    spec = """# Decomposition spec

## Purpose
Format B scenarios.

### REQ-DECOMP-001: Settings controller decomposition

**Scenarios:**

1. **GIVEN** a fat controller **WHEN** it is split **THEN** each part is testable
2. **GIVEN** a split controller **WHEN** routes resolve **THEN** behaviour is unchanged
"""
    test = """import { test } from '@playwright/test';
// @e2e decomp::settings-controller-decomposition-scenario-1
test('decomp', async () => {});
"""
    repo = tmp / "fmtb"
    make_repo(repo, {"decomp": spec}, {"decomp.spec.ts": test})
    run_program(program, repo, "0")
    rep = report_json(repo)

    check("format B: two numbered scenarios found", rep["specScenarios"] == 2,
          f"got {rep['specScenarios']}")
    check("format B: the referenced one is covered", rep["coveredScenarios"] == 1,
          f"got {rep['coveredScenarios']}")
    check("format B: coverage is 50%", rep["coverage"] == 50, f"got {rep['coverage']}")


def test_exclude_is_not_a_reference(program: str, tmp: Path) -> None:
    """`@e2e exclude …` inside a TEST file is a directive, not a scenario
    reference. Reading it as one would let a bare `@e2e exclude` in a test
    mark an arbitrary scenario covered."""
    test = """import { test } from '@playwright/test';
// @e2e exclude widget-renders-on-the-dashboard
test('nothing', async () => {});
"""
    repo = tmp / "excl-ref"
    make_repo(repo, {"widget": SPEC_FOUR}, {"widget.spec.ts": test})
    run_program(program, repo, "0")
    rep = report_json(repo)
    check("exclude-in-test: contributes no @e2e reference",
          rep["e2eReferences"] == 0, f"got {rep['e2eReferences']}")
    check("exclude-in-test: nothing is marked covered",
          rep["coveredScenarios"] == 0, f"got {rep['coveredScenarios']}")


TESTS = [
    test_below_threshold_fails,
    test_at_threshold_passes,
    test_zero_scenarios_is_not_a_pass,
    test_unrelated_tests_do_not_raise_coverage,
    test_exclusions_leave_the_denominator,
    test_whole_spec_exclusion,
    test_format_b_numbered_scenarios,
    test_exclude_is_not_a_reference,
]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workflow", nargs="?", default=".github/workflows/quality.yml")
    ap.add_argument(
        "--positive-control",
        action="store_true",
        help="Neuter the gate's non-zero exit and assert THIS SUITE then fails. "
        "A suite that cannot fail is the same defect it is testing for.",
    )
    args = ap.parse_args(argv)

    workflow = Path(args.workflow)
    if not workflow.is_file():
        print(f"FATAL: {workflow} not found")
        return 1

    if shutil.which("node") is None:
        print("FATAL: node is not on PATH — cannot execute the program under test")
        return 1

    program = extract_program(workflow)
    print(f"Extracted {len(program.splitlines())} lines of Node from "
          f"{workflow}:jobs.playwright.steps[{STEP_NAME!r}]")

    if args.positive_control:
        # Turn every hard exit back into the warning-only behaviour #189
        # describes. The suite MUST go red; if it stays green it is not
        # measuring the exit status at all.
        program = program.replace("process.exit(1)", "process.exit(0)")
        program = program.replace("::error::", "::warning::")
        print("POSITIVE CONTROL: gate neutered to warning-only (the #189 behaviour).")

    print()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for fn in TESTS:
            print(f"{fn.__name__}:")
            try:
                fn(program, tmp)
            except Exception as exc:  # noqa: BLE001
                FAILURES.append(f"{fn.__name__} raised {exc!r}")
                print(f"  FAIL  raised {exc!r}")
            print()

    print(f"{len(PASSES)} passed, {len(FAILURES)} failed")

    if args.positive_control:
        if FAILURES:
            print(
                "\nOK — the suite FAILS when the gate is neutered. "
                "Its clean pass is a verdict."
            )
            return 0
        print(
            "\nFAIL — the suite stayed GREEN with the gate neutered. It is not "
            "measuring enforcement."
        )
        return 1

    if FAILURES:
        print("\nFailures:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1

    print("\nOK — the spec-to-test coverage gate enforces, and can fail.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
