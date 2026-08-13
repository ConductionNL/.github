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
        behaviour for an unreadable input is the one that was there before.

        ⚠️ The blob below said `/api/things` until #430. That was never part
        of this test's claim — it was the LIST url standing in for a by-id
        route, which only worked while a trailing placeholder was dropped from
        the pattern. It now writes the url the route actually has, so the
        arm tests the fallback rather than the leniency."""
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"item": [ this is not json "/api/things/7"\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_PASS, out)


# ===========================================================================
# #430 — THE THREE WAYS AN ENDPOINT COULD NOT BE COVERED AT ALL
# ===========================================================================
#
# Measured 2026-08-13 across the eighteen core apps, package `fa555a2` vs
# `a316aa5` on identical trees: gate-25 gained 41 findings, nine apps went
# PASS -> FAIL, and 25 of the 41 could not be closed by any correct app
# change. Three independent causes, one arm each below. Each arm FAILS on
# `a316aa5` and passes here; each is paired with the control that stops the
# repair from becoming a relaxation.
class ContractCoverageClosability(unittest.TestCase):
    def setUp(self) -> None:
        self.app = _App()
        self.addCleanup(self.app.destroy)

    # -- 1. a medial placeholder made the url arm unsatisfiable -------------

    def test_a_medial_placeholder_does_not_make_the_route_unmatchable(self):
        """`_url_signature` deleted `{id}` and joined the survivors, so
        `/api/things/{id}/versions` became `api/things/versions` — a string no
        correct collection url can contain. 16 endpoints across the fleet were
        reported uncovered while a request for exactly that route existed;
        docudesk `api/templates/{id}/versions` is the shortest example."""
        self.app.write("appinfo/routes.php", """<?php
return ['routes' => [
    ['name' => 'thing#versions', 'url' => '/api/things/{id}/versions', 'verb' => 'GET'],
]];
""")
        self.app.write("lib/Controller/ThingController.php", """<?php
namespace OCA\\Fx\\Controller;
class ThingController
{
    #[NoAdminRequired]
    public function versions(int $id)
    {
        return 1;
    }
}
""")
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx"}, "item": [{"name": "list the versions",'
            ' "request": {"method": "GET", "url": {"raw":'
            ' "{{baseUrl}}/index.php/apps/fx/api/things/{{thingId}}/versions"}}}]}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_PASS, out)

    def test_a_sibling_operation_on_the_same_id_is_not_the_same_endpoint(self):
        """The control on the arm above, and the reason the repair is a regex
        rather than "truncate at the first placeholder".

        Truncating `/api/things/{id}/confirm` to `/api/things` would match the
        collection below — and would equally match `cancel`, `park` and
        `settle`, i.e. one request covering every operation on the id, in a
        gate whose whole subject is per-endpoint coverage. pipelinq has
        exactly that shape with five POS operations. `confirm` is covered
        here; `cancel` must still be reported."""
        self.app.write("appinfo/routes.php", """<?php
return ['routes' => [
    ['name' => 'thing#confirm', 'url' => '/api/things/{id}/confirm', 'verb' => 'POST'],
    ['name' => 'thing#cancel',  'url' => '/api/things/{id}/cancel',  'verb' => 'POST'],
]];
""")
        self.app.write("lib/Controller/ThingController.php", """<?php
namespace OCA\\Fx\\Controller;
class ThingController
{
    #[NoAdminRequired]
    public function confirm(int $id)
    {
        return 1;
    }

