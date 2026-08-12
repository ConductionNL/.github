#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_icon_vocabulary (gate 60). Run with:

    python3 scripts/lib/test_check_icon_vocabulary.py

WHY THIS SUITE EXISTS
---------------------
Gate 60 had NO tests at all, and half of it was unreachable code.

`CONCEPT_LABELS` mapped ten labels, and all ten resolved to **Tier A**
concepts, while `semantic-icons.json` ships **140 Tier B** concepts. So the
`warns.append(... Tier B — SHOULD)` branch could never execute — not for a
badly-chosen glyph, not for any input at all. Measured across 14 fleet repos
and 417 manifests with node_modules installed: **0 warnings, everywhere**. A
green gate-60 said nothing whatsoever about 140 of the 153 concepts it claims
to govern, and three TIER A concepts (`activity`, `admin`, `tutorial`) were
unreachable too — those are MUSTs.

Every class below plants a defect and asserts the gate names it, then plants
the correct code and asserts it stays silent. An arm that only ever sees clean
input proves nothing: a checker widened until it catches nothing passes it
identically.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_icon_vocabulary as iv  # noqa: E402


# Icons the fake node_modules below "ships". Deliberately a SMALL set: the
# existence rule must be able to fail, or the arms testing it prove nothing.
INSTALLED = (
    "FileDocumentOutline ViewDashboardOutline ReceiptTextOutline CurrencyEur "
    "StoreOutline ViewGridOutline Cog CogOutline History Eye EyeOutline "
    "ClipboardTextClockOutline"
).split()


def _app(tmp: Path, menu, *, with_node_modules=True, registered=None, pages=None):
    """Build a minimal repo-shaped app tree and return its root."""
    (tmp / "src").mkdir(parents=True, exist_ok=True)
    (tmp / "src" / "manifest.json").write_text(
        json.dumps({"version": "0.1.0", "menu": menu, "pages": pages or []}),
        encoding="utf-8")

    # Register every icon the manifest uses unless the caller overrides it, so
    # the registry-completeness rule never contaminates an arm about concepts.
    if registered is None:
        registered = sorted({
            v for v in _icons_in(menu)
            if v and v[:1].isupper() and not v.startswith("icon-")
        })
    (tmp / "src" / "main.js").write_text(
        "import icons from './icons.js'\nregisterIcons(icons)\n", encoding="utf-8")
    (tmp / "src" / "icons.js").write_text(
        "".join(f"import {n} from 'vue-material-design-icons/{n}.vue'\n"
                for n in registered)
        + "export default { " + ", ".join(registered) + " }\n",
        encoding="utf-8")

    if with_node_modules:
        nm = tmp / "node_modules" / "vue-material-design-icons"
        nm.mkdir(parents=True, exist_ok=True)
        for n in INSTALLED:
            (nm / f"{n}.vue").write_text("", encoding="utf-8")
    return tmp


def _icons_in(node):
    if isinstance(node, dict):
        if node.get("icon"):
            yield node["icon"]
        for v in node.values():
            yield from _icons_in(v)
    elif isinstance(node, list):
        for i in node:
            yield from _icons_in(i)


def _run(root: Path):
    """(exit_code, stdout) for a full check of *root*."""
    buf = io.StringIO()
    argv = sys.argv
    sys.argv = ["check_icon_vocabulary.py", str(root)]
    try:
        with redirect_stdout(buf):
            rc = iv.main()
    finally:
        sys.argv = argv
    return rc, buf.getvalue()


