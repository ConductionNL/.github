#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_store_and_settings_surface (gates 62 / 63). Run with:

    python3 scripts/lib/test_check_store_and_settings_surface.py

WHY THIS SUITE EXISTS
---------------------
Gate-62 had no tests, and half of it ignored diff scoping. Its manifest checks
honoured ADR-020; its `lib/**.php` store-discovery scan walked the whole tree
unconditionally. The combination is the worst of both: the gate only RUNS when
a manifest changed, and then judges code the PR never touched.

Measured on pipelinq: one pre-existing violation blocked EVERY
manifest-touching PR in that repo, permanently, with a finding naming a file
outside the diff. There was no action the author could take that was about
their own change — the definition of an unclosable gate.

Both ways, in the same class: an untouched violation must not block a
manifest-only PR, and the same violation must still fire the moment the PR
touches that file, and on any full-tree run.
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
import check_store_and_settings_surface as css  # noqa: E402

# Verbatim shape of the pipelinq violation: an app-local re-implementation of
# OpenRegister store discovery (ADR-080 D2/D3).
LEGACY_STORE_PHP = """<?php
namespace OCA\\Pipelinq\\Service;

class LegacyStoreService
{
    public function fetch(IClientService $client)
    {
        $url = '/apps/openregister/api/objects/' . $this->register;
        return $client->newClient()->get($url);
    }
}
"""

CLEAN_MANIFEST = {
    "id": "app",
    "menu": [{"label": "Store", "icon": "StoreOutline", "route": "store"}],
    "pages": [{"id": "store", "config": {"cardComponent": "StoreCard"}}],
}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args],
                   check=False, capture_output=True)


