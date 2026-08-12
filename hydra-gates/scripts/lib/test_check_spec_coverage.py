#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_spec_coverage. Run with:

    python3 scripts/lib/test_check_spec_coverage.py
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_spec_coverage as csc  # noqa: E402


def _all_lines(text: str) -> set[int]:
    """Mark every line of a file as added (full-file diff scope)."""
    return set(range(1, text.count("\n") + 2))


class BackendTest(unittest.TestCase):
    def test_covered_method_passes(self):
        text = """<?php
class FooService {
    /**
     * Do a thing.
     *
     * @spec openspec/changes/x/tasks.md#task-1
     */
    public function doThing(string $id): string
    {
        return $id;
    }
}
"""
        findings: list[str] = []
        csc.check_php_file("lib/Service/FooService.php", text, _all_lines(text), findings)
        self.assertEqual(findings, [])

    def test_uncovered_method_flagged(self):
        text = """<?php
class FooService {
    /**
     * Do a thing — no spec tag here.
     */
    public function doThing(string $id): string
    {
        return $id;
    }
}
"""
        findings: list[str] = []
        csc.check_php_file("lib/Service/FooService.php", text, _all_lines(text), findings)
        self.assertEqual(len(findings), 1)
        self.assertIn("FooService.php::doThing", findings[0])
        self.assertIn("missing @spec", findings[0])

    def test_spec_exclude_with_reason_passes(self):
        text = """<?php
class FooService {
    /**
     * Debug-only dump endpoint.
     *
     * @spec exclude debug-only endpoint, never shipped to users
     */
    public function debugDump(): string
    {
        return var_export($this, true);
    }
}
"""
        findings: list[str] = []
        csc.check_php_file("lib/Service/FooService.php", text, _all_lines(text), findings)
        self.assertEqual(findings, [], "a reason-bearing @spec exclude is compliant")

    def test_spec_exclude_through_intervening_comment(self):
        # A `/* istanbul ignore next */` (and a trailing-`//` variant) between the
        # docblock and the declaration must not hide the @spec exclude tag.
        text = """<?php
class FooService {
    /**
     * @spec exclude thin passthrough
     */
    /* istanbul ignore next */
    public function refreshA(): void {}

    /**
     * @spec exclude thin passthrough
     */
    /* istanbul ignore next */ // ignore in Jest until extracted
    public function refreshB(): void {}
}
"""
        findings: list[str] = []
        csc.check_php_file("lib/Service/FooService.php", text, _all_lines(text), findings)
        self.assertEqual(findings, [], "intervening single-line comments must not hide @spec")

    def test_spec_exclude_bare_flagged(self):
        text = """<?php
class FooService {
    /**
     * @spec exclude
     */
    public function sneaky(string $id): string
    {
        return $id;
    }
}
"""
        findings: list[str] = []
        csc.check_php_file("lib/Service/FooService.php", text, _all_lines(text), findings)
        self.assertEqual(len(findings), 1, "a bare @spec exclude (no reason) is NOT compliant")
        self.assertIn("::sneaky", findings[0])

    def test_docblock_status_classification(self):
        covered = ["    /**", "     * @spec openspec/changes/x/tasks.md#task-1", "     */", "    public function a() {"]
        self.assertEqual(csc._docblock_spec_status(covered, 3), ("covered", None))
        excluded = ["    /**", "     * @spec exclude vendor shim", "     */", "    public function b() {"]
        self.assertEqual(csc._docblock_spec_status(excluded, 3), ("excluded", "vendor shim"))
        bare = ["    /**", "     * @spec exclude", "     */", "    public function c() {"]
        self.assertEqual(csc._docblock_spec_status(bare, 3), ("exclude_noreason", None))
        none = ["    /**", "     * Just a description.", "     */", "    public function d() {"]
        self.assertEqual(csc._docblock_spec_status(none, 3), ("none", None))

    def test_protected_method_in_scope(self):
        text = """<?php
class FooService {
    protected function helper(): void
    {
        $x = 1;
        $y = 2;
        echo $x + $y;
    }
}
"""
        findings: list[str] = []
        csc.check_php_file("lib/Service/FooService.php", text, _all_lines(text), findings)
        self.assertEqual(len(findings), 1)
        self.assertIn("::helper", findings[0])

    def test_constructor_exempt(self):
        text = """<?php
class FooService {
    public function __construct(private readonly Bar $bar)
    {
    }
}
"""
        findings: list[str] = []
        csc.check_php_file("lib/Service/FooService.php", text, _all_lines(text), findings)
        self.assertEqual(findings, [])

    def test_simple_accessor_exempt(self):
        text = """<?php
class FooService {
    public function getName(): string
    {
        return $this->name;
    }
}
"""
        findings: list[str] = []
        csc.check_php_file("lib/Service/FooService.php", text, _all_lines(text), findings)
        self.assertEqual(findings, [])

    def test_accessor_with_logic_is_in_scope(self):
        # A get*-named method with a real (>2 line) body is NOT a trivial
        # accessor — it must carry @spec.
        text = """<?php
class FooService {
    public function getComputed(): int
    {
        $a = $this->a;
        $b = $this->b;
        $c = $this->c;
        return $a + $b + $c;
    }
}
"""
        findings: list[str] = []
        csc.check_php_file("lib/Service/FooService.php", text, _all_lines(text), findings)
        self.assertEqual(len(findings), 1)
        self.assertIn("::getComputed", findings[0])


