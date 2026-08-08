#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_e2e_coverage. Run with:

    python3 scripts/lib/test_check_e2e_coverage.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_e2e_coverage as cec  # noqa: E402


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Slug tests
# ---------------------------------------------------------------------------

class SlugTest(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(cec._slugify("Widget receives context on a detail page"),
                         "widget-receives-context-on-a-detail-page")

    def test_punctuation_stripped(self):
        self.assertEqual(cec._slugify("OR is not installed or unreachable"),
                         "or-is-not-installed-or-unreachable")

    def test_leading_trailing_stripped(self):
        self.assertEqual(cec._slugify("  Hello World  "), "hello-world")

    def test_special_chars(self):
        self.assertEqual(cec._slugify("Valid schema declaration present"),
                         "valid-schema-declaration-present")


# ---------------------------------------------------------------------------
# Spec parsing tests
# ---------------------------------------------------------------------------

BASIC_SPEC = """\
# my-spec Specification

## Purpose

This spec covers things.

### Requirement: Foo behaviour

Foo shall do bar.

#### Scenario: Foo does bar

- WHEN foo is called
- THEN bar happens

#### Scenario: Foo handles error

- WHEN foo fails
- THEN error is logged
"""

SPEC_WITH_EXCLUSION = """\
# my-spec Specification

## Purpose

### Requirement: Plumbing

#### Scenario: Internal wiring

@e2e exclude pure plumbing, verified by PHPUnit

- WHEN the wiring is set up
- THEN it connects

#### Scenario: Another covered

- WHEN something visible happens
- THEN it shows in the UI
"""

SPEC_WITH_BARE_EXCLUDE = """\
# my-spec Specification

## Purpose

### Requirement: Sneaky

#### Scenario: Hidden

@e2e exclude

- WHEN hidden
- THEN nothing
"""

WHOLE_SPEC_EXCLUDED = """\
# backend-spec Specification

## Purpose

@e2e exclude pure-backend API contract, covered by Newman

### Requirement: API endpoint

#### Scenario: Returns 200 on success

- WHEN the API is called
- THEN status 200 is returned

#### Scenario: Returns 404 when not found

- WHEN the resource does not exist
- THEN status 404 is returned
"""

REQUIREMENT_LEVEL_EXCLUDE = """\
# my-spec Specification

## Purpose

### Requirement: Background job

@e2e exclude background-only, not UI-observable

#### Scenario: Job runs at midnight

- WHEN the cron triggers
- THEN the job executes

#### Scenario: Job logs output

- WHEN the job finishes
- THEN a log entry is created
"""

# ---- Format B (alternative numbered scenario format) ----

ALT_FORMAT_BASIC = """\
# method-decomp Specification

## Purpose

Decompose complex methods.

### REQ-DECOMP-001: SettingsController Decomposition

The controller MUST be decomposed.

**Scenarios:**

1. **GIVEN** the controller has >10 deps **WHEN** decomposed **THEN** handlers are created.

2. **GIVEN** handlers exist **WHEN** tests run **THEN** all tests pass.

### REQ-DECOMP-002: EventListener Decomposition

The listener MUST be split.

**Scenarios:**

1. **GIVEN** the listener is monolithic **WHEN** decomposed **THEN** three handlers created.
"""

ALT_FORMAT_WITH_EXCLUSION = """\
# method-decomp Specification

## Purpose

### REQ-DECOMP-001: SettingsController Decomposition

**Scenarios:**

1. **GIVEN** something **WHEN** done **THEN** result.
@e2e exclude pure backend refactoring, no UI surface

2. **GIVEN** something else **WHEN** done **THEN** visible result.
"""

ALT_FORMAT_BARE_EXCLUDE = """\
# method-decomp Specification

## Purpose

### REQ-DECOMP-001: SettingsController Decomposition

**Scenarios:**

1. **GIVEN** something **WHEN** done **THEN** result.
@e2e exclude
"""

ALT_FORMAT_REQUIREMENT_LEVEL_EXCLUDE = """\
# method-decomp Specification

## Purpose

### REQ-DECOMP-001: Background Processor

@e2e exclude background-only, not UI-observable

**Scenarios:**

1. **GIVEN** cron fires **WHEN** job runs **THEN** log entry created.

2. **GIVEN** job finishes **WHEN** checked **THEN** status is done.
"""

ALT_FORMAT_WHOLE_SPEC_EXCLUDED = """\
# backend-spec Specification

## Purpose

@e2e exclude pure-backend, covered by Newman

### REQ-DECOMP-001: API Endpoint

**Scenarios:**

1. **GIVEN** the API is called **WHEN** valid **THEN** 200 returned.

2. **GIVEN** the API is called **WHEN** missing **THEN** 404 returned.
"""

ALT_FORMAT_MIXED = """\
# mixed-spec Specification

## Purpose

### Requirement: Classic requirement

#### Scenario: Classic scenario one

- WHEN classic
- THEN result

### REQ-ALT-001: Alt format requirement

The system MUST do things.

**Scenarios:**

1. **GIVEN** alt setup **WHEN** alt action **THEN** alt result.

2. **GIVEN** another alt **WHEN** another action **THEN** another result.
"""


class ParseSpecTest(unittest.TestCase):
    def _parse(self, content: str, spec_name: str = "my-spec") -> list[dict]:
        root = Path(tempfile.mkdtemp())
        try:
            p = _write(root, f"openspec/specs/{spec_name}/spec.md", content)
            return cec.parse_spec_scenarios(p)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_basic_two_scenarios(self):
        scenarios = self._parse(BASIC_SPEC)
        self.assertEqual(len(scenarios), 2)
        self.assertEqual(scenarios[0]["slug"], "foo-does-bar")
        self.assertEqual(scenarios[1]["slug"], "foo-handles-error")
        self.assertEqual(scenarios[0]["ref"], "my-spec::foo-does-bar")
        for s in scenarios:
            self.assertFalse(s["excluded"])
            self.assertFalse(s["bare_exclude"])

    def test_scenario_exclusion_with_reason(self):
        scenarios = self._parse(SPEC_WITH_EXCLUSION)
        self.assertEqual(len(scenarios), 2)
        hidden = next(s for s in scenarios if s["slug"] == "internal-wiring")
        visible = next(s for s in scenarios if s["slug"] == "another-covered")
        self.assertTrue(hidden["excluded"])
        self.assertFalse(hidden["bare_exclude"])
        self.assertEqual(hidden["exclude_reason"], "pure plumbing, verified by PHPUnit")
        self.assertFalse(visible["excluded"])

    def test_bare_exclude_is_noncompliant(self):
        scenarios = self._parse(SPEC_WITH_BARE_EXCLUDE)
        self.assertEqual(len(scenarios), 1)
        s = scenarios[0]
        self.assertTrue(s["excluded"])
        self.assertTrue(s["bare_exclude"])
        self.assertIsNone(s["exclude_reason"])

    def test_whole_spec_exclusion(self):
        scenarios = self._parse(WHOLE_SPEC_EXCLUDED, spec_name="backend-spec")
        self.assertEqual(len(scenarios), 2)
        for s in scenarios:
            self.assertTrue(s["excluded"], f"scenario {s['slug']} should be excluded")
            self.assertFalse(s["bare_exclude"])

    def test_requirement_level_exclusion(self):
        scenarios = self._parse(REQUIREMENT_LEVEL_EXCLUDE)
        self.assertEqual(len(scenarios), 2)
        for s in scenarios:
            self.assertTrue(s["excluded"])
            self.assertFalse(s["bare_exclude"])

    # ------------------------------------------------------------------ #
    # Format B — numbered **Scenarios:** list
    # ------------------------------------------------------------------ #

    def test_alt_format_basic_counted(self):
        """Alt-format numbered scenarios are counted (not silently zero)."""
        scenarios = self._parse(ALT_FORMAT_BASIC, spec_name="method-decomp")
        self.assertEqual(len(scenarios), 3)
        slugs = [s["slug"] for s in scenarios]
        self.assertIn("req-decomp-001-settingscontroller-decomposition-scenario-1", slugs)
        self.assertIn("req-decomp-001-settingscontroller-decomposition-scenario-2", slugs)
        self.assertIn("req-decomp-002-eventlistener-decomposition-scenario-1", slugs)
        for s in scenarios:
            self.assertFalse(s["excluded"])
            self.assertFalse(s["bare_exclude"])

    def test_alt_format_slug_convention(self):
        """Slug is <parent-req-slug>-scenario-<n>, deterministic from req heading."""
        scenarios = self._parse(ALT_FORMAT_BASIC, spec_name="method-decomp")
        s1 = next(s for s in scenarios if "scenario-1" in s["slug"]
                  and "settingscontroller" in s["slug"])
        self.assertEqual(
            s1["slug"],
            "req-decomp-001-settingscontroller-decomposition-scenario-1",
        )
        self.assertEqual(
            s1["ref"],
            "method-decomp::req-decomp-001-settingscontroller-decomposition-scenario-1",
        )

    def test_alt_format_scenario_level_exclusion(self):
        """@e2e exclude inside an alt-format numbered item excludes only that item."""
        scenarios = self._parse(ALT_FORMAT_WITH_EXCLUSION, spec_name="method-decomp")
        self.assertEqual(len(scenarios), 2)
        excluded_s = next(s for s in scenarios if s["slug"].endswith("-scenario-1"))
        visible_s = next(s for s in scenarios if s["slug"].endswith("-scenario-2"))
        self.assertTrue(excluded_s["excluded"])
        self.assertFalse(excluded_s["bare_exclude"])
        self.assertEqual(excluded_s["exclude_reason"], "pure backend refactoring, no UI surface")
        self.assertFalse(visible_s["excluded"])

    def test_alt_format_bare_exclude_noncompliant(self):
        """A bare @e2e exclude inside an alt-format item is non-compliant."""
        scenarios = self._parse(ALT_FORMAT_BARE_EXCLUDE, spec_name="method-decomp")
        self.assertEqual(len(scenarios), 1)
        s = scenarios[0]
        self.assertTrue(s["excluded"])
        self.assertTrue(s["bare_exclude"])
        self.assertIsNone(s["exclude_reason"])

    def test_alt_format_requirement_level_exclusion(self):
        """@e2e exclude on a ### REQ-... heading inherits to all its numbered scenarios."""
        scenarios = self._parse(ALT_FORMAT_REQUIREMENT_LEVEL_EXCLUDE, spec_name="method-decomp")
        self.assertEqual(len(scenarios), 2)
        for s in scenarios:
            self.assertTrue(s["excluded"], f"{s['slug']} should be excluded")
            self.assertFalse(s["bare_exclude"])

    def test_alt_format_whole_spec_exclusion(self):
        """Whole-spec @e2e exclude covers alt-format numbered scenarios."""
        scenarios = self._parse(ALT_FORMAT_WHOLE_SPEC_EXCLUDED, spec_name="backend-spec")
        self.assertEqual(len(scenarios), 2)
        for s in scenarios:
            self.assertTrue(s["excluded"], f"{s['slug']} should be excluded")
            self.assertFalse(s["bare_exclude"])

    def test_mixed_format_both_counted(self):
        """A spec may use both Format A (#### Scenario:) and Format B in different requirements."""
        scenarios = self._parse(ALT_FORMAT_MIXED, spec_name="mixed-spec")
        self.assertEqual(len(scenarios), 3)
        slugs = [s["slug"] for s in scenarios]
        # Format A scenario present
        self.assertIn("classic-scenario-one", slugs)
        # Format B scenarios present
        self.assertIn("req-alt-001-alt-format-requirement-scenario-1", slugs)
        self.assertIn("req-alt-001-alt-format-requirement-scenario-2", slugs)


# ---------------------------------------------------------------------------
# Covered-ref collection
# ---------------------------------------------------------------------------

class CoveredRefTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_long_form_annotation(self):
        _write(self.root, "tests/e2e/foo.spec.ts",
               "// @e2e openspec/specs/my-spec/spec.md#foo-does-bar\ntest('x', async ({ page }) => { await expect(page).toHaveTitle(/x/) })\n")
        refs = cec.collect_covered_refs(self.root)
        self.assertIn("my-spec::foo-does-bar", refs)

    def test_short_form_annotation(self):
        _write(self.root, "tests/e2e/foo.spec.ts",
               "// @e2e my-spec::foo-does-bar\ntest('x', async ({ page }) => { await expect(page).toHaveTitle(/x/) })\n")
        refs = cec.collect_covered_refs(self.root)
        self.assertIn("my-spec::foo-does-bar", refs)

    def test_both_forms_same_file(self):
        _write(self.root, "tests/e2e/bar.spec.js",
               "// @e2e my-spec::foo-does-bar\n// @e2e openspec/specs/my-spec/spec.md#foo-handles-error\n")
        refs = cec.collect_covered_refs(self.root)
        self.assertIn("my-spec::foo-does-bar", refs)
        self.assertIn("my-spec::foo-handles-error", refs)

    def test_subdirectory_e2e(self):
        _write(self.root, "tests/e2e/spec-coverage/deep.spec.ts",
               "// @e2e my-spec::foo-does-bar\n")
        refs = cec.collect_covered_refs(self.root)
        self.assertIn("my-spec::foo-does-bar", refs)

    def test_non_spec_file_ignored(self):
        _write(self.root, "tests/e2e/helpers.ts",
               "// @e2e my-spec::foo-does-bar\n")
        refs = cec.collect_covered_refs(self.root)
        # helpers.ts is not *.spec.ts / *.test.ts → should not be scanned
        self.assertNotIn("my-spec::foo-does-bar", refs)

    def test_no_e2e_dir(self):
        refs = cec.collect_covered_refs(self.root)
        self.assertEqual(refs, set())


# ---------------------------------------------------------------------------
# Report mode
# ---------------------------------------------------------------------------

class ReportModeTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_report_counts(self):
        _write(self.root, "openspec/specs/my-spec/spec.md", BASIC_SPEC)
        # Cover the first scenario
        _write(self.root, "tests/e2e/foo.spec.ts",
               "// @e2e my-spec::foo-does-bar\ntest('x', async ({ page }) => { await expect(page).toHaveTitle(/x/) })\n")

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cec.run_report(self.root)
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["mode"], "report")
        self.assertEqual(data["totals"]["scenarios"], 2)
        self.assertEqual(data["totals"]["covered"], 1)
        self.assertEqual(data["totals"]["uncovered"], 1)
        self.assertEqual(data["totals"]["excluded"], 0)
        self.assertEqual(len(data["uncovered"]), 1)
        self.assertEqual(data["uncovered"][0]["ref"], "my-spec::foo-handles-error")

    def test_report_with_exclusion(self):
        _write(self.root, "openspec/specs/my-spec/spec.md", SPEC_WITH_EXCLUSION)
        _write(self.root, "tests/e2e/foo.spec.ts",
               "// @e2e my-spec::another-covered\ntest('x', async ({ page }) => { await expect(page).toHaveTitle(/x/) })\n")

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cec.run_report(self.root)
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["totals"]["excluded"], 1)
        self.assertEqual(data["totals"]["covered"], 1)
        self.assertEqual(data["totals"]["uncovered"], 0)

    def test_report_no_specs_dir(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cec.run_report(self.root)
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["totals"]["scenarios"], 0)


