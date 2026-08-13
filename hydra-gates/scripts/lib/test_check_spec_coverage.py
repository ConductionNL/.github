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

    def test_trailing_comma_is_normalised_in_javascript_too(self):
        # `.github#435` REVERSED the PHP-only scope of this rule, and the
        # reversal is the whole reason the assertion changed rather than moved:
        # `[1, 2]` and `[1, 2,]` are both two-element arrays, in every engine
        # since ES5. The hazard #395 named is a HOLE, and the control for it is
        # the next test, not this one.
        base = "const a = [1, 2]\n"
        head = "const a = [1, 2,]\n"
        self.assertEqual(self._changed(base, head, is_php=False), set())

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

    def test_rewrap_across_an_asi_boundary_is_still_a_change_in_javascript(self):
        # ASI: `return` on its own line returns undefined. `.github#435` gave JS
        # the re-wrap rule but NOT across a restricted production, so this
        # assertion is unchanged from #395 — it is now the control for the
        # guard rather than for the absence of the rule.
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


class JsNormalisationTest(unittest.TestCase):
    """`.github#435` — the JS/TS/Vue half of #395's normalisation.

    Same contract as `NormalisationTest`: every rule ships with the change it
    must STILL see. A rule with only an A-arm is indistinguishable from having
    switched the frontend half of gate-16 off, which is the exact failure this
    gate exists to prevent — so the B-arms outnumber the A-arms here.

    MEASURED: pipelinq#820 (`feat/nextcloud-prettier`, 324 files) went from 468
    findings to 11 with no change to what `development` reports.
    """

    def _changed(self, base: str, head: str) -> set[int]:
        return csc._substantively_changed_lines(base, head, is_php=False)

    def _same(self, base: str, head: str) -> bool:
        return csc._js_canonical(base) == csc._js_canonical(head)

    # --- brace placement ---------------------------------------------------
    def test_a_mustache_split_over_lines_is_not_a_change(self):
        # The reason JS keeps its trailing `{`: stripping one leaves `{{` as `{`
        # and the halves stop matching their own single-line base.
        base = "      <span>{{ item.title }}</span>\n"
        head = "\t\t\t<span>{{\n\t\t\t\titem.title\n\t\t\t}}</span>\n"
        self.assertEqual(self._changed(base, head), set())

    def test_a_changed_expression_in_a_split_mustache_is_still_reported(self):
        base = "      <span>{{ item.title }}</span>\n"
        head = "\t\t\t<span>{{\n\t\t\t\titem.subtitle\n\t\t\t}}</span>\n"
        self.assertTrue(self._changed(base, head))

    def test_a_multiline_import_is_not_a_change(self):
        base = "import { CnAppRoot, CnObjectSidebar } from '@conduction/nextcloud-vue'\n"
        head = ("import {\n\tCnAppRoot,\n\tCnObjectSidebar,\n"
                "} from '@conduction/nextcloud-vue'\n")
        self.assertEqual(self._changed(base, head), set())

    def test_an_added_import_specifier_is_still_reported(self):
        base = "import { CnAppRoot, CnObjectSidebar } from '@conduction/nextcloud-vue'\n"
        head = ("import {\n\tCnAppRoot,\n\tCnObjectSidebar,\n\tbuiltinIntegrations,\n"
                "} from '@conduction/nextcloud-vue'\n")
        self.assertTrue(self._changed(base, head))

    # --- trailing comma / elision ------------------------------------------
    def test_an_elision_is_not_a_trailing_comma(self):
        # THE hazard #395 named. `[a, , b]` has three entries; `[a, b]` has two.
        base = "const a = [x, y]\n"
        head = "const a = [x, , y]\n"
        self.assertEqual(self._changed(base, head), {1})

    def test_an_elision_survives_a_rewrap(self):
        base = "const a = [x, , y]\n"
        head = "const a = [\n\tx,\n\t,\n\ty,\n]\n"
        self.assertTrue(self._changed(base, head),
                        "a hole must never be normalised away as punctuation")

    def test_a_broken_argument_list_with_a_trailing_comma_is_not_a_change(self):
        base = "\t\tawait axios.put(generateUrl('/apps/x/y'), delta)\n"
        head = "\t\tawait axios.put(\n\t\t\tgenerateUrl('/apps/x/y'),\n\t\t\tdelta,\n\t\t)\n"
        self.assertEqual(self._changed(base, head), set())

    def test_an_added_argument_through_the_trailing_comma_is_still_reported(self):
        base = "\t\tawait axios.put(generateUrl('/apps/x/y'), delta)\n"
        head = ("\t\tawait axios.put(\n\t\t\tgenerateUrl('/apps/x/y'),\n"
                "\t\t\tdelta,\n\t\t\t{ force: true },\n\t\t)\n")
        self.assertTrue(self._changed(base, head))

    # --- ASI ---------------------------------------------------------------
    def test_a_join_across_a_restricted_production_is_still_a_change(self):
        for word in ("return", "throw", "break", "continue", "yield"):
            with self.subTest(word=word):
                base = f"\t{word}\n\tvalue\n"
                head = f"\t{word} value\n"
                self.assertTrue(self._changed(base, head),
                                f"a line break after `{word}` ends the statement")

    def test_a_break_before_an_increment_is_still_a_change(self):
        base = "\tcount\n\t++other\n"
        head = "\tcount ++other\n"
        self.assertTrue(self._changed(base, head))

    # --- line comments -----------------------------------------------------
    def test_a_rewrap_that_uncomments_code_is_still_a_change(self):
        base = "\t// fixme flag = true\n"
        head = "\t// fixme\n\tflag = true\n"
        self.assertTrue(self._changed(base, head),
                        "inserting a break after `//` uncomments what followed")

    def test_a_rewrap_that_comments_out_code_is_still_a_change(self):
        base = "\tconst a = 1 // note\n\tconst b = 2\n"
        head = "\tconst a = 1 // note const b = 2\n"
        self.assertTrue(self._changed(base, head),
                        "joining onto a `//` line comments out what follows")

    # --- template literals -------------------------------------------------
    def test_a_line_local_template_literal_does_not_block_the_rewrap(self):
        base = "\t\tconst u = generateUrl(`/apps/x/${id}/${action}`)\n"
        head = "\t\tconst u = generateUrl(\n\t\t\t`/apps/x/${id}/${action}`,\n\t\t)\n"
        self.assertEqual(self._changed(base, head), set())

    def test_whitespace_inside_a_template_literal_is_still_a_change(self):
        base = "\t\tconst m = `not installed. `\n"
        head = "\t\tconst m = `not installed.`\n"
        self.assertEqual(self._changed(base, head), {1},
                         "a template literal's text is text a user reads")

    def test_a_changed_interpolation_is_still_reported(self):
        base = "\t\tconst u = generateUrl(`/apps/x/${id}`)\n"
        head = "\t\tconst u = generateUrl(\n\t\t\t`/apps/x/${otherId}`,\n\t\t)\n"
        self.assertTrue(self._changed(base, head))

    def test_a_break_inside_a_template_literal_is_still_a_change(self):
        # A newline inside a template literal is a CHARACTER of the string.
        base = "\t\tconst m = `alpha beta`\n"
        head = "\t\tconst m = `alpha\nbeta`\n"
        self.assertTrue(self._changed(base, head))

    # --- redundant parentheses ---------------------------------------------
    def test_a_return_wrapped_in_parentheses_is_not_a_change(self):
        base = "\t\t\treturn this.a !== this.b\n\t\t\t\t|| this.c !== this.d\n"
        head = "\t\t\treturn (\n\t\t\t\tthis.a !== this.b\n\t\t\t\t|| this.c !== this.d\n\t\t\t)\n"
        self.assertEqual(self._changed(base, head), set())

    def test_a_changed_operand_inside_a_parenthesised_return_is_still_reported(self):
        base = "\t\t\treturn this.a !== this.b\n\t\t\t\t|| this.c !== this.d\n"
        head = "\t\t\treturn (\n\t\t\t\tthis.a !== this.b\n\t\t\t\t|| this.c !== this.e\n\t\t\t)\n"
        self.assertTrue(self._changed(base, head))

    def test_a_precedence_changing_paren_edit_is_still_a_change(self):
        """THE control for the whole paren canonicaliser.

        Each pair is the same characters apart from one parenthesis, and each
        pair means two different things. If any of these ever equate, gate-16
        has stopped reporting a real operator-precedence bug.
        """
        pairs = [
            ("(a || b) && c", "a || b && c"),
            ("(a + b) * c", "a + b * c"),
            ("a - (b - c)", "a - b - c"),
            ("a + (b + c)", "a + b + c"),
            ("f((a, b))", "f(a, b)"),
            ("x = (a, b)", "x = a, b"),
            ("(a ? b : c) ? d : e", "a ? b : c ? d : e"),
            ("!(a && b)", "!a && b"),
            ("(a || b).c", "a || b.c"),
            ("(f || g)(x)", "f || g(x)"),
            ("(a || b)[0]", "a || b[0]"),
            ("(await x) ** 2", "await x ** 2"),
            ("typeof (a + b)", "typeof a + b"),
            ("new (a.b)()", "new a.b()"),
            ("('k' in ctx) + 1", "'k' in ctx + 1"),
            ("(a = 1) || b", "a = 1 || b"),
            ("(a, b) => y", "a, b => y"),
            ("({ a: 1 })", "{ a: 1 }"),
            ("/(a)/.test(s)", "/a/.test(s)"),
            ("(a || b) as string", "a || b as string"),
        ]
        for tighter, looser in pairs:
            with self.subTest(pair=tighter):
                self.assertFalse(self._same(tighter, looser),
                                 f"{tighter!r} and {looser!r} are different programs")

    def test_a_redundant_paren_prettier_reprints_is_not_a_change(self):
        """…and the other half: the ones that ARE the same program."""
        pairs = [
            ("return (a || b)", "return a || b"),
            ("x = (a && b) ? c : d", "x = a && b ? c : d"),
            ("map[s] || (s || '-')", "map[s] || s || '-'"),
            ("x = (await f()) || {}", "x = await f() || {}"),
            ("a ? b : (c ? d : e)", "a ? b : c ? d : e"),
            ("x ? (a) : b", "x ? a : b"),
            ("(x) => y", "x => y"),
            ("('k' in ctx) && q", "'k' in ctx && q"),
            ("for (const c of (x || [])) {", "for (const c of x || []) {"),
            ("((a - b) ** 2) / c", "(a - b) ** 2 / c"),
            ("return ({ a: 1 }[k] || 'z')", "return { a: 1 }[k] || 'z'"),
            ("value: `${(this.d?.rate || 0)}%`", "value: `${this.d?.rate || 0}%`"),
        ]
        for wrapped, bare in pairs:
            with self.subTest(pair=wrapped):
                self.assertTrue(self._same(wrapped, bare),
                                f"{wrapped!r} and {bare!r} are one program")

    def test_a_member_named_like_a_keyword_is_a_call_not_an_operator(self):
        # `axios.delete(url)` is a call. Reading its `delete` as the unary
        # operator hands the parentheses a binding power of 14 and welds
        # `axios.deleteurl`. Found on pipelinq's forecastApi.js.
        base = "\t\tconst r = await axios.delete(generateUrl(base + '/x/' + id))\n"
        head = "\t\tconst r = await axios.delete(\n\t\t\tgenerateUrl(base + '/x/' + id),\n\t\t)\n"
        self.assertEqual(self._changed(base, head), set())
        self.assertFalse(self._same("axios.delete(url)", "axios.deleteurl"))

    # --- the ordinary changes, through every rule above --------------------
    def test_a_renamed_method_is_still_reported(self):
        base = "\t\tfetchThings () {\n\t\t\treturn this.load()\n\t\t},\n"
        head = "\t\tfetchItems() {\n\t\t\treturn this.load()\n\t\t},\n"
        self.assertIn(1, self._changed(base, head))

    def test_an_added_parameter_is_still_reported(self):
        base = "\t\tsave (id) {\n\t\t\treturn this.put(id)\n\t\t},\n"
        head = "\t\tsave(id, force) {\n\t\t\treturn this.put(id)\n\t\t},\n"
        self.assertIn(1, self._changed(base, head))

    def test_a_changed_value_in_a_rewrapped_expression_is_still_reported(self):
        base = "\t\tconst total = a * 2 + b\n"
        head = "\t\tconst total =\n\t\t\ta * 3\n\t\t\t+ b\n"
        self.assertTrue(self._changed(base, head))

    def test_a_changed_string_content_is_still_reported(self):
        base = "\t\tshowError(t('app', 'Could not reveal address.'))\n"
        head = "\t\tshowError(\n\t\t\tt('app', 'Could not reveal the address.'),\n\t\t)\n"
        self.assertTrue(self._changed(base, head),
                        "re-quoting and re-wrapping must not carry a CONTENT edit through")

    def test_quote_style_alone_is_not_a_change_in_javascript(self):
        base = '\t\tconst m = "PDF extraction failed"\n'
        head = "\t\tconst m = 'PDF extraction failed'\n"
        self.assertEqual(self._changed(base, head), set())

    def test_an_added_method_is_entirely_in_scope_in_javascript(self):
        base = "export default {\n\tmethods: {\n\t},\n}\n"
        head = ("export default {\n\tmethods: {\n\t\tsave() {\n\t\t\treturn 1\n"
                "\t\t},\n\t},\n}\n")
        changed = self._changed(base, head)
        self.assertTrue({3, 4} <= changed, changed)

    def test_a_semicolon_to_newline_split_is_still_a_change(self):
        # prettier's `semi: false` turns `a; b` into two lines. Equating them
        # needs the same ASI argument the guard above refuses to make, so this
        # is REFUSED — measured cost, 3 findings on pipelinq#820.
        base = "\t\trun(i) { const a = load(); a.splice(i, 1); emit(a) },\n"
        head = "\t\trun(i) {\n\t\t\tconst a = load()\n\t\t\ta.splice(i, 1)\n\t\t\temit(a)\n\t\t},\n"
        self.assertTrue(self._changed(base, head))

    # --- the narrowing can only ever narrow --------------------------------
    def test_the_narrowing_is_an_intersection_with_git(self):
        """`_drop_cosmetic_only` may only REMOVE lines from git's answer."""
        base = "const a = [1, 2]\n"
        head = "const a = [\n\t1,\n\t2,\n]\n"
        changed = csc._substantively_changed_lines(base, head, is_php=False)
        git_says = {1, 2, 3, 4}
        self.assertTrue(changed <= git_says | set(),
                        "normalisation returned a line git never called added")


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


