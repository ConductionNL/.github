#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_markup_a11y (gate-31 img-alt, gate-32 semantic-controls).

Run with:  python3 scripts/lib/test_check_markup_a11y.py

Every case that must NOT fire has a neighbour built from the same fixture, one
edit apart, that MUST. A gate that has only ever been observed passing is
indistinguishable from a gate that cannot fail — and the whole reason these
two gates needed repair is that they were firing on prose, which is exactly
the failure a careless relaxation converts into firing on nothing.
"""
from __future__ import annotations

import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_markup_a11y as gate  # noqa: E402


def scan(rule: str, src: str, path: str = "src/components/X.vue") -> list[str]:
    return gate.scan_source(rule, path, src)


# The launchpad file that produced `[gate-31] img-alt: FAIL — 1 <img> tag(s)`
# with no `<img>` anywhere in the component (#220).
LAUNCHPAD = """<template>
  <div class="org-nav-item">
    <CnDashboardIcon :icon="item.icon" />
    <span>{{ item.label }}</span>
  </div>
</template>

<script>
/**
 * OrgNavigationItem
 *
 * `CnDashboardIcon` resolves any value the icon picker emits — a URL
 * (→ `<img>`), an SVG string, or a Material icon name.
 */
export default { name: 'OrgNavigationItem' }
</script>
"""

# openbuild's IconUploadSection shape (#235): two REAL images that already
# carry `:alt`, plus two JSDoc mentions that were reported as images.
OPENBUILD = """<template>
  <div>
    <img v-if="iconLightUrl" :src="iconLightUrl" :alt="t('openbuild', 'Light icon')">
    <img v-if="iconDarkUrl" :src="iconDarkUrl" :alt="t('openbuild', 'Dark icon')">
  </div>
</template>

<script>
export default {
  methods: {
    /**
     * @param {Event} e - The `<img>` `error` event fired when the light icon
     *                    fails to load.
     */
    onLightError(e) { this.iconLightUrl = null },
    /**
     * @param {Event} e - The `<img>` `error` event fired when the dark icon
     *                    fails to load.
     */
    onDarkError(e) { this.iconDarkUrl = null },
  },
}
</script>
"""


class TestImgAlt(unittest.TestCase):
    def test_launchpad_component_reports_nothing(self):
        self.assertEqual(scan("img-alt", LAUNCHPAD), [])

    def test_launchpad_component_with_one_real_bad_image_reports_one(self):
        """Anti-widening control. Same file, one tag added."""
        src = LAUNCHPAD.replace(
            '<span>{{ item.label }}</span>',
            '<img src="/badge.png"><span>{{ item.label }}</span>')
        found = scan("img-alt", src)
        self.assertEqual(len(found), 1, found)
        self.assertIn("/badge.png", found[0])

    def test_openbuild_three_findings_become_zero(self):
        self.assertEqual(scan("img-alt", OPENBUILD, "src/dialogs/IconUploadSection.vue"), [])

    def test_openbuild_with_alt_deleted_from_one_image_reports_that_one(self):
        """The measurement that separates 'fixed' from 'switched off'."""
        src = OPENBUILD.replace(' :alt="t(\'openbuild\', \'Dark icon\')"', '')
        found = scan("img-alt", src, "src/dialogs/IconUploadSection.vue")
        self.assertEqual(len(found), 1, found)
        self.assertIn("iconDarkUrl", found[0])

    def test_a_finding_names_the_tag_with_its_attributes(self):
        """The bare `<img>` in a log was the tell that a comment was scored."""
        src = '<template><img src="/a.png" class="x"></template>'
        found = scan("img-alt", src)
        self.assertEqual(len(found), 1)
        self.assertIn('src="/a.png"', found[0])
        self.assertNotEqual(found[0].split(": ", 1)[1], "<img>")

    def test_alt_written_after_an_arrow_function_is_seen(self):
        """`[^>]*` ended the tag at the arrow and lost every later prop."""
        src = ('<template><img :src="items.find(i => i.id === id).url" '
               ':alt="t(\'app\', \'Item\')"></template>')
        self.assertEqual(scan("img-alt", src), [])

    def test_the_same_tag_without_alt_still_fires(self):
        src = '<template><img :src="items.find(i => i.id === id).url"></template>'
        self.assertEqual(len(scan("img-alt", src)), 1)

    def test_commented_out_image_is_not_an_image(self):
        src = '<template><!-- <img src="/old.png"> --></template>'
        self.assertEqual(scan("img-alt", src), [])

    def test_php_template_image_is_in_scope(self):
        """#225: WCAG does not care which templating language made the DOM."""
        src = "<?php // renders an <img> when set ?>\n<img src=\"/logo.png\">\n"
        found = scan("img-alt", src, "templates/settings/admin.php")
        self.assertEqual(len(found), 1, found)
        self.assertIn("/logo.png", found[0])

    def test_php_comment_mentioning_img_is_not_an_image(self):
        src = "<?php // this template renders no <img> at all ?>\n<div id=x></div>\n"
        self.assertEqual(scan("img-alt", src, "templates/settings/admin.php"), [])

    def test_alt_empty_is_accepted(self):
        """Decorative images are declared with alt=\"\" — unchanged rule."""
        self.assertEqual(scan("img-alt", '<template><img src="/d.png" alt=""></template>'), [])

    def test_line_number_addresses_the_original_file(self):
        src = '<template>\n\n  <img src="/a.png">\n</template>\n'
        self.assertTrue(scan("img-alt", src)[0].startswith("src/components/X.vue:3:"))


