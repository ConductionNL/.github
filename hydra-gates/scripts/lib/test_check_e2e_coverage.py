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


if __name__ == "__main__":
    unittest.main()