class FrontendTest(unittest.TestCase):
    def test_vue_method_uncovered_flagged(self):
        text = """<script>
export default {
    methods: {
        async fetchThings (id) {
            const r = await api.get(id)
            this.things = r.data
            return r
        },
    },
}
</script>
"""
        findings: list[str] = []
        csc.check_frontend_file("src/views/Things.vue", text, _all_lines(text), findings)
        self.assertTrue(any("::fetchThings" in f for f in findings), findings)

    def test_vue_method_covered_passes(self):
        text = """<script>
export default {
    methods: {
        /**
         * Fetch things.
         * @spec openspec/changes/x/tasks.md#task-2
         */
        async fetchThings (id) {
            const r = await api.get(id)
            this.things = r.data
            return r
        },
    },
}
</script>
"""
        findings: list[str] = []
        csc.check_frontend_file("src/views/Things.vue", text, _all_lines(text), findings)
        self.assertEqual([f for f in findings if "fetchThings" in f], [])

    def test_lifecycle_hook_trivial_exempt(self):
        text = """<script>
export default {
    mounted () {
        this.load()
    },
}
</script>
"""
        findings: list[str] = []
        csc.check_frontend_file("src/views/Things.vue", text, _all_lines(text), findings)
        self.assertEqual(findings, [])

    def test_exported_service_fn_flagged(self):
        text = """export function buildPayload (input) {
    const out = { ...input }
    out.normalized = true
    return out
}
"""
        findings: list[str] = []
        csc.check_frontend_file("src/services/payload.js", text, _all_lines(text), findings)
        self.assertTrue(any("::buildPayload" in f for f in findings), findings)


