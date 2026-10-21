#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for gate-121's checker (check_register_auth_dialect.py), rule by rule.

  1. EACH DEAD KEY FAILS: x-openregister-rbac on a schema (the shillinq shape),
     x-rbac-role on a lifecycle transition, the singular x-openregister-validation
     on a schema and on a property.
  2. THE KEYS OPENREGISTER READS PASS: authorization, x-openregister-validations.
  3. A PROPERTY NAMED LIKE A DEAD KEY IS NOT A FINDING.
  4. EVERY WATCHED PATH IS READ: a top-level register, register.d, packages/**,
     and a mock; a JSON file elsewhere under lib/Settings is not.
  5. THE CENSUS MERGES LIKE OpenRegister: an authorization block a register.d
     fragment adds to a base schema counts; an empty block does not; a mock's
     schemas are not counted; a package's are, on their own.
  6. THE CENSUS IS REPORT-ONLY until --require-authorization.
  7. --judge-from NARROWS THE FINDINGS, NOT THE CENSUS.
  8. NO SCHEMA ANYWHERE IS NOT APPLICABLE (exit 4), never PASS.
  9. A DOCUMENT THAT IS NOT JSON IS exit 2, never a pass and never a finding.

Run: python3 scripts/lib/test_check_register_auth_dialect.py
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_register_auth_dialect as rad  # noqa: E402

OPEN = {"type": "object", "properties": {"name": {"type": "string"}}}
CLOSED = dict(OPEN, authorization={"read": ["staff"], "create": ["staff"]})


def document(schemas, mock=False):
    doc = {"openapi": "3.0.0", "info": {"title": "Fixture", "version": "1.0.0"},
           "components": {"schemas": schemas}}
    if mock:
        doc["x-openregister"] = {"type": "mock"}
    return doc


class Case(unittest.TestCase):
    def setUp(self):
        self.app = tempfile.mkdtemp(prefix="gate121-")
        self.addCleanup(shutil.rmtree, self.app)

    def write(self, path, body):
        full = os.path.join(self.app, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(body if isinstance(body, str) else json.dumps(body))

    def run_checker(self, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = rad.main([self.app, *extra])
        return rc, out.getvalue()


class DeadKeys(Case):
    def test_rbac_on_a_schema_fails(self):
        self.write("lib/Settings/fixture_register.json",
                   document({"Invoice": dict(OPEN, **{"x-openregister-rbac": {"read": ["staff"]}})}))
        rc, out = self.run_checker()
        self.assertEqual(rc, 1)
        self.assertIn("components.schemas.Invoice.x-openregister-rbac", out)
        self.assertIn("FAIL: 1 finding(s) in 1 schema(s)", out)

    def test_rbac_role_on_a_transition_fails(self):
        schema = dict(CLOSED, **{"x-openregister-lifecycle": {"transitions": {
            "approve": {"from": "draft", "to": "approved", "x-rbac-role": "controller"}}}})
        self.write("lib/Settings/register.d/10-runs.json", document({"PaymentRun": schema}))
        rc, out = self.run_checker()
        self.assertEqual(rc, 1)
        self.assertIn("x-openregister-lifecycle.transitions.approve.x-rbac-role", out)

    def test_singular_validation_fails_on_schema_and_property(self):
        prop = {"type": "string", "x-openregister-validation": {"rules": []}}
        schema = dict(CLOSED, properties={"iban": prop}, **{"x-openregister-validation": {"rules": []}})
        self.write("lib/Settings/fixture_register.json", document({"Account": schema}))
        rc, out = self.run_checker()
        self.assertEqual(rc, 1)
        self.assertIn("components.schemas.Account.x-openregister-validation:", out)
        self.assertIn("components.schemas.Account.properties.iban.x-openregister-validation:", out)
        self.assertIn("FAIL: 2 finding(s) in 1 schema(s)", out)

    def test_the_read_keys_pass(self):
        schema = dict(CLOSED, **{"x-openregister-validations": [{"rule": "x"}]})
        self.write("lib/Settings/fixture_register.json", document({"Account": schema}))
        rc, out = self.run_checker()
        self.assertEqual(rc, 0, out)
        self.assertIn("checked 1 document(s), 1 schema(s), 0 finding(s)", out)

    def test_a_property_named_like_a_dead_key_is_not_a_finding(self):
        schema = dict(CLOSED, properties={"x-rbac-role": {"type": "string"}})
        self.write("lib/Settings/fixture_register.json", document({"Role": schema}))
        rc, out = self.run_checker()
        self.assertEqual(rc, 0, out)


class Paths(Case):
    def test_every_watched_path_is_read(self):
        bad = {"S": dict(OPEN, **{"x-openregister-rbac": {}})}
        for path in ("lib/Settings/fixture_register.json",
                     "lib/Settings/register.d/20-more.json",
                     "lib/Settings/packages/vth/schemas/case.json",
                     "lib/Settings/fixture_mock_register.json"):
            self.write(path, document(bad, mock="mock" in path))
        rc, out = self.run_checker()
        self.assertEqual(rc, 1)
        self.assertIn("FAIL: 4 finding(s)", out)

    def test_other_json_under_settings_is_not_read(self):
        self.write("lib/Settings/fixture_register.json", document({"A": CLOSED}))
        self.write("lib/Settings/templates/a.json", document({"S": dict(OPEN, **{"x-openregister-rbac": {}})}))
        rc, out = self.run_checker()
        self.assertEqual(rc, 0, out)


class Census(Case):
    def test_a_fragment_closing_a_base_schema_counts(self):
        self.write("lib/Settings/fixture_register.json", document({"A": OPEN, "B": OPEN}))
        self.write("lib/Settings/register.d/50-close.json",
                   {"components": {"schemas": {"A": {"authorization": {"read": ["staff"]}}}}})
        rc, out = self.run_checker()
        self.assertEqual(rc, 0, out)
        self.assertIn("authorization coverage: 1 of 2 schema(s) declare an authorization block, 1 do not (report-only)", out)
        self.assertIn("    no authorization: B", out)

    def test_an_empty_block_does_not_count(self):
        self.write("lib/Settings/fixture_register.json", document({"A": dict(OPEN, authorization={})}))
        _rc, out = self.run_checker()
        self.assertIn("coverage: 0 of 1", out)

    def test_mocks_are_not_counted_and_packages_are(self):
        self.write("lib/Settings/fixture_register.json", document({"A": CLOSED}))
        self.write("lib/Settings/fixture_mock_register.json", document({"M": OPEN}, mock=True))
        self.write("lib/Settings/packages/p/register.json", document({"P": OPEN}))
        _rc, out = self.run_checker()
        self.assertIn("coverage: 1 of 2", out)
        self.assertIn("no authorization: P (lib/Settings/packages/p/register.json)", out)

    def test_require_authorization_fails_an_open_schema(self):
        self.write("lib/Settings/fixture_register.json", document({"A": OPEN, "B": CLOSED}))
        rc, out = self.run_checker("--require-authorization")
        self.assertEqual(rc, 1)
        self.assertIn("FAIL: 1 finding(s) in 1 schema(s)", out)
        self.assertNotIn("(report-only)", out)


class Scope(Case):
    def test_judge_from_narrows_findings_not_the_census(self):
        bad = document({"S": dict(OPEN, **{"x-openregister-rbac": {}})})
        self.write("lib/Settings/fixture_register.json", bad)
        self.write("lib/Settings/register.d/10-new.json", document({"N": CLOSED}))
        listing = os.path.join(self.app, "judge.txt")
        with open(listing, "w", encoding="utf-8") as fh:
            fh.write("lib/Settings/register.d/10-new.json\n")
        rc, out = self.run_checker("--judge-from", listing)
        self.assertEqual(rc, 0, out)
        self.assertIn("coverage: 1 of 2", out)

    def test_no_schema_is_not_applicable(self):
        self.write("lib/Settings/fixture_register.json",
                   {"openapi": "3.0.0", "components": {"registers": {"r": {"slug": "r"}}}})
        rc, out = self.run_checker()
        self.assertEqual(rc, 4)
        self.assertIn("NOT APPLICABLE", out)

    def test_invalid_json_cannot_run(self):
        self.write("lib/Settings/fixture_register.json", "{not json")
        rc, out = self.run_checker()
        self.assertEqual(rc, 2)
        self.assertNotIn("FAIL:", out)
        self.assertNotIn("checked", out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
