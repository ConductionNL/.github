#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for source_scope — the shared "where is the code" masks.

Run with:  python3 scripts/lib/test_source_scope.py

EVERY relaxation here is paired with the true positive it must not swallow.
The whole family of bugs this module fixes came from a checker that could not
tell code from prose; the way to reintroduce it is to write a mask that blanks
too much and then only ever test that it stops firing. So each "must not
match" case has a neighbouring "must still match" case built from the same
fixture with one edit.

⚠️ A TRAP KEPT ON PURPOSE
-------------------------
`test_a_fixture_cannot_exempt_itself_with_its_own_docblock` reproduces the
thing that bit an earlier agent on exactly this work: a fixture written to
DISPROVE a rule exempted itself with its own explanatory comment, because the
comment named the construct under test. The fixture below keeps its
explanatory docblock AND the real construct, and asserts the mask separates
them.
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import source_scope as ss  # noqa: E402
import check_e2e_coverage as cec  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


class TestOffsetsSurvive(unittest.TestCase):
    """A mask that moves offsets is useless: every caller reports line numbers
    from the mask and reads suppression markers out of the ORIGINAL."""

    CORPUS = [
        ("js", "const a = 1 // note\nconst b = 'x'\n"),
        ("js", "/* block\n   spanning */\nlet q = `t${1}`\n"),
        ("php", "<?php\n// c\n#[Attr]\n$x = 'y'; # trailing\n"),
        ("markup", "<template>\n<!-- c -->\n<img src=x>\n</template>\n<script>\n// j\n</script>\n"),
    ]

    def test_same_length_and_same_line_count(self):
        for kind, src in self.CORPUS:
            fn = {"js": ss.js_code_mask, "php": ss.php_mask,
                  "markup": lambda s: ss.markup_mask(s, "f.vue")}[kind]
            out = fn(src)
            self.assertEqual(len(out), len(src), f"{kind}: length changed")
            self.assertEqual(out.count("\n"), src.count("\n"), f"{kind}: lines changed")

    def test_line_number_of_a_kept_token_is_unchanged(self):
        src = "// <img>\n// <img>\n<img src=a>\n"
        masked = ss.html_markup_mask(src)
        # `//` is not an HTML comment, so this one is deliberately still there.
        self.assertEqual(masked.count("<img"), 3)
        src2 = "<!-- <img> -->\n<!-- <img> -->\n<img src=a>\n"
        masked2 = ss.html_markup_mask(src2)
        idx = masked2.index("<img")
        self.assertEqual(masked2.count("\n", 0, idx) + 1, 3,
                         "the surviving tag must still be on line 3")


class TestPhpMask(unittest.TestCase):
    def test_hash_bracket_is_an_attribute_not_a_comment(self):
        """#184's distinction. Losing it deletes every NC auth attribute."""
        src = "#[NoAdminRequired]\npublic function f() {}\n"
        self.assertIn("#[NoAdminRequired]", ss.php_mask(src))

    def test_bare_hash_is_a_comment(self):
        src = "# NoAdminRequired is not used here\n$x = 1;\n"
        self.assertNotIn("NoAdminRequired", ss.php_mask(src))
        self.assertIn("$x = 1;", ss.php_mask(src))

    def test_docblock_mention_of_an_attribute_is_blanked(self):
        """#196 in one assertion: the sentence that switched gate-5 off."""
        src = (
            "    /**\n"
            "     * ADMIN ONLY: `#[NoAdminRequired]` is deliberately NOT used here.\n"
            "     */\n"
            "    public function analytics(): JSONResponse\n"
        )
        masked = ss.php_mask(src)
        self.assertNotIn("NoAdminRequired", masked)
        self.assertIn("public function analytics", masked)

    def test_a_real_attribute_above_the_same_method_survives(self):
        """The anti-widening control for the case above."""
        src = (
            "    /**\n"
            "     * Analytics.\n"
            "     */\n"
            "    #[NoAdminRequired]\n"
            "    public function analytics(): JSONResponse\n"
        )
        self.assertIn("#[NoAdminRequired]", ss.php_mask(src))

    def test_slash_slash_inside_a_string_does_not_open_a_comment(self):
        src = "$u = 'https://example.test/x'; $keep = 1;\n"
        self.assertIn("$keep = 1;", ss.php_mask(src))

    def test_commented_out_code_is_blanked_both_ways(self):
        """#184's false GREEN: a commented-OUT prelude counted as a prelude."""
        src = "// \\OC_App::registerAutoloading('openregister', $p);\n"
        self.assertNotIn("registerAutoloading", ss.php_mask(src))