class _TmpCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TierBIsReachable(_TmpCase):
    """The half of the gate that was unreachable code."""

    def test_a_tier_b_concept_with_the_wrong_glyph_warns(self):
        # `invoice` is a Tier B concept. Before the fix this produced NOTHING —
        # no warning, no failure — because no label could resolve to Tier B.
        root = _app(self.tmp, [
            {"id": "inv", "label": "Invoice", "icon": "FileDocumentOutline"}])
        rc, out = _run(root)
        self.assertIn("Tier B — SHOULD", out)
        self.assertIn('concept "invoice"', out)
        self.assertIn("ReceiptTextOutline", out)

    def test_a_tier_b_warning_does_not_fail_the_gate(self):
        # SHOULD, not MUST. Widening Tier B must not turn 140 concepts into
        # 140 new ways to block a PR — that is how a gate starts crying wolf.
        root = _app(self.tmp, [
            {"id": "inv", "label": "Invoice", "icon": "FileDocumentOutline"}])
        rc, _ = _run(root)
        self.assertEqual(rc, 0)

    def test_the_correct_tier_b_glyph_is_silent(self):
        # ANTI-WIDENING. The same label with the canonical icon must produce
        # nothing at all.
        root = _app(self.tmp, [
            {"id": "inv", "label": "Invoice", "icon": "ReceiptTextOutline"}])
        rc, out = _run(root)
        self.assertEqual(rc, 0)
        self.assertNotIn("Tier B", out)
        self.assertNotIn("FAIL", out)

    def test_every_vocabulary_concept_is_reachable_by_its_own_name(self):
        # The structural assertion behind all of the above: the label table is
        # DERIVED from the vocabulary, so adding a concept makes it
        # enforceable. Before the fix this was 10 of 153.
        vocab = iv._load_vocab()
        concepts = {**vocab["tierA"], **vocab["tierB"]}
        labels = iv._concept_labels(concepts)
        unreachable = sorted(c for c in concepts if c not in set(labels.values()))
        self.assertEqual(unreachable, [])
        self.assertGreater(len(vocab["tierB"]), 100)

    def test_a_tier_a_concept_still_fails(self):
        # No regression: Tier A stays a MUST.
        root = _app(self.tmp, [
            {"id": "d", "label": "Dashboard", "icon": "FileDocumentOutline"}])
        rc, out = _run(root)
        self.assertEqual(rc, 1)
        self.assertIn("Tier A — MUST", out)

    def test_a_newly_reachable_tier_a_concept_fails(self):
        # `admin` was in Tier A and had no label mapping, so it was as dead as
        # Tier B despite being a MUST.
        vocab = iv._load_vocab()
        self.assertIn("admin", vocab["tierA"])
        root = _app(self.tmp, [
            {"id": "a", "label": "Admin", "icon": "FileDocumentOutline"}])
        rc, out = _run(root)
        self.assertEqual(rc, 1)
        self.assertIn('concept "admin"', out)

    def test_a_dutch_synonym_still_resolves(self):
        # The synonym layer must survive being merged with the derived one.
        root = _app(self.tmp, [
            {"id": "s", "label": "Instellingen", "icon": "FileDocumentOutline"}])
        rc, out = _run(root)
        self.assertIn('concept "settings"', out)

    def test_a_domain_label_is_never_guessed_at(self):
        # ANTI-WIDENING, and the thing ADR-077 rule 5 actually forbids. An
        # app's own wording resolves to no concept and is left alone.
        root = _app(self.tmp, [
            {"id": "z", "label": "Zaakdossiers", "icon": "FileDocumentOutline"}])
        rc, out = _run(root)
        self.assertEqual(rc, 0)
        self.assertNotIn("concept", out)

    def test_a_finding_names_the_entry_id(self):
        # One manifest can carry the same label at several ids; without the id
        # the findings are byte-identical and name nothing to edit.
        root = _app(self.tmp, [
            {"id": "inv-a", "label": "Invoice", "icon": "FileDocumentOutline"},
            {"id": "inv-b", "label": "Invoice", "icon": "FileDocumentOutline"}])
        rc, out = _run(root)
        self.assertIn("id=inv-a", out)
        self.assertIn("id=inv-b", out)