    #[NoAdminRequired]
    public function cancel(int $id)
    {
        return 1;
    }
}
""")
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx"}, "item": [{"name": "post it",'
            ' "request": {"method": "POST", "url": {"raw":'
            ' "{{baseUrl}}/api/things/{{thingId}}/confirm"}}}]}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_FAIL, out)
        self.assertIn("thing#cancel", out)
        self.assertNotIn("thing#confirm", out)

    # -- 2. the request-name arm was matching a syntax that was gone --------

    def test_a_request_named_after_the_controller_method_is_coverage(self):
        """`is_covered` matched `"name"\\s*:\\s*"…"` — JSON key syntax — against
        a haystack `_newman_paths` had rebuilt out of extracted VALUES. The arm
        matched nothing a collection declares.

        36 of the fleet's 41 new findings had been carried by this arm and by
        nothing else. The collection here sends to an unrelated url, so the
        name is the ONLY thing that can answer."""
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx"}, "item": [{"name": "destroy a thing",'
            ' "request": {"method": "DELETE", "url": {"raw":'
            ' "{{base}}/api/unrelated/7"}}}]}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_PASS, out)

    def test_the_method_name_in_a_url_is_not_a_request_name(self):
        """The control on the arm above. The docstring on `_newman_paths` says
        the discriminator is WHICH string, not whether it is one — so the tag
        has to be load-bearing. Here the word `destroy` appears in a url and in
        a payload, and in no request name; neither url matches the route."""
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx"}, "item": [{"name": "cleanup",'
            ' "request": {"method": "POST", "url": {"raw":'
            ' "{{base}}/api/jobs/destroy"}, "body": {"mode": "raw",'
            ' "raw": "{\\"name\\": \\"destroy\\"}"}}}]}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_FAIL, out)
        self.assertIn("thing#destroy", out)

    # -- 3. a nested array in the route entry deleted the url --------------

    def test_a_route_entry_with_a_nested_requirements_array_keeps_its_url(self):
        """`_ROUTE_ENTRY_RE` matched `\\[[^\\[\\]]*?\\]` — a bracket pair with no
        brackets inside — so every route declaring `'requirements' => [...]`
        fell through to the name-only sweep and was recorded with an EMPTY
        url. 9 endpoints across the fleet reached `is_covered` that way, and an
        empty url is an arm nothing can satisfy. launchpad's `page#deepLink`
        is the shape; the bracket characters inside the requirement regex are
        what a raw bracket walk miscounts."""
        self.app.write("appinfo/routes.php", """<?php
return ['routes' => [
    ['name' => 'thing#destroy',
     'url' => '/api/things/{id}/purge', 'verb' => 'DELETE',
     'requirements' => ['id' => '[A-Za-z0-9\\-]+']],
]];
""")
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx"}, "item": [{"name": "clean up",'
            ' "request": {"method": "DELETE", "url": {"raw":'
            ' "{{base}}/api/things/{{thingId}}/purge"}}}]}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_PASS, out)

    def test_the_url_is_read_from_the_entry_and_not_from_a_nested_array(self):
        """The control on the arm above. A `'requirements'` key named `url`
        constrains a `/{url}` parameter; it is not the route's path. If the
        recovery read it, this endpoint would be 'covered' by a request to
        `/api/other`."""
        self.app.write("appinfo/routes.php", """<?php
return ['routes' => [
    ['name' => 'thing#destroy',
     'url' => '/api/things/{url}/purge', 'verb' => 'DELETE',
     'requirements' => ['url' => '/api/other']],
]];
""")
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx"}, "item": [{"name": "elsewhere",'
            ' "request": {"method": "GET", "url": {"raw":'
            ' "{{base}}/api/other"}}}]}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_FAIL, out)
        self.assertIn("thing#destroy", out)

    # -- the leniency that is preserved on purpose, pinned so it is visible -

    def test_a_trailing_placeholder_is_a_required_segment(self):
        """A TIGHTENING, pinned so it is a decision rather than a side effect.

        `_url_signature` dropped trailing placeholders along with medial ones,
        so a request that only LISTS things counted as evidence for the by-id
        route. Keeping that leniency was measured to be unshippable next to
        the `parse_routes` repair: eight openregister endpoints that had never
        had a parsed url acquired one, and `/registers/{id}` was then answered
        by a request to `/api/registers`. A parser repair that converts
        findings into silence is the wrong trade whichever way the count
        moves.

        The fleet cost of this arm is measured, not assumed: across the
        eighteen core apps it exposes exactly one endpoint —
        zaakafhandelapp `users#me` (`GET /me`), which has no request, no
        matching request name and no PHPUnit call. It was previously
        'covered' because the two letters `me` occur somewhere in the
        collection."""
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx"}, "item": [{"name": "list",'
            ' "request": {"method": "GET", "url": {"raw":'
            ' "{{base}}/api/things"}}}]}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_FAIL, out)
        self.assertIn("thing#destroy", out)

    def test_a_partly_literal_segment_keeps_its_literal(self):
        """`{` does not make the whole segment wild. OpenRegister writes
        `/api/objects/{uuid}/_{type}`, where the `_` is what separates a link
        sub-resource from an object's schema id — wildcarding the segment lets
        a plain object read answer a link write."""
        self.app.write("appinfo/routes.php", """<?php