class TestVueMarkupMask(unittest.TestCase):
    LAUNCHPAD = (
        "<template>\n"
        '  <div class="nav"><CnDashboardIcon :icon="icon" /></div>\n'
        "</template>\n"
        "\n"
        "<script>\n"
        "/**\n"
        " * resolves any value the icon picker emits — a URL (→ `<img>`), an SVG\n"
        " */\n"
        "export default {}\n"
        "</script>\n"
    )

    def test_img_inside_a_jsdoc_comment_is_not_markup(self):
        """#220 / #235, on the real shape from launchpad and openbuild."""
        masked = ss.vue_markup_mask(self.LAUNCHPAD)
        self.assertNotIn("<img", masked)

    def test_a_real_img_in_the_template_survives(self):
        """Anti-widening control: the same file with one real tag added."""
        src = self.LAUNCHPAD.replace(
            '<div class="nav">', '<div class="nav"><img src="/a.png">')
        masked = ss.vue_markup_mask(src)
        self.assertIn("<img", masked)
        tags = list(ss.iter_open_tags(masked, {"img"}))
        self.assertEqual(len(tags), 1)

    def test_openbuild_finding_shape_is_gone(self):
        """The finding text was the tell: a bare `<img>` with no attributes."""
        src = (
            "<template><span/></template>\n"
            "<script>\n"
            " * @param {Event} e - The `<img>` `error` event fired when the icon\n"
            "</script>\n"
        )
        self.assertEqual(list(ss.iter_open_tags(ss.vue_markup_mask(src), {"img"})), [])

    def test_html_comment_in_the_template_is_blanked(self):
        """#236 part 2: the comment describing the div it replaced was scored."""
        src = (
            "<template>\n"
            "  <!-- role/tabindex/keydown rather than a bare <div @click>: picking\n"
            "       the merge target is the consequential choice here -->\n"
            '  <div role="option" tabindex="0" @click="pick" @keydown.enter="pick" />\n'
            "</template>\n"
        )
        masked = ss.vue_markup_mask(src)
        tags = [t for t in ss.iter_open_tags(masked, {"div"})]
        self.assertEqual(len(tags), 1)
        self.assertIn("role=", tags[0].attrs)

    def test_a_real_bad_div_next_to_that_comment_still_matches(self):
        """Anti-widening control for the case above."""
        src = (
            "<template>\n"
            "  <!-- a bare <div @click> is what this replaced -->\n"
            '  <div @click="pick" />\n'
            "</template>\n"
        )
        tags = list(ss.iter_open_tags(ss.vue_markup_mask(src), {"div"}))
        self.assertEqual(len(tags), 1)
        self.assertIn("@click", tags[0].attrs)

    def test_a_fixture_cannot_exempt_itself_with_its_own_docblock(self):
        """THE TRAP, kept deliberately.

        A fixture written to disprove the rule described the construct in its
        own explanatory comment. Under the pre-fix flat grep the comment WAS
        the finding, so the fixture "proved" whatever the author wanted. Here
        the comment and the construct are both present and the mask must
        separate them: one real tag, not two, and not zero.
        """
        src = (
            "<template>\n"
            "  <!-- This fixture exists to show that `<img>` written in prose is\n"
            "       not an image. The tag below IS one and must still count. -->\n"
            '  <img src="/real.png">\n'
            "</template>\n"
        )
        tags = list(ss.iter_open_tags(ss.vue_markup_mask(src), {"img"}))
        self.assertEqual(len(tags), 1, "exactly the real tag, not the prose one")
        self.assertIn("src=", tags[0].attrs)

    def test_no_template_block_means_no_markup(self):
        src = "<script>\n// <img> in prose\n</script>\n"
        self.assertEqual(ss.vue_markup_mask(src).strip(), "")

    def test_a_nested_slot_template_does_not_end_the_block(self):
        """MEASURED REGRESSION, caught on openconnector before this landed.

        `<template #default>` is a slot, written INSIDE the SFC's template. A
        lazy `<template…>(.*?)</template>` ends the block at the first slot
        close, and everything below it — including a real unlabelled
        `<NcSelect>` at EditMapping.vue:376 — silently stops being scanned.
        A relaxation that deletes true positives is the fix over-applied, and
        the whole point of this change is that it must not happen.
        """
        src = (
            "<template>\n"
            "  <NcDialog>\n"
            "    <template #default>\n"
            "      <span>a</span>\n"
            "    </template>\n"
            "    <template #actions>\n"
            "      <span>b</span>\n"
            "    </template>\n"
            "  </NcDialog>\n"
            '  <img src="/late.png">\n'
            "</template>\n"
            "<script>\n// <img> in prose\n</script>\n"
        )
        tags = list(ss.iter_open_tags(ss.vue_markup_mask(src), {"img"}))
        self.assertEqual(len(tags), 1, "the tag after the slots must survive")
        self.assertIn("/late.png", tags[0].attrs)
        self.assertNotIn("in prose", ss.vue_markup_mask(src))

    def test_a_self_closing_template_opens_nothing(self):
        src = '<template>\n  <template v-if="x" />\n  <img src="/a.png">\n</template>\n'
        self.assertEqual(len(list(ss.iter_open_tags(ss.vue_markup_mask(src), {"img"}))), 1)

    def test_an_unbalanced_template_open_keeps_the_rest_of_the_file(self):
        """Dropping it would blank everything — a false green by parse error."""
        src = '<template>\n  <img src="/a.png">\n'
        self.assertEqual(len(list(ss.iter_open_tags(ss.vue_markup_mask(src), {"img"}))), 1)