# ---------------------------------------------------------------------------
# Gate mode (full integration with a real git repo)
# ---------------------------------------------------------------------------

class GateModeTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self._run("git", "init", "-q")
        self._run("git", "config", "user.email", "t@t.nl")
        self._run("git", "config", "user.name", "t")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _run(self, *args: str) -> None:
        subprocess.run(args, cwd=str(self.root), check=True,
                       capture_output=True, text=True)

    def _commit(self, msg: str = "commit") -> str:
        self._run("git", "add", "-A")
        self._run("git", "commit", "-q", "-m", msg)
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(self.root), capture_output=True, text=True
        ).stdout.strip()

    def test_pass_when_no_spec_files_in_diff(self):
        # Baseline commit, then change a non-spec file
        _write(self.root, "src/index.ts", "export const x = 1\n")
        base = self._commit("base")
        _write(self.root, "src/index.ts", "export const x = 2\n")
        self._commit("change")

        os.environ["HYDRA_GATE_BASE_REF"] = base
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cec.run_gate(self.root)
        finally:
            del os.environ["HYDRA_GATE_BASE_REF"]

        self.assertEqual(rc, 0)
        self.assertIn("PASS", buf.getvalue())

    def test_the_status_never_wraps_to_zero_while_findings_exist(self):
        # An exit status is one byte. Returning the raw count meant 266
        # findings left as 10 — and 256 findings left as 0, which the bash
        # gate reads as PASS. Any multiple of 256 was a silent green.
        _write(self.root, "README.md", "# app\n")
        base = self._commit("base")
        spec = ["# S\n\n## Requirements\n\n### Requirement: R\n"]
        for i in range(256):
            spec.append(f"\n#### Scenario: scenario number {i}\n\n- **WHEN** x happens\n")
        _write(self.root, "openspec/specs/s/spec.md", "".join(spec))
        self._commit("add spec")

        os.environ["HYDRA_GATE_BASE_REF"] = base
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cec.run_gate(self.root)
        finally:
            del os.environ["HYDRA_GATE_BASE_REF"]

        self.assertNotEqual(rc, 0, "256 findings must not exit 0")
        self.assertLessEqual(rc, 255, "an exit status is one byte")
        # The TRUE number still has to reach the reader, which is why the
        # bash gate reports the printed summary rather than the status.
        self.assertIn("256 scenario(s) without a running e2e test", buf.getvalue())

    def test_the_clamp_does_not_turn_a_clean_spec_into_a_failure(self):
        # THE CONTROL for the clamp.
        _write(self.root, "README.md", "# app\n")
        base = self._commit("base")
        _write(self.root, "openspec/specs/s/spec.md",
               "# S\n\n## Requirements\n\n### Requirement: R\n\n"
               "#### Scenario: only one\n\n- **WHEN** x happens\n"
               "- @e2e exclude backend only — covered by PHPUnit\n")
        self._commit("add spec")

        os.environ["HYDRA_GATE_BASE_REF"] = base
        try:
            with redirect_stdout(io.StringIO()):
                rc = cec.run_gate(self.root)
        finally:
            del os.environ["HYDRA_GATE_BASE_REF"]
        self.assertEqual(rc, 0)

    def test_fail_uncovered_scenario_in_diff(self):
        # Baseline: nothing
        _write(self.root, "README.md", "# app\n")
        base = self._commit("base")
        # PR adds a spec with two scenarios and no e2e tests
        _write(self.root, "openspec/specs/my-spec/spec.md", BASIC_SPEC)
        self._commit("add spec")

        os.environ["HYDRA_GATE_BASE_REF"] = base
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cec.run_gate(self.root)
        finally:
            del os.environ["HYDRA_GATE_BASE_REF"]

        self.assertEqual(rc, 2)
        out = buf.getvalue()
        self.assertIn("missing @e2e", out)
        self.assertIn("FAIL", out)
        self.assertIn("2 scenario(s)", out)

    def test_pass_when_all_scenarios_covered(self):
        _write(self.root, "README.md", "# app\n")
        base = self._commit("base")
        _write(self.root, "openspec/specs/my-spec/spec.md", BASIC_SPEC)
        _write(self.root, "tests/e2e/my.spec.ts",
               "// @e2e my-spec::foo-does-bar\n// @e2e my-spec::foo-handles-error\ntest('x', async ({ page }) => { await expect(page).toHaveTitle(/x/) })\n")
        self._commit("add spec + tests")

        os.environ["HYDRA_GATE_BASE_REF"] = base
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cec.run_gate(self.root)
        finally:
            del os.environ["HYDRA_GATE_BASE_REF"]

        self.assertEqual(rc, 0)
        self.assertIn("PASS", buf.getvalue())

    def test_fail_bare_exclude_is_noncompliant(self):
        _write(self.root, "README.md", "# app\n")
        base = self._commit("base")
        _write(self.root, "openspec/specs/my-spec/spec.md", SPEC_WITH_BARE_EXCLUDE)
        self._commit("add spec with bare exclude")

        os.environ["HYDRA_GATE_BASE_REF"] = base
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cec.run_gate(self.root)
        finally:
            del os.environ["HYDRA_GATE_BASE_REF"]

        self.assertEqual(rc, 1)
        out = buf.getvalue()
        self.assertIn("exclude without reason", out)

    def test_pass_exclude_with_reason(self):
        _write(self.root, "README.md", "# app\n")
        base = self._commit("base")
        _write(self.root, "openspec/specs/my-spec/spec.md", SPEC_WITH_EXCLUSION)
        # Only the non-excluded scenario needs coverage
        _write(self.root, "tests/e2e/my.spec.ts",
               "// @e2e my-spec::another-covered\ntest('x', async ({ page }) => { await expect(page).toHaveTitle(/x/) })\n")
        self._commit("add spec + test for visible scenario")

        os.environ["HYDRA_GATE_BASE_REF"] = base
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cec.run_gate(self.root)
        finally:
            del os.environ["HYDRA_GATE_BASE_REF"]

        self.assertEqual(rc, 0)
        self.assertIn("PASS", buf.getvalue())

    def test_whole_spec_exclude_passes_all_scenarios(self):
        _write(self.root, "README.md", "# app\n")
        base = self._commit("base")
        _write(self.root, "openspec/specs/backend-spec/spec.md", WHOLE_SPEC_EXCLUDED)
        self._commit("add backend-only spec")

        os.environ["HYDRA_GATE_BASE_REF"] = base
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cec.run_gate(self.root)
        finally:
            del os.environ["HYDRA_GATE_BASE_REF"]

        self.assertEqual(rc, 0)
        self.assertIn("PASS", buf.getvalue())

    def test_diff_scope_only_changed_spec_flagged(self):
        """A spec not touched in the diff must NOT be flagged even if uncovered."""
        # Baseline: existing uncovered spec
        _write(self.root, "openspec/specs/old-spec/spec.md",
               "# old-spec Spec\n## Purpose\n### Requirement: Old\n#### Scenario: Old one\n- WHEN old\n- THEN nothing\n")
        base = self._commit("base with uncovered spec")

        # PR only touches an unrelated file
        _write(self.root, "src/index.ts", "export const x = 1\n")
        self._commit("add source file")

        os.environ["HYDRA_GATE_BASE_REF"] = base
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cec.run_gate(self.root)
        finally:
            del os.environ["HYDRA_GATE_BASE_REF"]

        # old-spec is not in the diff → should not be flagged
        self.assertEqual(rc, 0)
        self.assertNotIn("old-spec", buf.getvalue())