class NormalisationTest(unittest.TestCase):
    """`.github#395` — layout is not a change, and a change is not layout.

    Each pair below is one normalisation rule and ITS POSITIVE CONTROL: the
    A-arm proves the reformat stops being a change, the B-arm proves a real
    change still travels THROUGH that same rule. A rule with only an A-arm is
    indistinguishable from a rule that switched the gate off.
    """

    def _changed(self, base: str, head: str, is_php: bool = True) -> set[int]:
        return csc._substantively_changed_lines(base, head, is_php)

    # --- braces ------------------------------------------------------------
    def test_brace_move_alone_is_not_a_change(self):
        base = "public function foo(): int\n{\n    return 1;\n}\n"
        head = "public function foo(): int {\n\treturn 1;\n}\n"
        self.assertEqual(self._changed(base, head), set(),
                         "K&R vs Allman is where the brace SITS, not what the code does")

    def test_a_body_change_through_the_brace_move_is_still_reported(self):
        base = "public function foo(): int\n{\n    return 1;\n}\n"
        head = "public function foo(): int {\n\treturn 2;\n}\n"
        self.assertEqual(self._changed(base, head), {2},
                         "the reformatted line whose VALUE changed must survive normalisation")

    # --- whitespace --------------------------------------------------------
    def test_indent_and_operator_spacing_alone_is_not_a_change(self):
        base = "    $a = (array) $x;\n    $b = 'p'.$q;\n"
        head = "\t$a = (array)$x;\n\t$b = 'p' . $q;\n"
        self.assertEqual(self._changed(base, head), set(),
                         "php-cs-fixer both adds and removes spacing; neither is a change")

    def test_whitespace_inside_a_string_is_still_a_change(self):
        # The reason literals are lifted out before whitespace is touched: this
        # is text a user reads.
        base = "    $msg = 'not installed. ';\n"
        head = "\t$msg = 'not installed.';\n"
        self.assertEqual(self._changed(base, head), {1})

    # --- trailing comma ----------------------------------------------------
    def test_trailing_comma_alone_is_not_a_change(self):
        base = "public function f(\n    string $a,\n    int $b\n) {\n"
        head = "public function f(\n\tstring $a,\n\tint $b,\n) {\n"
        self.assertEqual(self._changed(base, head), set())

    def test_a_new_parameter_through_the_trailing_comma_is_still_reported(self):
        base = "public function f(\n    string $a,\n    int $b\n) {\n"
        head = "public function f(\n\tstring $a,\n\tint $b,\n\tbool $c,\n) {\n"
        self.assertIn(4, self._changed(base, head),
                      "an ADDED parameter is not a trailing comma")

    def test_trailing_comma_is_not_normalised_in_javascript(self):
        # `[1, 2,]` and `[1, 2,,]` differ in JS (elision), so the rule is PHP-only.
        base = "const a = [1, 2]\n"
        head = "const a = [1, 2,]\n"
        self.assertEqual(self._changed(base, head, is_php=False), {1})

    # --- quote style -------------------------------------------------------
    def test_quote_style_alone_is_not_a_change(self):
        base = '    $m = "PDF extraction failed: ";\n'
        head = "\t$m = 'PDF extraction failed: ';\n"
        self.assertEqual(self._changed(base, head), set())

    def test_quote_style_with_escaped_quotes_is_not_a_change(self):
        # MEASURED on shillinq#532: `"CAST(\"object\" AS TEXT)"` became
        # `'CAST("object" AS TEXT)'` — the same characters, differently spelled.
        base = '    $q = "CAST(\\"object\\" AS TEXT)";\n'
        head = "\t$q = 'CAST(\"object\" AS TEXT)';\n"
        self.assertEqual(self._changed(base, head), set())

    def test_string_content_change_through_the_quote_rule_is_still_reported(self):
        base = '    $m = "PDF extraction failed: ";\n'
        head = "\t$m = 'PDF extraction succeeded: ';\n"
        self.assertEqual(self._changed(base, head), {1},
                         "re-quoting must not carry a CONTENT edit through with it")

    def test_dropping_interpolation_is_a_change(self):
        # `"$name"` is the value of $name; `'$name'` is six literal characters.
        # A rule that equated these would hide a real bug behind a style fix.
        base = '    $m = "$name";\n'
        head = "\t$m = '$name';\n"
        self.assertEqual(self._changed(base, head), {1})

    def test_dropping_an_escape_sequence_is_a_change(self):
        # `"\n"` is a newline; `'\n'` is a backslash and an n.
        base = '    $m = "a\\nb";\n'
        head = "\t$m = 'a\\nb';\n"
        self.assertEqual(self._changed(base, head), {1})

    # --- statement re-wrap -------------------------------------------------
    def test_rewrapping_one_php_statement_is_not_a_change(self):
        base = "    $x = 'a: '.$b.' c: '.$d;\n"
        head = "\t$x = 'a: '.$b\n\t\t.' c: '.$d;\n"
        self.assertEqual(self._changed(base, head), set(),
                         "the same characters, redistributed across lines")

    def test_a_changed_operand_in_a_rewrapped_statement_is_still_reported(self):
        base = "    $x = 'a: '.$b.' c: '.$d;\n"
        head = "\t$x = 'a: '.$b\n\t\t.' c: '.$e;\n"
        self.assertTrue(self._changed(base, head),
                        "a re-wrap that also changes an operand is a change")

    def test_rewrap_is_not_applied_across_a_line_comment(self):
        # Inserting a break after `//` UNCOMMENTS what followed: the same
        # characters, a different program.
        base = "    // fixme $flag = true;\n"
        head = "    // fixme\n    $flag = true;\n"
        self.assertTrue(self._changed(base, head),
                        "uncommenting a statement is not a re-wrap")

    def test_rewrap_is_not_applied_to_javascript(self):
        # ASI: `return` on its own line returns undefined.
        base = "    return buildThing(a)\n"
        head = "    return\n    buildThing(a)\n"
        self.assertTrue(self._changed(base, head, is_php=False),
                        "JavaScript has automatic semicolon insertion; PHP does not")

    # --- what is NOT normalised -------------------------------------------
    def test_a_respelled_type_is_still_a_change(self):
        # `string|null` -> `?string` is another rule in the same php-cs-fixer
        # run and it IS equivalent — but it is deliberately NOT normalised: the
        # line is a method SIGNATURE, the set of rules a normaliser can carry is
        # open-ended, and every one of them costs a little more of the gate's
        # eyesight. MEASURED on openregister#2445, where exactly two methods
        # change this way; both are already `@spec`-tagged, so the gate sees
        # them, has an answer for them, and reports nothing.
        base = "    public function f(): string|null\n    {\n"
        head = "\tpublic function f(): ?string {\n"
        self.assertEqual(self._changed(base, head), {1})

    # --- the narrowing can only ever narrow --------------------------------
    def test_an_added_method_is_entirely_in_scope(self):
        base = "class A {\n}\n"
        head = "class A {\n\tpublic function b(): int {\n\t\treturn 1;\n\t}\n}\n"
        changed = self._changed(base, head)
        # Declaration and body. (Which of the two identical `}` lines the
        # matcher calls "the new one" is ambiguous and irrelevant — a closing
        # brace is never what puts a method in scope.)
        self.assertTrue({2, 3} <= changed, changed)
        self.assertEqual(len(changed), 3, changed)


