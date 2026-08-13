#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_contract_coverage (gate-25). Run with:

    python3 scripts/lib/test_check_contract_coverage.py

WHY THIS FILE DID NOT EXIST UNTIL NOW, AND WHAT THAT COST
---------------------------------------------------------
gate-25 shipped with no suite of its own. Nothing asserted that it could
fail, so nothing noticed that **its coverage evidence was file text**.

gate-25 is written as gate-19's API-layer companion, and it inherited gate
19's original defect along with its shape: a comment saying you still owe the
test satisfied the gate that exists to collect the test. Measured on this
checker, one fixture, one variable each time:

    no tests at all                     FAIL — 1 new public endpoint
    + a *Test.php whose ONLY mention    PASS — 1 endpoint, all covered
      of the method is
      "// TODO: we still owe a contract
       test that calls
       $this->controller->destroy($id)
       ... Not written yet."

    no collection at all                FAIL — 1 new public endpoint
    + a .postman_collection.json with   PASS — 1 endpoint, all covered
      ZERO items whose description
      reads "NOTE: we do NOT yet cover
      /api/things — the DELETE
      endpoint is untested."

**Both greens were bought by a sentence admitting the debt.** The more honest
the note, the more coverage it fabricated — and an author who writes neither
note gets the red. That is the gate rewarding silence.

THE STRUCTURE OF THIS SUITE
---------------------------
Every closure arm is paired, in the same test, with the REAL artefact it must
not swallow — a genuine `->destroy(` call, a genuine collection request. A
mask that eats code rather than prose passes the closure arm and fails the
pair, which is the only way that mistake announces itself.

`test_positive_control_*` is first and is not decoration: it is the arm that
proves the rest are measuring a live gate. Every other assertion in this file
is worthless if that one ever goes green.
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_contract_coverage as ccc  # noqa: E402

ROUTES = """<?php
return ['routes' => [
    ['name' => 'thing#destroy', 'url' => '/api/things/{id}', 'verb' => 'DELETE'],
]];
"""

# `#[NoAdminRequired]` is required or the method is not a PUBLIC endpoint and
# the gate correctly ignores it. Leaving it out was the first rig error made
# while measuring this defect: the "positive control" printed PASS — "no new
# public endpoint" — and the false-negative arm printed PASS after it, so the
# two agreed and neither meant anything. A control that passes for the wrong
# reason is indistinguishable from a gate that works.
CONTROLLER = """<?php
namespace OCA\\Fx\\Controller;
class ThingController
{
    #[NoAdminRequired]
    public function destroy(int $id)
    {
        return 1;
    }
}
"""


class _App:
    """A repo-shaped fixture: routes + one public endpoint, nothing else."""

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.write("appinfo/routes.php", ROUTES)
        self.write("lib/Controller/ThingController.php", CONTROLLER)
        self._git("init", "-q")
        self._git("config", "user.email", "t@example.invalid")
        self._git("config", "user.name", "test")
        self.commit()

    def _git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.root), *args],
                       check=False, capture_output=True)

    def write(self, rel: str, body: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")

    def commit(self) -> None:
        self._git("add", "-A")
        self._git("commit", "-qm", "fixture")

    def verdict(self) -> tuple[int, str]:
        """(exit status, stdout) of a full-tree gate run over this fixture."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = ccc.run_gate(self.root)
        return rc, buf.getvalue()

    def destroy(self) -> None:
        subprocess.run(["rm", "-rf", str(self.root)], check=False)


class ContractCoverageEvidence(unittest.TestCase):
    def setUp(self) -> None:
        self.app = _App()
        self.addCleanup(self.app.destroy)

    # -- the control the rest of the file rests on --------------------------

    def test_positive_control_an_untested_public_endpoint_is_a_finding(self):
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_FAIL, out)
        self.assertIn("thing#destroy", out)

    # -- PHPUnit side: prose is not a test ---------------------------------

    def test_a_todo_naming_the_missing_test_is_not_the_test(self):
        self.app.write("tests/ThingTest.php", """<?php
class ThingTest extends \\PHPUnit\\Framework\\TestCase
{
    public function testSomethingElse(): void
    {
        // TODO: we still owe a contract test that calls
        // $this->controller->destroy($id) and asserts the 404 shape.
        // Not written yet.
        $this->assertTrue(true);
    }
}
""")
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_FAIL, out)

    def test_a_real_call_is_still_coverage(self):
        """The pair. A mask that ate code rather than comments passes the arm
        above and fails this one."""
        self.app.write("tests/ThingTest.php", """<?php
class ThingTest extends \\PHPUnit\\Framework\\TestCase
{
    public function testDestroy(): void
    {
        $controller = new \\OCA\\Fx\\Controller\\ThingController();
        $this->assertSame(1, $controller->destroy(7));
    }
}
""")
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_PASS, out)

    def test_the_method_name_inside_a_string_literal_is_not_a_call(self):
        """`->destroy(` is a call. It is never legitimately spelled inside a
        string, so a fixture payload quoting one is not evidence."""
        self.app.write("tests/ThingTest.php", """<?php
class ThingTest extends \\PHPUnit\\Framework\\TestCase
{
    public function testSomethingElse(): void
    {
        $note = 'the missing case is $controller->destroy($id)';
        $this->assertNotEmpty($note);
    }
}
""")
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_FAIL, out)

    # -- Newman side: a description is a comment in JSON syntax -------------

    def test_a_collection_description_is_not_a_request(self):
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx", "description": '
            '"NOTE: we do NOT yet cover /api/things - the DELETE endpoint is untested."},'
            ' "item": []}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_FAIL, out)

    def test_a_real_collection_request_is_still_coverage(self):
        """The pair for the Newman side — including the same misleading
        description, so the ONLY difference between this arm and the one above
        is that a request exists."""
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx", "description": '
            '"NOTE: we do NOT yet cover /api/things."},'
            ' "item": [{"name": "delete a thing", "request": {"method": "DELETE",'
            ' "url": {"raw": "{{base}}/api/things/7", "host": ["{{base}}"],'
            ' "path": ["api", "things", "7"]}}}]}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_PASS, out)

    def test_a_url_given_as_a_bare_string_is_still_a_request(self):
        """Postman v2.0 writes `url` as a string, v2.1 as an object. The
        extractor must not be a schema-version check wearing a coverage check's
        name."""
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx"}, "item": [{"name": "del",'
            ' "request": {"method": "DELETE", "url": "https://x/api/things/7"}}]}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_PASS, out)

    def test_an_unparseable_collection_falls_back_to_raw_text(self):
        """A malformed fixture must not be silently converted into findings.

        Inventing failures in repos this change was never measured against is
        the failure mode of a fix applied at fleet scale, so the honest
        behaviour for an unreadable input is the one that was there before."""
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"item": [ this is not json "/api/things"\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_PASS, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