class TestSemanticControls(unittest.TestCase):
    # softwarecatalog's repaired element plus the comment that described what
    # it replaced. Pre-fix, gate-32 scored the COMMENT and rewording it
    # cleared the gate with the markup byte-identical (#236).
    REPAIRED = """<template>
  <!-- role/tabindex/keydown rather than a bare <div @click>: picking the
       merge target is the consequential choice in this dialog, so it has to
       be reachable from the keyboard. -->
  <div v-for="obj in availableObjects"
       :key="obj.id"
       role="option"
       tabindex="0"
       @click="selectTargetObject(obj)"
       @keydown.enter.prevent="selectTargetObject(obj)">
    {{ obj.title }}
  </div>
</template>
"""

    def test_the_repaired_element_reports_nothing(self):
        self.assertEqual(scan("semantic-controls", self.REPAIRED), [])

    def test_the_comment_alone_reports_nothing(self):
        src = "<template>\n  <!-- a bare <div @click> is what this replaced -->\n  <p>x</p>\n</template>\n"
        self.assertEqual(scan("semantic-controls", src), [])

    def test_a_real_bare_click_div_below_that_comment_still_fires(self):
        """Anti-widening control, and the direction that matters most: a bad
        element must not be explainable away by a comment above it."""
        src = ("<template>\n"
               "  <!-- a bare <div @click> is what this replaced -->\n"
               '  <div @click="pick(obj)">x</div>\n'
               "</template>\n")
        found = scan("semantic-controls", src)
        self.assertEqual(len(found), 1, found)
        self.assertIn("role=", found[0])
        self.assertIn("tabindex=", found[0])
        self.assertIn("@keydown", found[0])

    def test_removing_one_of_the_trio_from_the_repaired_element_fires(self):
        src = self.REPAIRED.replace('       tabindex="0"\n', "")
        found = scan("semantic-controls", src)
        self.assertEqual(len(found), 1, found)
        self.assertIn("missing[tabindex=]", found[0])

    def test_anchor_with_href_is_exempt(self):
        src = '<template><a href="/x" @click="go">x</a></template>'
        self.assertEqual(scan("semantic-controls", src), [])

    def test_anchor_without_href_is_not_exempt(self):
        src = '<template><a @click="go">x</a></template>'
        self.assertEqual(len(scan("semantic-controls", src)), 1)

    def test_click_stop_with_no_handler_is_event_management(self):
        src = "<template><div @click.stop><span/></div></template>"
        self.assertEqual(scan("semantic-controls", src), [])

    def test_click_stop_with_a_real_handler_is_not_exempt(self):
        src = '<template><div @click.stop="pick(o)"><span/></div></template>'
        self.assertEqual(len(scan("semantic-controls", src)), 1)

    def test_click_written_after_an_arrow_function_is_seen(self):
        """The truncation hid violations too — this is a finding the pre-fix
        gate could not report at all."""
        src = ('<template><div :title="opts.find(o => o.id === id).label" '
               '@click="pick()">x</div></template>')
        self.assertEqual(len(scan("semantic-controls", src)), 1)

    def test_component_wrappers_are_out_of_scope(self):
        src = '<template><NcButton @click="go">x</NcButton></template>'
        self.assertEqual(scan("semantic-controls", src), [])