return ['routes' => [
    ['name' => 'thing#destroy', 'url' => '/api/things/{uuid}/_{type}', 'verb' => 'DELETE'],
]];
""")
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx"}, "item": [{"name": "read",'
            ' "request": {"method": "GET", "url": {"raw":'
            ' "{{base}}/api/things/{{uuid}}/{{schema}}"}}}]}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_FAIL, out)
        self.assertIn("thing#destroy", out)

    def test_an_api_request_does_not_cover_the_spa_page_route_of_the_same_name(self):
        """A route path starts at the APP ROOT, so `/registers/{id}` and
        `/api/registers/{id}` are different endpoints — and with a free left
        edge the second contains the first and answers for it.

        This is the measured cost of the `parse_routes` repair, not a
        hypothetical: openregister's `ui#registersDetails`, `ui#schemasDetails`,
        `ui#objectDetail` and `ui#applicationDetails` acquired a parsed url for
        the first time and were immediately 'covered' by `…/api/registers/…`
        and friends. Four real findings turned into silence by a repair whose
        subject is findings that could not be closed."""
        self.app.write("appinfo/info.xml",
                       "<?xml version='1.0'?><info><id>fx</id></info>\n")
        self.app.write("appinfo/routes.php", """<?php
return ['routes' => [
    ['name' => 'ui#thingDetail', 'url' => '/things/{id}', 'verb' => 'GET'],
]];
""")
        self.app.write("lib/Controller/UiController.php", """<?php
namespace OCA\\Fx\\Controller;
class UiController
{
    #[NoAdminRequired]
    public function thingDetail(int $id)
    {
        return 1;
    }
}
""")
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx"}, "item": [{"name": "read",'
            ' "request": {"method": "GET", "url": {"raw":'
            ' "{{base}}/index.php/apps/fx/api/things/{{thingId}}"}}}]}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_FAIL, out)
        self.assertIn("ui#thingDetail", out)

    def test_the_app_base_is_an_anchor_and_not_a_wall(self):
        """The pair. The anchor must still let the app's OWN routes match, in
        every spelling the fleet's collections use: after `/apps/<id>`, after a
        `}` (`{{baseUrl}}/{{app}}/api/…`, zaakafhandelapp), and at the start of
        a bare path."""
        self.app.write("appinfo/info.xml",
                       "<?xml version='1.0'?><info><id>fx</id></info>\n")
        for raw in (
            "{{base}}/index.php/apps/fx/api/things/7",
            "{{base}}/{{app}}/api/things/7",
            "/api/things/7",
            "https://nc.example/index.php/apps/fx/api/things/7",
        ):
            with self.subTest(raw=raw):
                self.app.write(
                    "tests/integration/things.postman_collection.json",
                    '{"info": {"name": "Fx"}, "item": [{"name": "x",'
                    ' "request": {"method": "DELETE", "url": {"raw": "'
                    + raw + '"}}}]}\n',
                )
                self.app.commit()
                rc, out = self.app.verdict()
                self.assertEqual(rc, ccc.EXIT_PASS, out)

    def test_a_second_registration_of_the_same_name_is_also_the_endpoint(self):
        """`parse_routes` kept ONE url per route name and the last entry
        overwrote the earlier ones, so the coverage question depended on which
        entry the parser happened to keep. Six of the eighteen core apps
        register a method under several paths with differing urls —
        zaakafhandelapp does it 13 times, with `'postfix'` entries that exist
        for exactly this purpose. A test for either path is a test for the
        endpoint."""
        self.app.write("appinfo/routes.php", """<?php
return ['routes' => [
    ['name' => 'thing#destroy', 'url' => '/api/things', 'verb' => 'DELETE'],
    ['name' => 'thing#destroy', 'postfix' => 'byId',
     'url' => '/api/things/{id}', 'verb' => 'DELETE'],
]];
""")
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx"}, "item": [{"name": "second path",'
            ' "request": {"method": "DELETE", "url": {"raw":'
            ' "{{base}}/api/things/7"}}}]}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_PASS, out)

    def test_a_route_is_not_covered_by_a_request_that_extends_it(self):
        """The right edge is end-of-url, not any segment boundary. A request
        to `/api/things/7/children` is a request to a different endpoint that
        merely has this route as a prefix."""
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx"}, "item": [{"name": "kids",'
            ' "request": {"method": "GET", "url": {"raw":'
            ' "{{base}}/api/things/7/children"}}}]}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_FAIL, out)
        self.assertIn("thing#destroy", out)

    def test_a_neighbouring_path_is_not_the_route(self):
        """`/api/things` must not be satisfied by `/api/thingsummary`, and the
        left edge must be a segment boundary too."""
        self.app.write(
            "tests/integration/things.postman_collection.json",
            '{"info": {"name": "Fx"}, "item": [{"name": "summary",'
            ' "request": {"method": "GET", "url": {"raw":'
            ' "{{base}}/xapi/thingsummary"}}}]}\n',
        )
        self.app.commit()
        rc, out = self.app.verdict()
        self.assertEqual(rc, ccc.EXIT_FAIL, out)
        self.assertIn("thing#destroy", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
