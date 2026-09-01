#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_cross_app_schema_slug (gate 106). Run with:

    python3 scripts/lib/test_check_cross_app_schema_slug.py

WHY THIS SUITE EXISTS
---------------------
This gate answers a CROSS-app question from a SINGLE-app checkout, which it can
only do through a recorded baseline. That makes two failure modes possible that
no amount of running it against real repositories would reveal:

  1. It goes quiet. A gate that catches nothing passes every repository, and a
     green run then means "no cross-app claim" when it actually means "the
     checker stopped working". Every arm below plants a real claim and asserts
     the gate names it.

  2. It goes loud on legitimate input. A register.d fragment addresses an
     existing schema by its dict KEY and carries no `slug`; larpinq ships one
     that adds `configuration` to the schema keyed `skill`, whose slug is
     `larping_skill`. Reading that key as a claim invents a collision out of a
     fragment that declares nothing. That exact bug was in the first draft of
     the baseline generator, and it reported larpinq as still owning `skill`
     three days after the rename shipped.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "check_cross_app_schema_slug.py")


def _contract(tmp, owners):
    path = os.path.join(tmp, "contract.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"version": 1, "apps_scanned": [], "owners": owners}, handle)
    return path


def _app(tmp, app_id, descriptors):
    """Build a minimal app tree. `descriptors` is {filename: document}."""
    root = os.path.join(tmp, "app")
    os.makedirs(os.path.join(root, "appinfo"), exist_ok=True)
    os.makedirs(os.path.join(root, "lib", "Settings", "register.d"), exist_ok=True)
    with open(os.path.join(root, "appinfo", "info.xml"), "w", encoding="utf-8") as handle:
        handle.write(f'<?xml version="1.0"?>\n<info>\n  <id>{app_id}</id>\n</info>\n')
    for name, doc in descriptors.items():
        with open(os.path.join(root, "lib", "Settings", name), "w", encoding="utf-8") as handle:
            json.dump(doc, handle)
    return root


def _doc(app_id, schemas, reg_type="application"):
    return {
        "openapi": "3.0.0",
        "info": {"title": "t", "version": "1.0.0"},
        "x-openregister": {"type": reg_type, "app": app_id},
        "components": {"schemas": schemas},
    }


def _run(root, contract, *extra):
    proc = subprocess.run(
        [sys.executable, CHECKER, root, "--contract", contract, *extra],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


class CrossAppSchemaSlugTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_a_new_claim_on_another_apps_slug_fails(self):
        contract = _contract(self.tmp, {"product": ["pipelinq"]})
        root = _app(self.tmp, "keepiq", {"r.json": _doc("keepiq", {
            "product": {"slug": "product", "title": "Product", "properties": {"n": {}}},
        })})
        rc, out = _run(root, contract)
        self.assertEqual(rc, 1, out)
        self.assertIn("'product'", out)
        self.assertIn("pipelinq", out)

    def test_the_owning_app_keeps_its_own_slug(self):
        contract = _contract(self.tmp, {"product": ["pipelinq"]})
        root = _app(self.tmp, "pipelinq", {"r.json": _doc("pipelinq", {
            "product": {"slug": "product", "title": "Product", "properties": {"n": {}}},
        })})
        rc, out = _run(root, contract)
        self.assertEqual(rc, 0, out)

    def test_an_existing_shared_slug_stays_green_for_every_listed_app(self):
        """Reddening state that already exists teaches people to ignore a gate."""
        contract = _contract(self.tmp, {"task": ["dossiq", "pipelinq", "planninq"]})
        for app in ("dossiq", "pipelinq", "planninq"):
            shutil.rmtree(os.path.join(self.tmp, "app"), ignore_errors=True)
            root = _app(self.tmp, app, {"r.json": _doc(app, {
                "task": {"slug": "task", "title": "Task", "properties": {"n": {}}},
            })})
            rc, out = _run(root, contract)
            self.assertEqual(rc, 0, f"{app}: {out}")

    def test_a_fragment_that_only_extends_by_key_is_not_a_claim(self):
        """The bug that reported larpinq as still owning `skill` after the rename."""
        contract = _contract(self.tmp, {"skill": ["pipelinq"]})
        root = _app(self.tmp, "larpinq", {"r.json": _doc("larpinq", {
            "skill": {"configuration": {"x-openregister-mcp": {}}},
        })})
        rc, out = _run(root, contract)
        self.assertEqual(rc, 0, out)

    def test_a_slug_nobody_owns_is_free(self):
        contract = _contract(self.tmp, {"product": ["pipelinq"]})
        root = _app(self.tmp, "keepiq", {"r.json": _doc("keepiq", {
            "vaultEntry": {"slug": "vaultEntry", "title": "Vault entry", "properties": {"n": {}}},
        })})
        rc, out = _run(root, contract)
        self.assertEqual(rc, 0, out)

    def test_slug_matching_is_case_insensitive(self):
        """`Application` and `application` are one row to LOWER(slug)."""
        contract = _contract(self.tmp, {"application": ["buildiq"]})
        root = _app(self.tmp, "humaniq", {"r.json": _doc("humaniq", {
            "Application": {"slug": "Application", "title": "Application", "properties": {"n": {}}},
        })})
        rc, out = _run(root, contract)
        self.assertEqual(rc, 1, out)

    def test_a_mock_register_is_not_a_claim(self):
        contract = _contract(self.tmp, {"product": ["pipelinq"]})
        root = _app(self.tmp, "keepiq", {"r.json": _doc("keepiq", {
            "product": {"slug": "product", "title": "Product", "properties": {"n": {}}},
        }, reg_type="mock")})
        rc, out = _run(root, contract)
        self.assertEqual(rc, 0, out)

    def test_the_declaring_app_wins_over_the_directory(self):
        """A descriptor shipped inside one app may declare another app's id."""
        contract = _contract(self.tmp, {"workflow": ["n8n"]})
        root = _app(self.tmp, "openregister", {"r.json": _doc("n8n", {
            "workflow": {"slug": "workflow", "title": "Workflow", "properties": {"n": {}}},
        })})
        rc, out = _run(root, contract)
        self.assertEqual(rc, 0, out)

    def test_diff_scoping_restricts_to_changed_descriptors(self):
        contract = _contract(self.tmp, {"product": ["pipelinq"]})
        root = _app(self.tmp, "keepiq", {"r.json": _doc("keepiq", {
            "product": {"slug": "product", "title": "Product", "properties": {"n": {}}},
        })})
        rc, out = _run(root, contract, "--changed-file", "lib/Settings/other.json")
        self.assertEqual(rc, 0, out)
        rc, out = _run(root, contract, "--changed-file", "lib/Settings/r.json")
        self.assertEqual(rc, 1, out)

    def test_an_app_without_an_id_is_reported_not_crashed(self):
        contract = _contract(self.tmp, {"product": ["pipelinq"]})
        root = os.path.join(self.tmp, "app")
        os.makedirs(os.path.join(root, "lib", "Settings"), exist_ok=True)
        rc, out = _run(root, contract)
        self.assertEqual(rc, 0, out)
        self.assertIn("checked 0 descriptor(s)", out)

    def test_an_unreadable_contract_is_a_wiring_failure_not_a_pass(self):
        """Exit 2, so the runner reports SKIP-wiring rather than counting a pass."""
        root = _app(self.tmp, "keepiq", {"r.json": _doc("keepiq", {})})
        rc, out = _run(root, os.path.join(self.tmp, "absent.json"))
        self.assertEqual(rc, 2, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