class TagPositionTest(unittest.TestCase):
    """A SENTENCE ABOUT THE TAG IS NOT THE TAG (#415 class, #422).

    ``SPEC_RE`` was an unanchored substring, so any docblock line MENTIONING
    ``@spec openspec/…`` marked the method covered — including the sentence
    stating that nobody has written one. That is the gate that exists to
    COLLECT the gap being closed by a note describing it.

    This one is the borderline case in #422 and the borderline is worth
    stating: ``@spec`` is a docblock marker, so unlike every other gate in that
    issue the evidence legitimately LIVES in a comment and a comment mask would
    delete it. What was missing is POSITION — the anchoring gates 47 and 48
    already have.

    Reverted against origin/main, arms 1 and 2 FLIP. Arms 3-8 pass either way
    and are CONTROLS: they are every spelling the fleet actually uses, and the
    pattern was measured against them exhaustively — 46,187 method judgements
    across the six repos, diff scope bypassed — until it produced ZERO new
    findings. Arm 8 is the one that made the first cut wrong.
    """

    def _findings(self, text: str) -> list[str]:
        findings: list[str] = []
        csc.check_php_file("lib/Service/FooService.php", text, _all_lines(text), findings)
        return findings

    def _method(self, docblock: str) -> str:
        return ("<?php\nclass FooService {\n"
                f"{docblock}"
                "    public function doThing(string $id): string\n"
                "    {\n"
                "        return $id;\n"
                "    }\n"
                "}\n")

    def test_1_a_todo_saying_nobody_wrote_the_tag_is_not_the_tag(self):
        out = self._findings(self._method(
            "    /**\n"
            "     * Do a thing.\n"
            "     *\n"
            "     * TODO: nobody has written @spec openspec/specs/thing/spec.md\n"
            "     * for this yet.\n"
            "     */\n"))
        self.assertEqual(len(out), 1, out)
        self.assertIn("missing @spec", out[0])

    def test_2_a_note_about_a_REMOVED_tag_is_not_the_tag(self):
        """Found in the fleet while measuring the lead class: openregister
        carries `NOTE: this used to read @spec openspec/changes/…`. A note
        recording that the tag was taken away read as the tag."""
        out = self._findings(self._method(
            "    /**\n"
            "     * NOTE: this used to read @spec openspec/changes/dso/tasks.md#T07,\n"
            "     * which was archived.\n"
            "     */\n"))
        self.assertEqual(len(out), 1, out)

    def test_3_CONTROL_the_docblock_continuation_form(self):
        """` * @spec …` — 3,726 occurrences in procest alone."""
        self.assertEqual(self._findings(self._method(
            "    /**\n"
            "     * @spec openspec/specs/thing/spec.md\n"
            "     */\n")), [])

    def test_4_CONTROL_the_single_line_docblock_form(self):
        """`/** @spec … */` — 670 in procest, 638 in opencatalogi. The lead
        class must admit SLASHES, which the package's markdown `standalone`
        lead (`^[ \\t>*#-]`) does not: an agent reusing that lead here would
        uncover 1,308 correctly-tagged methods in two repos."""
        self.assertEqual(self._findings(self._method(
            "    /** @spec openspec/specs/thing/spec.md */\n")), [])

    def test_5_CONTROL_a_line_comment_tag_never_counted_and_still_does_not(self):
        """CONTROL, and it corrects a wrong prediction rather than hiding it.

        The fleet carries 109 `// @spec openspec/…` lines (openregister 56,
        procest 43, softwarecatalog 10) and I expected the anchor to have to
        admit them. It does not: `_docblock_block` SKIPS `//` lines when
        looking for the block above a declaration, so a line-comment tag has
        never satisfied this gate — before this change or after. Asserted so
        the next reader does not re-derive the wrong expectation from the
        lead class, which admits `/` for the `/** … */` form only."""
        self.assertEqual(len(self._findings(self._method(
            "    // @spec openspec/specs/thing/spec.md\n"))), 1)

    def test_6_CONTROL_a_reason_bearing_exclude_still_excludes(self):
        self.assertEqual(self._findings(self._method(
            "    /**\n"
            "     * @spec exclude thin DI wiring with no standalone contract\n"
            "     */\n")), [])

    def test_8_CONTROL_description_then_tag_in_a_one_line_docblock(self):
        """CONTROL, AND THE ARM THAT CAUGHT THE FIRST CUT BEING WRONG.

        `/** Description. @spec … */` is the ordinary PHPDoc order — the
        description comes first and the tags follow — and a start-anchor alone
        rejected it. Measured: FIVE real, deliberately tagged methods in
        decidesk's VotingRoundPanel.vue went red, and the only way to close
        them would have been to reflow correct documentation. A gate that
        reddens documented code teaches authors to stop documenting it."""
        self.assertEqual(self._findings(self._method(
            "    /** Rule enum option lists for the dialog."
            " @spec openspec/specs/voting-system/spec.md */\n")), [])

    def test_9_a_debt_sentence_with_no_terminator_is_still_not_a_tag(self):
        """The discriminator between arm 8 and arm 1 is a COMPLETED SENTENCE
        before the tag, so this states what the second alternative does NOT
        admit: a colon is not a sentence terminator."""
        out = self._findings(self._method(
            "    /**\n"
            "     * TODO: still owed: @spec openspec/specs/thing/spec.md\n"
            "     */\n"))
        self.assertEqual(len(out), 1, out)

    def test_7_CONTROL_a_tag_plus_trailing_prose_on_the_same_line(self):
        """The tag OPENS the line's content; what follows it does not matter.
        Anchoring the START is the whole change — anchoring the end too would
        break every `@spec path (see also …)` in the fleet."""
        self.assertEqual(self._findings(self._method(
            "    /**\n"
            "     * @spec openspec/specs/thing/spec.md (see also the ADR)\n"
            "     */\n")), [])


if __name__ == "__main__":
    unittest.main()