class TestImgAltEmptyOnly(unittest.TestCase):
    """gate-35. The defect was BLINDNESS, so the fire-cases come first."""

    def _img(self, attrs: str) -> str:
        return f"<template><div><img {attrs}></div></template>"

    def test_the_four_camelcase_spellings_the_word_boundary_could_not_match(self):
        # `\\b` is a WORD-character boundary and `U` is a word character, so the
        # old `\\b(avatar|photo|thumbnail|picture)\\b` matched NONE of these.
        for expr in ("user.avatarUrl", "user.thumbnailUrl",
                     "user.photoUrl", "user.pictureUrl"):
            with self.subTest(expr=expr):
                self.assertEqual(len(scan("img-alt-empty-only",
                                          self._img(f':src="{expr}" alt=""'))), 1)

    def test_underscore_is_a_word_character_too(self):
        self.assertEqual(len(scan("img-alt-empty-only",
                                  self._img(':src="user.avatar_url" alt=""'))), 1)

    def test_the_spellings_the_old_rule_already_caught_still_fire(self):
        for expr in ("user.avatar", "user.photo", "user.thumbnail",
                     "/img/headshot.png", "profilePicture"):
            with self.subTest(expr=expr):
                self.assertEqual(len(scan("img-alt-empty-only",
                                          self._img(f':src="{expr}" alt=""'))), 1)

    def test_single_quoted_alt_and_src(self):
        self.assertEqual(len(scan("img-alt-empty-only",
                                  self._img("src='/img/avatar.png' alt=''"))), 1)

    # --- ANTI-WIDENING. Recall must not be bought with noise. ---------------
    def test_a_noun_that_is_only_a_SUBSTRING_does_not_fire(self):
        # The tempting repair — relax `\\b` to a substring match — lights all
        # three of these up. Token EQUALITY after camel/underscore splitting
        # keeps them out.
        for expr in ("user.photographerBio", "gallery.pictures", "thumbnails"):
            with self.subTest(expr=expr):
                self.assertEqual(scan("img-alt-empty-only",
                                      self._img(f':src="{expr}" alt=""')), [])

    def test_a_real_alt_is_not_a_finding(self):
        self.assertEqual(scan("img-alt-empty-only",
                              self._img(':src="user.avatarUrl" alt="Photo of Ada"')), [])
        self.assertEqual(scan("img-alt-empty-only",
                              self._img(':src="user.avatarUrl" :alt="label"')), [])

    def test_decorative_by_name_and_by_shape_stay_silent(self):
        self.assertEqual(scan("img-alt-empty-only",
                              self._img(':src="uploadIcon" alt=""')), [])
        self.assertEqual(scan("img-alt-empty-only",
                              self._img('src="/img/decoration.svg" alt=""')), [])

    def test_prose_in_script_is_not_a_tag(self):
        src = ('<template><div /></template>\n<script>\n'
               '// <img :src="user.avatarUrl" alt=""> in a docblock\n</script>')
        self.assertEqual(scan("img-alt-empty-only", src), [])

    # --- NAMED BY CONTEXT (WCAG H67) ---------------------------------------
    # An empty alt is the CORRECT answer when the enclosing element already
    # takes its accessible name from its own text. The noun test still decides
    # which images are suspicious; the markup decides whether the suspicion
    # survives.
    def test_image_named_by_sibling_text_in_a_link_is_not_a_finding(self):
        src = ('<template><a :href="item.link">'
               '<img :src="item.thumbnailUrl" alt="">'
               "<h4>{{ item.title }}</h4></a></template>")
        self.assertEqual(scan("img-alt-empty-only", src), [])

    def test_figure_button_and_static_text_all_name_the_image(self):
        for src in (
            '<template><figure><img :src="user.photoUrl" alt="">'
            "<figcaption>{{ user.name }}</figcaption></figure></template>",
            '<template><button><img :src="user.avatarUrl" alt="">'
            "<span>Open profile</span></button></template>",
            '<template><a href="/team"><img :src="m.headshotUrl" alt="">'
            "Meet the team</a></template>",
        ):
            with self.subTest(src=src[:48]):
                self.assertEqual(scan("img-alt-empty-only", src), [])

    def test_text_BEFORE_the_image_names_it_too(self):
        src = ('<template><a href="/x"><span>Ada Lovelace</span>'
               '<img :src="user.avatarUrl" alt=""></a></template>')
        self.assertEqual(scan("img-alt-empty-only", src), [])

    # --- ANTI-WIDENING for the exemption above ------------------------------
    def test_a_link_whose_ONLY_content_is_the_image_still_fires(self):
        # The image is the link's only possible accessible name, so alt=""
        # leaves it nameless. An exemption keyed on "inside a link" rather than
        # "the link also has text" would wrongly clear this.
        src = ('<template><a :href="user.profile">'
               '<img :src="user.avatarUrl" alt=""></a></template>')
        self.assertEqual(len(scan("img-alt-empty-only", src)), 1)

    def test_a_plain_div_wrapper_is_not_name_giving(self):
        # `<div>` takes no accessible name from its text, so neighbouring
        # prose does NOT excuse the empty alt.
        src = ('<template><div><img :src="user.avatarUrl" alt="">'
               "<h4>Ada</h4></div></template>")
        self.assertEqual(len(scan("img-alt-empty-only", src)), 1)

    def test_a_sibling_link_does_not_excuse_an_image_outside_it(self):
        # The image is NOT inside the named element — no exemption.
        src = ('<template><div><img :src="user.avatarUrl" alt="">'
               "<a href='/x'>Ada Lovelace</a></div></template>")
        self.assertEqual(len(scan("img-alt-empty-only", src)), 1)