class CaptionsAreNotRenderedIcons(_TmpCase):
    """The gate-60 / gate-62 divergence, decided against the renderer.

    `CnAppNav.vue` renders a caption as `<NcAppNavigationCaption :name=... />`
    — no `#icon` slot, no `:to`, no children loop — and its docblock says
    "Caption entries ignore `route`, `href`, `action`, `icon`, `count`,
    `children`, and `pinned`". The manifest schema agrees independently. So a
    caption's icon draws nothing and cannot be wrong; gate 62 used to fail it
    twice and has been aligned to this.
    """

    def test_a_caption_icon_is_not_judged_as_a_glyph(self):
        root = _app(self.tmp, [
            {"id": "cap", "type": "caption", "label": "Dashboard",
             "icon": "FileDocumentOutline"}])
        rc, out = _run(root)
        self.assertEqual(rc, 0)
        self.assertNotIn("Tier A", out)
        self.assertNotIn("FAIL", out)

    def test_a_caption_carrying_dead_keys_still_says_so(self):
        # The exemption must not be a SILENCE — it produces a sentence.
        root = _app(self.tmp, [
            {"id": "cap", "type": "caption", "label": "Dashboard",
             "icon": "FileDocumentOutline"}])
        rc, out = _run(root)
        self.assertIn("caption entry", out)
        self.assertIn("icon", out)
        self.assertTrue(out.lstrip().startswith("WARN"), out)

    def test_a_clean_caption_is_completely_silent(self):
        # ANTI-WIDENING: a caption with only the honoured keys says nothing.
        root = _app(self.tmp, [
            {"id": "cap", "type": "caption", "label": "Dashboard", "order": 1}])
        rc, out = _run(root)
        self.assertEqual(rc, 0)
        self.assertNotIn("caption entry", out)

    def test_the_identical_node_without_type_caption_still_fails(self):
        # The decisive pair. Same label, same icon; only `type` differs.
        root = _app(self.tmp, [
            {"id": "cap", "label": "Dashboard", "icon": "FileDocumentOutline"}])
        rc, out = _run(root)
        self.assertEqual(rc, 1)
        self.assertIn("Tier A — MUST", out)


class ToolingMissingIsNarrowedToWhatItActuallyBlocks(_TmpCase):
    """A missing npm install must not erase a verdict the gate already has."""

    def test_an_all_vocabulary_app_passes_with_no_node_modules(self):
        # Every icon here is a vocabulary icon, whose existence is asserted by
        # nextcloud-vue's own semanticIcons.spec.js. The library answers no
        # question this manifest asks, so the run is fully verified. This used
        # to report SKIPPED, which is how the gate "went unrun" in apps whose
        # manifests were clean.
        root = _app(self.tmp,
                    [{"id": "d", "label": "Dashboard",
                      "icon": "ViewDashboardOutline"}],
                    with_node_modules=False)
        rc, out = _run(root)
        self.assertEqual(rc, 0)
        self.assertNotIn("NOTE", out)

    def test_a_non_vocabulary_name_without_node_modules_is_still_unverifiable(self):
        # ANTI-WIDENING. The third state survives exactly where it is earned:
        # this name is not in the vocabulary, so only the library could confirm
        # it, and the library is absent. Neither a finding nor a pass.
        root = _app(self.tmp,
                    [{"id": "x", "label": "Widgets", "icon": "SomeInventedName"}],
                    with_node_modules=False)
        rc, out = _run(root)
        self.assertEqual(rc, iv.EXIT_TOOLING_MISSING)
        self.assertIn("SomeInventedName", out)

    def test_an_invented_name_with_node_modules_present_fails(self):
        # And with the library there, the same name is a hard failure.
        root = _app(self.tmp,
                    [{"id": "x", "label": "Widgets", "icon": "SomeInventedName"}])
        rc, out = _run(root)
        self.assertEqual(rc, 1)
        self.assertIn("does not exist in", out)


class RegressionGuards(_TmpCase):
    """Rules that existed before and must keep working."""

    def test_an_unbridged_legacy_css_icon_fails(self):
        root = _app(self.tmp, [
            {"id": "x", "label": "Widgets", "icon": "icon-not-a-real-bridge"}])
        rc, out = _run(root)
        self.assertEqual(rc, 1)
        self.assertIn("unbridged legacy icon", out)

    def test_an_unregistered_mdi_name_fails(self):
        root = _app(self.tmp,
                    [{"id": "x", "label": "Widgets", "icon": "Eye"}],
                    registered=[])
        rc, out = _run(root)
        self.assertEqual(rc, 1)
        self.assertIn("NOT registered", out)

    def test_a_lowercase_non_contentblock_name_fails(self):
        # The blanket lowercase skip is what hid shillinq's `calendar-sync`.
        root = _app(self.tmp, [
            {"id": "x", "label": "Widgets", "icon": "calendar-sync"}])
        rc, out = _run(root)
        self.assertEqual(rc, 1)
        self.assertIn("ContentBlocks", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