class TestPhpMarkupMask(unittest.TestCase):
    FRAGMENT = (
        "<?php\n"
        "// This mount point is substituted into core's page. Core emitted the\n"
        "// <html> element for it, with its lang attribute, long before this file.\n"
        "?>\n"
        '<div id="app-settings"></div>\n'
    )

    def test_html_named_in_a_php_comment_is_not_emitted(self):
        """#266 verbatim."""
        self.assertNotIn("<html", ss.php_markup_mask(self.FRAGMENT))

    def test_a_template_that_really_emits_html_still_matches(self):
        """Anti-widening control."""
        src = "<?php // a standalone page ?>\n<html>\n<body>x</body>\n</html>\n"
        self.assertIn("<html>", ss.php_markup_mask(src))

    def test_html_comment_hiding_a_lang_attribute_does_not_satisfy_the_gate(self):
        """The other direction #266 names: a commented-out `<html lang>` must
        not vouch for a real unlangged one."""
        src = '<!-- <html lang="en"> -->\n<html>\n'
        masked = ss.php_markup_mask(src)
        self.assertEqual(masked.count("<html"), 1)
        self.assertNotIn("lang=", masked)

    def test_jsdoc_img_in_an_inline_script_is_not_markup(self):
        src = (
            "<div id=x></div>\n"
            "<script>\n"
            "// renders an `<img>` when a URL is picked\n"
            "</script>\n"
        )
        self.assertEqual(list(ss.iter_open_tags(ss.php_markup_mask(src), {"img"})), [])