class TestTabindexPositive(unittest.TestCase):
    """gate-36. The defect was NOISE, so the silence-cases come first."""

    def test_a_positive_tabindex_in_an_HTML_COMMENT_is_not_a_finding(self):
        src = ('<template><div>\n'
               '<!-- never write tabindex="5"; it breaks focus order -->\n'
               '<button tabindex="0">ok</button>\n</div></template>')
        self.assertEqual(scan("tabindex-positive", src), [])

    def test_a_positive_tabindex_in_a_JS_COMMENT_is_not_a_finding(self):
        src = ('<template><div /></template>\n<script>\n'
               '// forbidden: tabindex="9"\nexport default {}\n</script>')
        self.assertEqual(scan("tabindex-positive", src), [])

    def test_zero_and_minus_one_and_bound_values_are_correct_code(self):
        for attr in ('tabindex="0"', 'tabindex="-1"', ':tabindex="n"'):
            with self.subTest(attr=attr):
                self.assertEqual(
                    scan("tabindex-positive", f"<template><b {attr}>x</b></template>"), [])

    # --- the true positives the noise fix must not cost ---------------------
    def test_a_real_positive_tabindex_still_fires(self):
        self.assertEqual(
            len(scan("tabindex-positive", '<template><b tabindex="5">x</b></template>')), 1)

    def test_single_quotes_render_the_same_DOM(self):
        self.assertEqual(
            len(scan("tabindex-positive", "<template><b tabindex='12'>x</b></template>")), 1)

    def test_a_tabindex_EMITTED_FROM_SCRIPT_still_fires(self):
        # `markup_mask` would blank `<script>` wholesale and lose this. The mask
        # here is comments-only for exactly that reason.
        src = ('<template><div /></template>\n<script>\n'
               'el.innerHTML = \'<button tabindex="4">x</button>\'\n</script>')
        self.assertEqual(len(scan("tabindex-positive", src)), 1)

    def test_a_js_file_keeps_both_behaviours(self):
        fire = 'export const h = \'<b tabindex="3">x</b>\'\n'
        self.assertEqual(len(scan("tabindex-positive", fire, "src/h.js")), 1)
        quiet = '// tabindex="3" is forbidden\nexport const h = 1\n'
        self.assertEqual(scan("tabindex-positive", quiet, "src/h.js"), [])


class TestCli(unittest.TestCase):
    def test_unknown_rule_is_an_error_not_an_empty_answer(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = gate.main(["check_markup_a11y.py", "--rule", "nonsense", "x.vue"])
        self.assertEqual(rc, 2)
        self.assertEqual(buf.getvalue(), "")

    def test_missing_arguments_is_an_error(self):
        self.assertEqual(gate.main(["check_markup_a11y.py"]), 2)

    def test_an_unreadable_file_is_skipped_not_fatal(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = gate.main(["check_markup_a11y.py", "--rule", "img-alt", "/nope/x.vue"])
        self.assertEqual(rc, 0)
        self.assertEqual(buf.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