# ---------------------------------------------------------------------------
# A PERMANENTLY-SKIPPED TEST IS NOT COVERAGE
#
# decidesk carried four tests with EMPTY BODIES and a hardcoded
# `test.skip(true, ...)`, each tagged `@e2e`, each counted as traceability,
# together asserting nothing. A gate that accepts a switched-off test as proof
# is a dead gate by construction.
#
# The discriminator is the ARGUMENT, not the call: `test.skip(true)` is a test
# someone turned off; `test.skip(browserName === 'firefox')` is a real test
# with a runtime guard, and it runs everywhere else. Both ways, in one class.
# ---------------------------------------------------------------------------
class SkippedTestIsNotCoverageTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _refs(self, body: str) -> set:
        _write(self.root, "tests/e2e/foo.spec.ts", body)
        return cec.collect_covered_refs(self.root)

    # --- dead: must NOT count -------------------------------------------
    def test_hardcoded_skip_true_with_empty_body_does_not_count(self):
        # The decidesk shape, verbatim.
        self.assertEqual(self._refs(
            "// @e2e my-spec::foo-does-bar\n"
            "test('minutes are published', async ({ page }) => {\n"
            "  test.skip(true, 'pending backend work')\n"
            "})\n"), set())

    def test_skip_modifier_does_not_count(self):
        self.assertEqual(self._refs(
            "// @e2e my-spec::foo-does-bar\n"
            "test.skip('minutes are published', async ({ page }) => {\n"
            "  await expect(page).toHaveTitle(/x/)\n"
            "})\n"), set())

    def test_xit_does_not_count(self):
        self.assertEqual(self._refs(
            "// @e2e my-spec::foo-does-bar\n"
            "xit('minutes are published', async () => { await go() })\n"), set())

    def test_fixme_does_not_count(self):
        self.assertEqual(self._refs(
            "// @e2e my-spec::foo-does-bar\n"
            "test.fixme('broken', async () => { await go() })\n"), set())

    def test_empty_body_does_not_count(self):
        self.assertEqual(self._refs(
            "// @e2e my-spec::foo-does-bar\n"
            "test('minutes are published', async ({ page }) => {})\n"), set())

    def test_a_body_of_only_comments_does_not_count(self):
        self.assertEqual(self._refs(
            "// @e2e my-spec::foo-does-bar\n"
            "test('later', async () => {\n"
            "  // TODO: write this once the endpoint lands\n"
            "  /* nothing here yet */\n"
            "})\n"), set())

    def test_argumentless_skip_does_not_count(self):
        self.assertEqual(self._refs(
            "// @e2e my-spec::foo-does-bar\n"
            "test('off', async ({ page }) => {\n"
            "  test.skip()\n"
            "  await expect(page).toHaveTitle(/x/)\n"
            "})\n"), set())

    # --- live: must STILL count -----------------------------------------
    def test_a_real_test_counts(self):
        self.assertIn("my-spec::foo-does-bar", self._refs(
            "// @e2e my-spec::foo-does-bar\n"
            "test('minutes are published', async ({ page }) => {\n"
            "  await expect(page.getByRole('heading')).toBeVisible()\n"
            "})\n"))

    def test_a_runtime_conditional_skip_still_counts(self):
        # THE anti-blindness pair. This test RUNS on every browser but one.
        # Refusing it would swap the gate's old blindness for a new one.
        self.assertIn("my-spec::foo-does-bar", self._refs(
            "// @e2e my-spec::foo-does-bar\n"
            "test('minutes are published', async ({ page, browserName }) => {\n"
            "  test.skip(browserName === 'firefox', 'flaky on gecko')\n"
            "  await expect(page.getByRole('heading')).toBeVisible()\n"
            "})\n"))

    def test_an_env_conditional_skip_still_counts(self):
        self.assertIn("my-spec::foo-does-bar", self._refs(
            "// @e2e my-spec::foo-does-bar\n"
            "test('needs a fixture', async ({ page }) => {\n"
            "  test.skip(!process.env.CI, 'needs a CI fixture')\n"
            "  await page.goto('/')\n"
            "})\n"))

    def test_one_live_reference_rescues_a_skipped_sibling(self):
        # A scenario proven by a real test is covered even if some other
        # skipped test also names it. The gate reports UNCOVERED, not
        # "you have a skipped test".
        self.assertIn("my-spec::foo-does-bar", self._refs(
            "// @e2e my-spec::foo-does-bar\n"
            "test.skip('old version', async () => { await go() })\n"
            "// @e2e my-spec::foo-does-bar\n"
            "test('new version', async ({ page }) => {\n"
            "  await expect(page).toHaveTitle(/x/)\n"
            "})\n"))

    def test_a_file_level_tag_with_no_enclosing_test_still_counts(self):
        # This gate is fixing tests that were switched OFF. It must not
        # invent a structural requirement it never had.
        self.assertIn("my-spec::foo-does-bar", self._refs(
            "// @e2e my-spec::foo-does-bar\n"
            "import { test, expect } from '@playwright/test'\n"))

    def test_dead_refs_are_reported_with_a_reason(self):
        _write(self.root, "tests/e2e/foo.spec.ts",
               "// @e2e my-spec::foo-does-bar\n"
               "test('x', async () => { test.skip(true, 'later') })\n")
        live, dead = cec.collect_ref_status(self.root)
        self.assertEqual(live, set())
        self.assertIn("my-spec::foo-does-bar", dead)
        self.assertIn("never runs", dead["my-spec::foo-does-bar"])

    # --- a member call named `test` is not a test -----------------------
    def test_a_regexp_test_call_is_not_mistaken_for_the_enclosing_test(self):
        # openconnector dead-letter-replay.spec.ts, verbatim in shape: a
        # console-filter helper sits between the file-level @e2e tags and the
        # real tests, and it calls RegExp.prototype.test. The forward search
        # landed on `rx.test(text)`, found no body, and reported all 11 refs
        # as "referenced only by a test that never runs" — about a file whose
        # tests run fine.
        self.assertIn("my-spec::foo-does-bar", self._refs(
            "// @e2e my-spec::foo-does-bar\n"
            "const IGNORED = [/Deprecation/i]\n"
            "function spy(page) {\n"
            "  page.on('console', (msg) => {\n"
            "    if (IGNORED.some((rx) => rx.test(msg.text()))) return\n"
            "  })\n"
            "}\n"
            "test('the view mounts', async ({ page }) => {\n"
            "  await expect(page).toHaveTitle(/x/)\n"
            "})\n"))

    def test_an_identifier_merely_ending_in_test_is_not_a_test(self):
        # `latest(` / `submit(` end in `it`/`test` and must not open a block.
        self.assertIn("my-spec::foo-does-bar", self._refs(
            "// @e2e my-spec::foo-does-bar\n"
            "const v = latest(versions)\n"
            "test('the view mounts', async ({ page }) => {\n"
            "  await expect(page).toHaveTitle(/x/)\n"
            "})\n"))

    def test_a_member_call_does_not_rescue_a_genuinely_skipped_test(self):
        # THE CONTROL. Ignoring `rx.test(...)` must not make the gate skip
        # forward past a real skipped test and find a live one instead — the
        # skipped test still owns this tag, and it must still be dead.
        _write(self.root, "tests/e2e/foo.spec.ts",
               "// @e2e my-spec::foo-does-bar\n"
               "const ok = /x/.test('x')\n"
               "test('x', async () => { test.skip(true, 'later') })\n"
               "test('unrelated', async ({ page }) => {\n"
               "  await expect(page).toHaveTitle(/x/)\n"
               "})\n")
        live, dead = cec.collect_ref_status(self.root)
        self.assertEqual(live, set())
        self.assertIn("my-spec::foo-does-bar", dead)