class TestTagExtraction(unittest.TestCase):
    def test_an_arrow_function_does_not_end_the_element(self):
        """#236 part 1: `[^>]*` stopped at the `>` of `option => option.value`."""
        src = (
            "<template>\n"
            "  <NcSelect\n"
            '    :reduce="option => option.value"\n'
            '    :options="opts"\n'
            '    input-label="Transport Type" />\n'
            "</template>\n"
        )
        tags = list(ss.iter_open_tags(ss.vue_markup_mask(src), {"NcSelect"}))
        self.assertEqual(len(tags), 1)
        self.assertIn("input-label", tags[0].attrs,
                      "the prop written after the reducer must be visible")

    def test_the_same_element_without_the_label_is_still_extracted(self):
        """Anti-widening control: fixing extraction must not stop findings."""
        src = (
            "<template>\n"
            '  <NcSelect :reduce="option => option.value" :options="opts" />\n'
            "</template>\n"
        )
        tags = list(ss.iter_open_tags(ss.vue_markup_mask(src), {"NcSelect"}))
        self.assertEqual(len(tags), 1)
        self.assertNotIn("input-label", tags[0].attrs)

    def test_two_elements_are_not_greedily_merged(self):
        """The trap a naive `.*?`-less fix falls into."""
        src = (
            "<template>\n"
            '  <NcSelect input-label="A" />\n'
            '  <NcSelect :options="o" />\n'
            "</template>\n"
        )
        tags = list(ss.iter_open_tags(ss.vue_markup_mask(src), {"NcSelect"}))
        self.assertEqual(len(tags), 2)
        self.assertIn("input-label", tags[0].attrs)
        self.assertNotIn("input-label", tags[1].attrs)

    def test_closing_tags_are_not_reported(self):
        src = "<template><div>x</div></template>"
        tags = list(ss.iter_open_tags(ss.vue_markup_mask(src), {"div"}))
        self.assertEqual(len(tags), 1)

    def test_line_numbers_address_the_original_file(self):
        src = "<template>\n\n\n  <img src=a>\n</template>\n"
        tags = list(ss.iter_open_tags(ss.vue_markup_mask(src), {"img"}))
        self.assertEqual(tags[0].line, 4)


class TestScriptMask(unittest.TestCase):
    def test_a_comment_mentioning_window_confirm_is_blanked(self):
        """#224 arm 1: the false RED."""
        src = (
            "<template>\n"
            "  <!-- This component deliberately avoids window.confirm() and uses NcDialog. -->\n"
            '  <NcDialog :open="open" />\n'
            "</template>\n"
        )
        self.assertNotIn("window.confirm", ss.script_mask(src, "a.vue"))

    def test_a_real_call_in_the_same_file_still_shows(self):
        """#224 arm 4: the control that proves the probe can fire."""
        src = (
            "<template>\n"
            "  <!-- avoids window.confirm() -->\n"
            "</template>\n"
            "<script>\n"
            "export default { methods: { d() { if (window.confirm('x')) {} } } }\n"
            "</script>\n"
        )
        masked = ss.script_mask(src, "a.vue")
        self.assertEqual(masked.count("window.confirm"), 1)

    def test_string_literals_survive_the_comment_mask(self):
        """gate-58's whole evidence is a string literal."""
        src = "await page.goto(u, { waitUntil: 'networkidle' })\n"
        self.assertIn("'networkidle'", ss.js_comment_mask(src))

    def test_a_comment_warning_against_networkidle_is_blanked(self):
        """#230, the larpingapp line verbatim."""
        src = (
            "// live `waitForLoadState('networkidle')` in the suite; every other mention\n"
            "await page.waitForLoadState('domcontentloaded')\n"
        )
        masked = ss.js_comment_mask(src)
        self.assertNotIn("networkidle", masked)
        self.assertIn("domcontentloaded", masked)

    def test_a_real_call_with_a_trailing_comment_still_matches(self):
        """Anti-widening control: a line-position filter would lose this."""
        src = "await page.waitForLoadState('networkidle') // TODO remove\n"
        self.assertIn("waitForLoadState('networkidle')", ss.js_comment_mask(src))

    def test_a_slash_inside_a_string_does_not_open_a_comment(self):
        src = "const u = 'http://x/networkidle'\nawait f()\n"
        self.assertIn("await f()", ss.js_comment_mask(src))

    def test_an_inline_handler_in_a_vue_template_is_script(self):
        src = "<template><button @click=\"window.confirm('x') && go()\">g</button></template>\n"
        self.assertIn("window.confirm", ss.script_mask(src, "a.vue"))

    def test_a_script_end_tag_with_junk_still_ends_the_script(self):
        """CodeQL py/bad-tag-filter, HIGH, raised against this change.

        `</script\\s*>` does not match `</script bar>`, and an HTML parser DOES
        end the element there. The block regex then fails to match AT ALL, the
        script body is never comment-masked, and a JSDoc `<img>` inside it is
        scanned as markup — which is #235 exactly, reintroduced by the mask
        meant to fix it.

        ⚠️ The first version of this test used `vue_markup_mask`, which does
        not go through `_SCRIPT_BLOCK` at all, and the mutant SURVIVED. Assert
        the mutation applies AND kills before believing a mutation test.
        """
        src = (
            "<script>\n"
            "// renders an <img src=x> when a URL is picked\n"
            "</script bar>\n"
            '<img src="/real.png">\n'
        )
        tags = list(ss.iter_open_tags(ss.html_markup_mask(src), {"img"}))
        self.assertEqual(len(tags), 1, "only the real tag; the JSDoc one is in script")
        self.assertIn("/real.png", tags[0].attrs)

    def test_a_script_end_tag_with_whitespace_and_junk(self):
        src = (
            "<div id=x></div>\n"
            "<script>\n"
            "// this template avoids window.confirm entirely\n"
            "</script\t\n foo>\n"
        )
        self.assertNotIn("window.confirm", ss.script_mask(src, "templates/a.php"))

    def test_style_block_is_blanked(self):
        src = "<template><i/></template>\n<style>/* window.confirm */ .a{}</style>\n"
        self.assertNotIn("window.confirm", ss.script_mask(src, "a.vue"))