class LibScanIsDiffScoped(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "src").mkdir(parents=True)
        (self.root / "lib" / "Service").mkdir(parents=True)
        (self.root / "src" / "manifest.json").write_text(
            json.dumps(CLEAN_MANIFEST), encoding="utf-8")
        (self.root / "lib" / "Service" / "LegacyStoreService.php").write_text(
            LEGACY_STORE_PHP, encoding="utf-8")
        _git(self.root, "init", "-q")
        _git(self.root, "config", "user.email", "t@example.invalid")
        _git(self.root, "config", "user.name", "test")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", "base: the violation is already here")
        self.base = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            capture_output=True, text=True).stdout.strip()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _run(self, base: str | None) -> tuple[int, str]:
        argv = [str(self.root), "--gate", "store"]
        if base:
            argv += ["--base", base]
        buf = io.StringIO()
        old = sys.argv
        sys.argv = ["check_store_and_settings_surface.py", *argv]
        try:
            with redirect_stdout(buf):
                rc = css.main()
        finally:
            sys.argv = old
        return rc, buf.getvalue()

    def _touch_manifest_only(self):
        m = json.loads((self.root / "src" / "manifest.json").read_text())
        m["menu"][0]["label"] = "Store"
        m["pages"][0]["config"]["cardComponent"] = "StoreCardV2"
        (self.root / "src" / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", "manifest-only change")

    def test_an_untouched_violation_does_not_block_a_manifest_only_pr(self):
        self._touch_manifest_only()
        rc, out = self._run(self.base)
        self.assertNotIn("LegacyStoreService", out)
        self.assertEqual(rc, 0)

    def test_the_same_violation_fires_when_the_pr_touches_that_file(self):
        # The pairing. Identical repository, identical violation — only the
        # diff differs, which is the whole property ADR-020 scoping asserts.
        self._touch_manifest_only()
        php = self.root / "lib" / "Service" / "LegacyStoreService.php"
        php.write_text(php.read_text() + "\n// touched by this PR\n", encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", "touch the service too")
        rc, out = self._run(self.base)
        self.assertIn("LegacyStoreService", out)
        self.assertEqual(rc, 1)

    def test_an_unscoped_full_tree_run_still_reports_inherited_debt(self):
        # Scoping hides the finding from a PR that did not cause it. It must
        # not delete it: a full-tree run is where inherited debt is counted.
        rc, out = self._run(None)
        self.assertIn("LegacyStoreService", out)
        self.assertEqual(rc, 1)

    def test_manifest_findings_are_unaffected_by_the_scoping_change(self):
        m = json.loads((self.root / "src" / "manifest.json").read_text())
        m["menu"][0]["icon"] = "ShoppingOutline"   # wrong glyph for STORE
        (self.root / "src" / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", "wrong store icon")
        rc, out = self._run(self.base)
        self.assertIn("ShoppingOutline", out)
        self.assertEqual(rc, 1)


class GateIsNotBlind(unittest.TestCase):
    """If `check_store` ever stops producing findings entirely, the scoping
    assertions above still pass. This asserts the floor directly."""

    def test_check_store_reports_a_bad_icon(self):
        root = Path(tempfile.mkdtemp())
        try:
            findings: list[str] = []
            bad = dict(CLEAN_MANIFEST)
            bad["menu"] = [{"label": "Store", "icon": "ShoppingOutline", "route": "store"}]
            css.check_store(root, [(root / "src" / "manifest.json", bad)], findings)
            self.assertTrue(any("ShoppingOutline" in f for f in findings))
        finally:
            shutil.rmtree(root, ignore_errors=True)


class CaptionsAreNotMenuEntriesForThisGate(unittest.TestCase):
    """The gate-60 / gate-62 divergence, and the decision that resolved it.

    Until 2026-08-12 these two gates disagreed about one node, in the same
    package: gate 60 exempted a `type: "caption"` entry, and gate 62 failed it
    TWICE. Reproduced on a fixture carrying
    `{"type":"caption","label":"Store","icon":"ViewGridOutline"}` —
    gate-60 → 0 findings, gate-62 → 2 FAILs.

    Decided against the RENDERER, not by aligning whichever was easier to
    change. `CnAppNav.vue` renders a caption as
    `<NcAppNavigationCaption :name=... :data-testid=... />` — no `#icon` slot,
    no `:to`, no children loop — and its docblock states "Caption entries
    ignore `route`, `href`, `action`, `icon`, `count`, `children`, and
    `pinned`". The manifest schema says the same independently. Every rule in
    `check_store` is a claim about a rendered icon or a resolved route, and a
    caption has neither, so gate 62 was emitting unclosable findings about
    dead metadata. Gate 62 was aligned to gate 60; gate 60 now WARNs about the
    dead keys so the information is not merely dropped.
    """

    def _findings(self, entry, gate="store"):
        root = Path(tempfile.mkdtemp())
        try:
            data = {"id": "app", "menu": [entry], "pages": []}
            findings: list[str] = []
            fn = css.check_store if gate == "store" else css.check_settings
            fn(root, [(root / "src" / "manifest.json", data)], findings)
            return findings
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_caption_claiming_the_store_concept_is_not_failed(self):
        findings = self._findings({
            "id": "cap", "type": "caption", "label": "Store",
            "icon": "ViewGridOutline"})
        self.assertEqual(findings, [])

    def test_the_identical_node_without_type_caption_still_fails_twice(self):
        # THE DECISIVE PAIR. Same label, same icon; only `type` differs. If
        # this arm ever goes green the exemption has become a hole.
        findings = self._findings({
            "id": "cap", "label": "Store", "icon": "ViewGridOutline"})
        self.assertEqual(len(findings), 2, findings)
        self.assertTrue(all(f.startswith("FAIL") for f in findings))

    def test_a_child_of_a_caption_is_not_judged_either(self):
        # The renderer does not walk a caption's children, so nothing under it
        # is drawn. gate 60 skips the subtree for the same reason.
        findings = self._findings({
            "id": "cap", "type": "caption", "label": "Section",
            "children": [{"id": "s", "label": "Store", "icon": "ViewGridOutline"}]})
        self.assertEqual(findings, [])

    def test_a_non_caption_parent_still_has_its_children_judged(self):
        # ANTI-WIDENING for the arm above: the subtree skip must be caused by
        # `type: "caption"` and by nothing else.
        findings = self._findings({
            "id": "grp", "label": "Section",
            "children": [{"id": "s", "label": "Store", "icon": "ViewGridOutline"}]})
        self.assertEqual(len(findings), 2, findings)

    def test_gate_63_still_walks_captions_because_labels_ARE_rendered(self):
        # SCOPE OF THE DECISION. It covers icon and route rules only. A
        # caption's LABEL is honoured by the renderer, so ADR-079 D4 — which is
        # a rule about the label — must keep applying to one.
        findings = self._findings(
            {"id": "cap", "type": "caption", "label": "Settings",
             "section": "settings"},
            gate="settings")
        self.assertTrue(any("ADR-079 D4" in f for f in findings), findings)


if __name__ == "__main__":
    unittest.main(verbosity=2)