# ---------------------------------------------------------------------------
# A SWITCHED-OFF ANCESTOR TAKES THE TAG WITH IT  (#210)
#
# `_enclosing_block` searched FORWARD only. A tag written where the convention
# says to write it — immediately above the `test()` it annotates — resolved to
# that inner, un-skipped test, and the `test.describe.skip` wrapping both was
# never consulted. The ref counted as coverage while nothing ran.
#
# A second, wider defect was found while writing these: `_TEST_DECL_RE` could
# not match `test.describe.skip(` AT ALL. At `test` the modifier group finds
# `.describe` instead of `.skip` so the required `(` fails; at `describe` the
# `(?<![.\w$])` lookbehind sees the preceding dot and refuses. So the
# "correctly dead" case in #210's own reproduction — the tag ABOVE the skipped
# describe — was in fact reported LIVE too. Both are covered below.
#
# EVERY dead assertion here is paired with a live one. `describe.only`,
# `describe.serial`, a live `describe`, and a sibling that merely follows a
# closed skipped block must all keep counting: refusing them would trade this
# gate's blindness for the opposite blindness, which is the same defect with
# the sign flipped.
# ---------------------------------------------------------------------------
class SkippedAncestorTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _refs(self, body: str) -> set:
        _write(self.root, "tests/e2e/foo.spec.ts", body)
        return cec.collect_covered_refs(self.root)

    # --- dead: an ancestor that never runs ------------------------------
    def test_tag_INSIDE_a_skipped_describe_does_not_count(self):
        # THE #210 DEFECT, verbatim. The tag sits where the docstring says to
        # put it and the forward search lands on the live inner `test()`.
        self.assertEqual(self._refs(
            "test.describe.skip('outer B', () => {\n"
            "  // @e2e demo::inside\n"
            "  test('inner b', async ({ page }) => {\n"
            "    await expect(page).toBeTruthy()\n"
            "  })\n"
            "})\n"), set())

    def test_tag_ABOVE_a_skipped_describe_does_not_count(self):
        # #210 believed this case already worked. It did not: the namespaced
        # `test.describe.skip(` was invisible to the declaration regex, so the
        # forward search stepped straight over it onto the inner test.
        self.assertEqual(self._refs(
            "// @e2e demo::above\n"
            "test.describe.skip('outer A', () => {\n"
            "  test('inner a', async ({ page }) => {\n"
            "    await expect(page).toBeTruthy()\n"
            "  })\n"
            "})\n"), set())

    def test_bare_describe_skip_ancestor_does_not_count(self):
        self.assertEqual(self._refs(
            "describe.skip('outer', () => {\n"
            "  // @e2e demo::inside\n"
            "  it('inner', async () => { await go() })\n"
            "})\n"), set())

    def test_xdescribe_ancestor_does_not_count(self):
        self.assertEqual(self._refs(
            "xdescribe('outer', () => {\n"
            "  // @e2e demo::inside\n"
            "  it('inner', async () => { await go() })\n"
            "})\n"), set())

    def test_describe_fixme_ancestor_does_not_count(self):
        self.assertEqual(self._refs(
            "test.describe.fixme('outer', () => {\n"
            "  // @e2e demo::inside\n"
            "  test('inner', async ({ page }) => { await expect(page).toBeTruthy() })\n"
            "})\n"), set())

    def test_a_live_describe_nested_in_a_skipped_one_does_not_count(self):
        # The INNERMOST enclosing block runs, and it still never executes.
        self.assertEqual(self._refs(
            "test.describe.skip('outer', () => {\n"
            "  test.describe('inner group', () => {\n"
            "    // @e2e demo::deep\n"
            "    test('t', async ({ page }) => { await expect(page).toBeTruthy() })\n"
            "  })\n"
            "})\n"), set())

    def test_the_scholiq_shape_repeated_tags_inside_the_block(self):
        # scholiq peer-and-self-assessment.spec.ts: the header tags above the
        # `describe.skip` were dead, and the SAME refs repeated inside the
        # block resurrected them. Both copies must now be dead.
        self.assertEqual(self._refs(
            "// @e2e demo::a\n"
            "// @e2e demo::b\n"
            "test.describe.skip('needs an isolated instance', () => {\n"
            "  // @e2e demo::a\n"
            "  test('one', async ({ page }) => { await expect(page).toBeTruthy() })\n"
            "  // @e2e demo::b\n"
            "  test('two', async ({ page }) => { await expect(page).toBeTruthy() })\n"
            "})\n"), set())

    # --- live: must STILL count -----------------------------------------
    def test_tag_inside_a_LIVE_describe_still_counts(self):
        # THE CONTROL for every assertion above. If this ever fails, the
        # ancestor walk has stopped discriminating and is simply killing
        # everything nested.
        self.assertIn("demo::inside", self._refs(
            "test.describe('outer', () => {\n"
            "  // @e2e demo::inside\n"
            "  test('inner', async ({ page }) => {\n"
            "    await expect(page).toBeTruthy()\n"
            "  })\n"
            "})\n"))

    def test_describe_only_is_not_switched_off(self):
        # `.only` RUNS — it suppresses everything else, which is the opposite
        # of being skipped.
        self.assertIn("demo::inside", self._refs(
            "test.describe.only('outer', () => {\n"
            "  // @e2e demo::inside\n"
            "  test('inner', async ({ page }) => { await expect(page).toBeTruthy() })\n"
            "})\n"))

    def test_describe_serial_is_not_switched_off(self):
        self.assertIn("demo::inside", self._refs(
            "test.describe.serial('outer', () => {\n"
            "  // @e2e demo::inside\n"
            "  test('inner', async ({ page }) => { await expect(page).toBeTruthy() })\n"
            "})\n"))

    def test_describe_configure_is_not_a_declaration(self):
        # `test.describe.configure({...})` is a settings call, not a block. It
        # must neither open a block nor be mistaken for one by the forward
        # search that follows a file-level tag.
        self.assertIn("demo::top", self._refs(
            "// @e2e demo::top\n"
            "test.describe.configure({ mode: 'parallel' })\n"
            "test('real', async ({ page }) => { await expect(page).toBeTruthy() })\n"))

    def test_a_sibling_AFTER_a_closed_skipped_describe_still_counts(self):
        # The span check must be "encloses", not "appears earlier". A skipped
        # block that has already closed is a sibling and must not poison what
        # follows it.
        self.assertIn("demo::after", self._refs(
            "test.describe.skip('dead group', () => {\n"
            "  test('x', async ({ page }) => { await expect(page).toBeTruthy() })\n"
            "})\n"
            "// @e2e demo::after\n"
            "test('live one', async ({ page }) => {\n"
            "  await expect(page).toBeTruthy()\n"
            "})\n"))

    def test_a_runtime_conditional_skip_inside_a_live_describe_still_counts(self):
        # The gate's original anti-blindness pair, now with an ancestor in the
        # picture: this runs on every browser but one.
        self.assertIn("demo::inside", self._refs(
            "test.describe('outer', () => {\n"
            "  // @e2e demo::inside\n"
            "  test('inner', async ({ page, browserName }) => {\n"
            "    test.skip(browserName === 'firefox', 'flaky on gecko')\n"
            "    await expect(page).toBeTruthy()\n"
            "  })\n"
            "})\n"))

    def test_a_live_sibling_rescues_a_ref_dead_inside_a_skipped_describe(self):
        # Same rule the module already applies to skipped tests: one running
        # reference is coverage. The gate reports UNCOVERED, not "you have a
        # skipped describe".
        self.assertIn("demo::both", self._refs(
            "test.describe.skip('dead group', () => {\n"
            "  // @e2e demo::both\n"
            "  test('x', async ({ page }) => { await expect(page).toBeTruthy() })\n"
            "})\n"
            "// @e2e demo::both\n"
            "test('live one', async ({ page }) => {\n"
            "  await expect(page).toBeTruthy()\n"
            "})\n"))

    # --- the regex must still reject what it always rejected -------------
    def test_a_member_call_named_test_is_still_not_a_declaration(self):
        # The namespace segment added for `test.describe` must not have
        # widened into "any member call". `rx.test(` is RegExp.prototype.test.
        self.assertIn("demo::live", self._refs(
            "// @e2e demo::live\n"
            "const IGNORED = [/Deprecation/i]\n"
            "function spy(page) {\n"
            "  page.on('console', (msg) => {\n"
            "    if (IGNORED.some((rx) => rx.test(msg.text()))) return\n"
            "  })\n"
            "}\n"
            "test('the view mounts', async ({ page }) => {\n"
            "  await expect(page).toBeTruthy()\n"
            "})\n"))

    # --- ownership of an unconditional skip -----------------------------
    def test_a_nested_tests_own_skip_does_not_kill_the_whole_group(self):
        # launchpad spec-coverage.spec.ts, in shape: a file-level tag now
        # resolves to the enclosing `test.describe`, and ONE nested test in
        # that group guards itself with `test.skip(true, …)`. The other tests
        # run. Condemning the group is the gate's blindness with the sign
        # flipped.
        self.assertIn("demo::header", self._refs(
            "// @e2e demo::header\n"
            "test.describe('sidebar', () => {\n"
            "  test('a', async ({ page }) => {\n"
            "    await expect(page).toBeTruthy()\n"
            "  })\n"
            "  test('b', async ({ page }) => {\n"
            "    test.skip(true, 'not available in this environment')\n"
            "    await expect(page).toBeTruthy()\n"
            "  })\n"
            "})\n"))

    def test_a_group_level_unconditional_skip_still_kills_the_group(self):
        # THE CONTROL. Playwright's `test.skip()` called directly in a describe
        # body skips every test in the group, and that must still be dead.
        self.assertEqual(self._refs(
            "// @e2e demo::header\n"
            "test.describe('sidebar', () => {\n"
            "  test.skip()\n"
            "  test('a', async ({ page }) => {\n"
            "    await expect(page).toBeTruthy()\n"
            "  })\n"
            "})\n"), set())

    def test_a_tests_own_unconditional_skip_still_kills_that_test(self):
        # The decidesk shape must not be rescued by the ownership rule.
        self.assertEqual(self._refs(
            "test.describe('group', () => {\n"
            "  // @e2e demo::inner\n"
            "  test('minutes are published', async ({ page }) => {\n"
            "    test.skip(true, 'pending backend work')\n"
            "  })\n"
            "})\n"), set())

    def test_the_four_case_fixture_from_the_issue(self):
        # #210's minimal reproduction, whole, in one file — the shape the fix
        # is measured against.
        _write(self.root, "tests/e2e/a.spec.ts",
               "import { test, expect } from '@playwright/test'\n"
               "\n"
               "// @e2e demo::tag-above-a-skipped-describe\n"
               "test.describe.skip('outer A', () => {\n"
               "  test('inner a', async ({ page }) => { await expect(page).toBeTruthy() })\n"
               "})\n"
               "\n"
               "test.describe.skip('outer B', () => {\n"
               "  // @e2e demo::tag-inside-a-skipped-describe\n"
               "  test('inner b', async ({ page }) => { await expect(page).toBeTruthy() })\n"
               "})\n"
               "\n"
               "// @e2e demo::plain-skipped-test\n"
               "test.skip('plain skipped', async ({ page }) => { await expect(page).toBeTruthy() })\n"
               "\n"
               "// @e2e demo::genuinely-live\n"
               "test('live one', async ({ page }) => { await expect(page).toBeTruthy() })\n")
        live, dead = cec.collect_ref_status(self.root)
        self.assertEqual(live, {"demo::genuinely-live"})
        self.assertEqual(set(dead), {
            "demo::plain-skipped-test",
            "demo::tag-above-a-skipped-describe",
            "demo::tag-inside-a-skipped-describe",
        })