class TestSharedWithGate19(unittest.TestCase):
    """The shared mask and gate-19's own must be byte-identical.

    Gate-19 keeps its copy because its 60-assertion suite is what proves the
    tokeniser correct, and moving it under that suite mid-change would be a
    bad trade. Two copies that are PROVEN equal are a maintenance cost; two
    copies that MIGHT differ are a defect. This test is the proof, and it is
    mutation-checked: flip one branch of either copy and it goes red.
    """

    CORPUS = [
        "const a = 1 // note\n",
        "/* b */ test('x', async () => {})\n",
        "const r = /a\\/b/g; const d = 4 / 2\n",
        "const t = `a${'b'}c`\n",
        "test.skip('name', fn)\ntest.skip(cond, 'reason')\n",
        "const s = 'unterminated\nnext()\n",
        "if (x) test.skip(true, 'why') // trailing\n",
        "const u = 'http://x//y'\n",
        "await page.waitForLoadState('networkidle')\n",
        # One per regex-position keyword. Dropping any single entry from
        # either copy's keyword set must be caught, and a corpus that only
        # exercises `return` cannot do that — measured: the first draft of
        # this test SURVIVED deleting "await" from the shared set.
        *[f"x = {kw} /a'b/.test(s)\n" for kw in sorted(cec._JS_REGEX_KEYWORDS)],
    ]

    def test_the_keyword_sets_are_the_same(self):
        """The cheapest drift there is, and the corpus alone did not see it."""
        self.assertEqual(ss._JS_REGEX_KEYWORDS, cec._JS_REGEX_KEYWORDS)

    def test_identical_over_the_corpus(self):
        for src in self.CORPUS:
            self.assertEqual(ss.js_code_mask(src), cec._code_mask(src),
                             f"masks diverged on {src!r}")

    def test_identical_over_this_packages_own_js_sources(self):
        seen = 0
        for name in sorted(os.listdir(HERE)):
            if not name.endswith(".js"):
                continue
            with open(os.path.join(HERE, name), encoding="utf-8", errors="replace") as f:
                src = f.read()
            self.assertEqual(ss.js_code_mask(src), cec._code_mask(src), name)
            seen += 1
        self.assertGreater(seen, 0, "no .js sources found — this test measured nothing")