class DiffScopeFullRunTest(unittest.TestCase):
    """End-to-end: a real git repo where only one method is in the diff."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self._run("git", "init", "-q")
        self._run("git", "config", "user.email", "t@t.nl")
        self._run("git", "config", "user.name", "t")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _run(self, *args: str) -> None:
        subprocess.run(args, cwd=str(self.dir), check=True,
                       capture_output=True, text=True)

    def _write(self, rel: str, content: str) -> None:
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def test_only_changed_method_flagged(self):
        # Baseline commit: one already-untagged legacy method.
        self._write("lib/Service/FooService.php", """<?php
class FooService {
    public function legacyUntagged(): int
    {
        $a = 1;
        $b = 2;
        return $a + $b;
    }
}
""")
        self._run("git", "add", "-A")
        self._run("git", "commit", "-q", "-m", "base")
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(self.dir),
                              capture_output=True, text=True).stdout.strip()

        # New commit adds a NEW untagged method but leaves legacy untouched.
        self._write("lib/Service/FooService.php", """<?php
class FooService {
    public function legacyUntagged(): int
    {
        $a = 1;
        $b = 2;
        return $a + $b;
    }

    public function brandNewMethod(): int
    {
        $x = 10;
        $y = 20;
        return $x + $y;
    }
}
""")
        self._run("git", "add", "-A")
        self._run("git", "commit", "-q", "-m", "feat")

        os.environ["HYDRA_GATE_BASE_REF"] = base
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = csc.main(["check_spec_coverage.py", str(self.dir)])
        finally:
            del os.environ["HYDRA_GATE_BASE_REF"]

        out = buf.getvalue()
        # The legacy method (untouched) must NOT be flagged; only the new one.
        self.assertIn("brandNewMethod", out)
        self.assertNotIn("legacyUntagged", out)
        self.assertEqual(rc, 1)

    def _spec_removal_fixture(self):
        """A tagged method plus an untagged legacy one, committed as the base.
        Returns the base sha."""
        self._write("lib/Service/BarService.php", """<?php
class BarService {
    /**
     * Does the thing.
     *
     * @spec openspec/specs/things/spec.md
     */
    public function doThing(string $id): array
    {
        return [$id];
    }

    /**
     * Legacy, never tagged.
     */
    public function legacyThing(string $id): array
    {
        return [$id, 'legacy'];
    }
}
""")
        self._run("git", "add", "-A")
        self._run("git", "commit", "-q", "-m", "base")
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(self.dir),
                              capture_output=True, text=True).stdout.strip()

    def _gate(self, base):
        os.environ["HYDRA_GATE_BASE_REF"] = base
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = csc.main(["check_spec_coverage.py", str(self.dir)])
        finally:
            del os.environ["HYDRA_GATE_BASE_REF"]
        return buf.getvalue(), rc

    def test_deleting_an_at_spec_tag_is_caught(self):
        # .github#271 — `_overlaps` walks FORWARD from the declaration, so the
        # docblock is outside the scope window, and the docblock is the only
        # place @spec can live. Deleting the tag left the body byte-identical:
        # the helper printed `# count=0` and exited 0. Every @spec tag in a repo
        # could be stripped and this gate stayed green — the one edit that
        # removes coverage was the one it could not see.
        #
        # Worse, run_gate skipped any file whose `added` set was empty, and a
        # pure deletion produces exactly that, so the file was never opened.
        base = self._spec_removal_fixture()
        text = (self.dir / "lib/Service/BarService.php").read_text()
        old = "     *\n     * @spec openspec/specs/things/spec.md\n"
        self.assertIn(old, text, "fixture premise: the @spec line must be there to delete")
        self._write("lib/Service/BarService.php", text.replace(old, ""))
        self._run("git", "add", "-A")
        self._run("git", "commit", "-q", "-m", "strip the tag")

        out, rc = self._gate(base)
        self.assertIn("doThing", out, "the method that LOST its @spec must be named")
        self.assertEqual(rc, 1)
        # ...and ONLY that method. Naming every untagged method in the file
        # would surface inherited debt the author never touched, which is what
        # ADR-020 exists to keep out of a PR.
        self.assertNotIn("legacyThing", out)

    # ---- .github#395, end to end through changed_lines -------------------
    _ALLMAN = """<?php