# ---------------------------------------------------------------------------
# The declaration regex, directly. These are the unit-level counterparts of the
# behaviour above: `test.describe.skip(` matching AT ALL is the precondition
# for every dead assertion in the class above, and `rx.test(` NOT matching is
# the precondition for the live ones.
# ---------------------------------------------------------------------------
class DeclarationRegexTest(unittest.TestCase):
    def _mod(self, src: str):
        m = cec._TEST_DECL_RE.match(src)
        return None if m is None else (m.group("fn"), m.group("mod"))

    def test_namespaced_describe_skip_matches(self):
        self.assertEqual(self._mod("test.describe.skip('a', () => {})")[0], "describe")
        self.assertIsNotNone(self._mod("test.describe.skip('a', () => {})")[1])

    def test_namespaced_describe_matches_and_is_live(self):
        self.assertEqual(self._mod("test.describe('a', () => {})"), ("describe", None))

    def test_bare_forms_still_match(self):
        self.assertEqual(self._mod("test('a', () => {})"), ("test", None))
        self.assertEqual(self._mod("describe('a', () => {})"), ("describe", None))
        self.assertIsNotNone(self._mod("test.skip('a', () => {})")[1])

    def test_serial_and_only_are_not_modifiers(self):
        self.assertEqual(self._mod("test.describe.serial('a', () => {})"), ("describe", None))
        self.assertEqual(self._mod("test.describe.only('a', () => {})"), ("describe", None))

    def test_member_calls_are_still_rejected(self):
        for src in ("rx.test(msg)", "foo.it(1)", "latest(versions)", "submit(form)"):
            self.assertIsNone(cec._TEST_DECL_RE.match(src), src)

    def test_hooks_and_config_calls_are_not_declarations(self):
        for src in ("test.beforeEach(async () => {})",
                    "test.use({ locale: 'nl' })",
                    "test.step('x', async () => {})",
                    "test.describe.configure({ mode: 'parallel' })"):
            self.assertIsNone(cec._TEST_DECL_RE.match(src), src)


if __name__ == "__main__":
    unittest.main()