class TestHtmlCommentDelimiterScope(unittest.TestCase):
    """#424 group 2 — `<!--` is only a comment opener where it can BE one.

    Every relaxation below is paired with the true positive it must not
    swallow, and the whole class is mutation-checked against the regex it
    replaces: `_HTML_COMMENT` is still in the module, and
    `test_the_old_regex_still_fails_this` asserts it disagrees. Flip
    `html_comment_spans` back to the regex and five arms below go red.

    WHICH ARM IS EVIDENCE AND WHICH IS A CONTROL, measured by running this
    class against `html_comment_spans = _HTML_COMMENT.finditer`:

      EVIDENCE (red under the mutation, green after the fix)
        test_interpolated_delimiter_does_not_blank_the_markup_between
        test_delimiter_in_a_quoted_attribute_value_opens_nothing
        test_a_string_in_a_script_body_is_script_data_not_a_comment_opener
        test_script_mask_keeps_a_call_between_two_delimiter_strings
        test_an_unterminated_comment_still_runs_to_end_of_file

      CONTROL (green BOTH ways — they prove the fix did not over-relax, and
      they are not evidence that it did anything)
        test_a_real_comment_is_still_blanked
        test_a_real_comment_after_an_interpolation_is_still_blanked
        test_a_real_comment_after_a_tag_with_a_quoted_gt_is_still_blanked
        test_quotes_in_a_TEXT_node_do_not_protect_the_opener
        test_a_js_comment_in_that_script_body_is_still_blanked
        test_an_unterminated_interpolation_does_not_swallow_the_file
        test_an_unterminated_quote_does_not_swallow_the_file
        test_offsets_survive_the_scanner
    """

    # The exact shape measured on main, from the issue.
    HOLE = (
        "<p>{{ '<!--' }}</p>\n"
        '<img alt="" src="/a/avatarUrl.png">\n'
        "<p>{{ '-->' }}</p>"
    )

    def test_interpolated_delimiter_does_not_blank_the_markup_between(self):
        out = ss.markup_mask(self.HOLE, "f.html")
        self.assertIn('<img alt="" src="/a/avatarUrl.png">', out)

    def test_the_old_regex_still_fails_this(self):
        """The MUTATION CONTROL. If this ever passes, the arm above is inert."""
        old = ss._HTML_COMMENT.sub("", self.HOLE)
        self.assertNotIn("<img", old)

    def test_delimiter_in_a_quoted_attribute_value_opens_nothing(self):
        src = '<img alt="<!--" src="/a/avatarUrl.png">\n<img alt="" src="/b/-->.png">'
        out = ss.markup_mask(src, "f.html")
        self.assertEqual(out, src)

    def test_a_real_comment_is_still_blanked(self):
        """The paired true positive: relaxing the opener must not stop the
        gate seeing a commented-out element as commented out."""
        src = '<!-- <img src="/a/old.png"> -->\n<p>x</p>\n'
        out = ss.markup_mask(src, "f.html")
        self.assertNotIn("<img", out)
        self.assertIn("<p>x</p>", out)

    def test_a_real_comment_after_an_interpolation_is_still_blanked(self):
        src = '<p>{{ label }}</p>\n<!-- <img src="/a/old.png"> -->\n'
        self.assertNotIn("<img", ss.markup_mask(src, "f.html"))

    def test_a_real_comment_after_a_tag_with_a_quoted_gt_is_still_blanked(self):
        src = ('<NcSelect :reduce="option => option.value" />\n'
               '<!-- <img src="/a/old.png"> -->\n')
        self.assertNotIn("<img", ss.markup_mask(src, "f.html"))

    def test_quotes_in_a_TEXT_node_do_not_protect_the_opener(self):
        """A browser has no string literals in text: this really is a comment,
        and pretending otherwise would be the over-relaxed direction."""
        src = "<p>'<!--' <img src=\"/a/x.png\"> '-->'</p>"
        self.assertNotIn("<img", ss.markup_mask(src, "f.html"))

    def test_a_string_in_a_script_body_is_script_data_not_a_comment_opener(self):
        # The two delimiter strings sit in DIFFERENT script bodies with live
        # markup between them, so the old regex really does blank the <img>.
        src = ('<script>\nconst OPEN = "<!--"\n</script>\n'
               '<img alt="" src="/a/avatarUrl.png">\n'
               '<script>\nconst CLOSE = "-->"\n</script>\n')
        self.assertIn('<img alt="" src="/a/avatarUrl.png">',
                      ss.html_markup_mask(src))

    def test_a_js_comment_in_that_script_body_is_still_blanked(self):
        """Paired: the script body is handed to the tokeniser that knows JS."""
        src = '<script>\n// <img src="/a/old.png">\n</script>\n'
        self.assertNotIn("<img", ss.html_markup_mask(src))

    def test_an_unterminated_interpolation_does_not_swallow_the_file(self):
        src = '<p>{{ oops</p>\n<!-- <img src="/a/old.png"> -->\n<p>y</p>\n'
        out = ss.markup_mask(src, "f.html")
        self.assertNotIn("<img", out)      # the real comment still went
        self.assertIn("<p>y</p>", out)     # and nothing after it was eaten

    def test_an_unterminated_quote_does_not_swallow_the_file(self):
        src = '<p title="oops>\n<!-- <img src="/a/old.png"> -->\n<p>y</p>\n'
        self.assertIn("<p>y</p>", ss.markup_mask(src, "f.html"))

    def test_an_unterminated_comment_still_runs_to_end_of_file(self):
        src = '<p>a</p>\n<!-- <img src="/a/old.png">\n'
        self.assertNotIn("<img", ss.markup_mask(src, "f.html"))

    def test_offsets_survive_the_scanner(self):
        for src in (self.HOLE, '<!-- c -->\n<p>x</p>\n', '<script>"<!--"</script>\n'):
            out = ss.mask_html_comments(src)
            self.assertEqual(len(out), len(src))
            self.assertEqual(out.count("\n"), src.count("\n"))

    def test_script_mask_keeps_a_call_between_two_delimiter_strings(self):
        """gate-34/58 read `script_mask`; the same hole was armed there."""
        src = ("<template>\n  <p>{{ '<!--' }}</p>\n"
               "  <button @click=\"window.confirm('sure?')\">go</button>\n"
               "  <p>{{ '-->' }}</p>\n</template>\n")
        self.assertIn("window.confirm", ss.script_mask(src, "f.vue"))