class ReportService {
    /**
     * Untagged legacy — inherited debt, and it stays that way.
     */
    public function buildLabel(
        string $id,
        string $kind
    ): string {
        $prefix = "row";

        return $prefix . ':' . $kind . ':' . $id;
    }

    /**
     * Also untagged.
     */
    public function totalWeights(array $rows): int
    {
        $total = 0;
        foreach ($rows as $row) {
            $total = $total + (int) ($row['weight'] ?? 0);
        }

        return $total;
    }
}
"""
    # Every difference below is one `nextcloud/coding-standard` rule.
    _KNR = """<?php
class ReportService {
\t/**
\t * Untagged legacy — inherited debt, and it stays that way.
\t */
\tpublic function buildLabel(
\t\tstring $id,
\t\tstring $kind,
\t): string {
\t\t$prefix = 'row';

\t\treturn $prefix . ':' . $kind
\t\t\t. ':' . $id;
\t}

\t/**
\t * Also untagged.
\t */
\tpublic function totalWeights(array $rows): int {
\t\t$total = 0;
\t\tforeach ($rows as $row) {
\t\t\t$total = $total %s (int)($row['weight'] ?? 0);
\t\t}

\t\treturn $total;
\t}
}
"""

    def _reformat_fixture(self, operator: str) -> str:
        self._write("lib/Service/ReportService.php", self._ALLMAN)
        self._run("git", "add", "-A")
        self._run("git", "commit", "-q", "-m", "base: before the reformat")
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(self.dir),
                              capture_output=True, text=True).stdout.strip()
        self._write("lib/Service/ReportService.php", self._KNR % operator)
        self._run("git", "add", "-A")
        self._run("git", "commit", "-q", "-m", "style: adopt nextcloud/coding-standard")
        return base

    def test_a_coding_standard_reformat_is_not_a_set_of_changed_methods(self):
        # `.github#395`. The changed-method set came from a plain `git diff -U0`,
        # so K&R braces made EVERY method in a migrated app "modified" and
        # gate-16 demanded an @spec tag on all of them. Measured on procest#819:
        # 1 finding on the base branch, 185 on the formatting-only PR.
        base = self._reformat_fixture("+")

        # NOT VACUOUS: git still sees a large diff here. If the two fixture
        # strings were accidentally equal, the assertion below would pass on an
        # empty change set and prove nothing.
        churn = subprocess.run(
            ["git", "diff", "--numstat", f"{base}...HEAD"],
            cwd=str(self.dir), capture_output=True, text=True).stdout.split()
        self.assertGreaterEqual(int(churn[0]), 10, f"the reformat must BE a diff: {churn}")

        out, rc = self._gate(base)
        self.assertEqual(out, "# count=0\n", f"expected a clean run, got: {out}")
        self.assertEqual(rc, 0)

    def test_a_body_change_inside_a_reformatted_file_is_still_reported(self):
        # The anti-widening control, and the half that matters most: a gate that
        # stops reporting is worse than one that over-reports. Same reformat,
        # one operator flipped.
        base = self._reformat_fixture("-")
        out, rc = self._gate(base)
        self.assertIn("totalWeights", out, "the method whose body changed must be named")
        self.assertNotIn("buildLabel", out,
                         "the method beside it carries the same reformat and no change")
        self.assertEqual(rc, 1)

    def test_an_unrelated_docblock_edit_does_not_surface_legacy_debt(self):
        # The anti-widening control for the arm above. The fix must key on
        # "a tag was TAKEN AWAY", not on "a docblock was touched" — otherwise a
        # typo fix in a legacy untagged method's docblock becomes a finding.
        base = self._spec_removal_fixture()
        text = (self.dir / "lib/Service/BarService.php").read_text()
        old = "     * Legacy, never tagged.\n"
        self.assertIn(old, text)
        self._write("lib/Service/BarService.php",
                    text.replace(old, "     * Legacy, never tagged. Typo fixed.\n"))
        self._run("git", "add", "-A")
        self._run("git", "commit", "-q", "-m", "typo")

        out, rc = self._gate(base)
        self.assertEqual(out, "# count=0\n", f"expected a clean run, got: {out}")
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