class TestPhpHeredoc(unittest.TestCase):
    """#424 adopting #429 — a heredoc body is a string, not code.

    gate-50's private stripper grew this handling in #429 and gate-50 now calls
    `php_mask` instead, so the capability had to move here first. These arms
    are what make that a move rather than a loss.

    Mutation-checked: delete the `<<<` branch from `php_mask` and the first
    four go red. `test_a_heredoc_body_survives_the_default_mask` is the CONTROL
    — the body is evidence in the default mode and must not be blanked.
    """

    SRC = (
        "<?php\n"
        "$sql = <<<SQL\n"
        "  SELECT * FROM t -- keep\n"
        "  // not a comment\n"
        "  it's fine { unbalanced\n"
        "SQL;\n"
        "// this IS a comment\n"
        "return null;\n"
    )

    def test_a_slash_slash_inside_a_heredoc_is_not_a_comment(self):
        self.assertIn("// not a comment", ss.php_mask(self.SRC))

    def test_an_apostrophe_inside_a_heredoc_opens_no_string(self):
        """Without heredoc awareness the `'` in `it's` opens a literal that
        runs to the next stray quote, and everything between stops being
        parsed — the swallow this module keeps finding new spellings of."""
        self.assertNotIn("this IS a comment", ss.php_mask(self.SRC))

    def test_the_real_comment_after_the_heredoc_is_still_blanked(self):
        masked = ss.php_mask(self.SRC)
        self.assertIn("return null;", masked)
        self.assertNotIn("this IS a comment", masked)

    def test_the_structural_copy_blanks_the_body_and_balances_braces(self):
        blob = ss.php_mask(self.SRC, blank_strings=True)
        self.assertNotIn("unbalanced", blob)
        self.assertEqual(blob.count("{"), blob.count("}"))

    def test_a_heredoc_body_survives_the_default_mask(self):
        """CONTROL: default mode keeps string contents, heredocs included."""
        self.assertIn("SELECT * FROM t", ss.php_mask(self.SRC))

    def test_nowdoc_and_quoted_labels_are_recognised(self):
        for opener in ("<<<'SQL'", '<<<"SQL"', "<<<SQL"):
            src = f"<?php\n$x = {opener}\n  it's {{ here\nSQL;\n// c\n"
            self.assertNotIn("c", ss.php_mask(src).split("\n")[-2], opener)

    def test_an_indented_closing_label_closes_it(self):
        src = "<?php\n$x = <<<SQL\n  body\n    SQL;\n// c\n$y = 1;\n"
        masked = ss.php_mask(src)
        self.assertIn("$y = 1;", masked)
        self.assertNotIn("// c", masked)

    def test_an_unterminated_heredoc_runs_to_end_of_file(self):
        """The language's own rule, and the safe direction: it cannot leak
        heredoc text back into code scope."""
        src = "<?php\n$x = <<<SQL\nbody\n"
        self.assertEqual(len(ss.php_mask(src)), len(src))

    def test_offsets_survive_in_both_modes(self):
        for kw in ({}, {"blank_strings": True}):
            out = ss.php_mask(self.SRC, **kw)
            self.assertEqual(len(out), len(self.SRC))
            self.assertEqual(out.count("\n"), self.SRC.count("\n"))


class TestStartsInCode(unittest.TestCase):
    """The anchoring predicate gates 10 and 11 read (#424)."""

    JS = "const doc = \"document.getElementById('x').dataset.v\"\n" \
         "const v = document.getElementById('x').dataset.v\n"

    def setUp(self):
        self.anchor = ss.js_code_mask(self.JS)
        self.evidence = ss.js_comment_mask(self.JS)

    def test_the_two_masks_stay_aligned(self):
        self.assertEqual(len(self.anchor), len(self.evidence))

    def test_a_token_inside_a_literal_is_not_code(self):
        i = self.JS.index("document")           # the one in quotes
        self.assertFalse(ss.starts_in_code(self.anchor, self.evidence, i))

    def test_the_same_token_outside_a_literal_is_code(self):
        i = self.JS.index("document", self.JS.index("\n"))
        self.assertTrue(ss.starts_in_code(self.anchor, self.evidence, i))

    def test_php_masks_align_too(self):
        src = "<?php\n$doc = 'return null;';\nreturn null;\n"
        a = ss.php_mask(src, blank_strings=True)
        e = ss.php_mask(src)
        self.assertEqual(len(a), len(e))
        self.assertFalse(ss.starts_in_code(a, e, src.index("return")))
        self.assertTrue(ss.starts_in_code(a, e, src.rindex("return")))

    def test_an_out_of_range_offset_is_not_code(self):
        """It must not raise: a caller with a stale offset gets a False, and
        False can only ever UNDER-report."""
        self.assertFalse(ss.starts_in_code("a", "a", 99))
        self.assertFalse(ss.starts_in_code("a", "a", -1))


class TestCli(unittest.TestCase):
    """The bash gates call this module as a process; a broken CLI is a dead
    gate, so it is exercised the way they call it."""

    def _run(self, args, stdin=""):
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "source_scope.py"), *args],
            input=stdin, capture_output=True, text=True,
        )

    def test_php_mask_from_stdin(self):
        r = self._run(["--mask", "php", "-"], "// x NoAdminRequired\n#[NoAdminRequired]\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.count("NoAdminRequired"), 1)

    def test_unknown_kind_is_an_error_not_an_empty_answer(self):
        r = self._run(["--mask", "nonsense", "-"], "x")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")

    def test_no_arguments_is_an_error(self):
        self.assertEqual(self._run([]).returncode, 2)


if __name__ == "__main__":
    unittest.main()
