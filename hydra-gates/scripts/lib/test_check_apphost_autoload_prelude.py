#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_apphost_autoload_prelude. Run with:

    python3 scripts/lib/test_check_apphost_autoload_prelude.py

The first two cases are the ones that matter: a KNOWN-BAD app must go RED, and
the same app with the prelude added must go GREEN. A gate that has only ever
been observed passing is indistinguishable from a gate that cannot fail.
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_apphost_autoload_prelude as gate  # noqa: E402

PRELUDE = """
        try {
            $orPath = \\OCP\\Server::get(\\OCP\\App\\IAppManager::class)->getAppPath('openregister');
            \\OC_App::registerAutoloading('openregister', $orPath);
        } catch (\\Throwable) {
            // OpenRegister absent/disabled — fall through to the degraded path.
        }
"""

UNGUARDED_BOOTSTRAP = """<?php
namespace OCA\\Leaf\\AppInfo;

use OCA\\OpenRegister\\AppHost\\Bootstrap;
use OCP\\AppFramework\\App;

class Application extends App
{
    public function register($context): void
    {
%s
        Bootstrap::register($context, 'leaf', ['namespace' => 'OCA\\\\Leaf']);
        $context->registerEventListener(SomeEvent::class, SomeListener::class);
    }
}
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _run(app_dir: Path) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = gate.main(["check_apphost_autoload_prelude.py", str(app_dir)])
    return rc, buf.getvalue()


class GateCase(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="apphost-prelude-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def app(self, name: str, content: str) -> None:
        _write(self.dir / "lib" / "AppInfo" / name, content)


class SeverityFramingTest(GateCase):
    """The message must not overclaim. An app sorting AFTER openregister works
    today; saying otherwise makes the gate look like it is crying wolf."""

    def _with_id(self, app_id: str) -> None:
        _write(
            self.dir / "appinfo" / "info.xml",
            f"<?xml version='1.0'?>\n<info>\n <id>{app_id}</id>\n</info>\n",
        )
        self.app("Application.php", UNGUARDED_BOOTSTRAP % "")

    def test_app_sorting_before_openregister_is_LIVE_EXPOSED(self):
        self._with_id("doriath")
        rc, out = _run(self.dir)
        self.assertEqual(rc, 1)
        self.assertIn("LIVE-EXPOSED", out)
        self.assertIn("sorts BEFORE", out)

    def test_app_sorting_after_openregister_is_LATENT(self):
        self._with_id("pipelinq")
        rc, out = _run(self.dir)
        self.assertEqual(rc, 1, "still a landmine, so still a failure")
        self.assertIn("LATENT", out)
        self.assertIn("by alphabet alone", out)
        self.assertNotIn("LIVE-EXPOSED", out)

    def test_app_id_comes_from_info_xml_not_the_directory_name(self):
        """The checkout directory is not what Nextcloud sorts on."""
        self._with_id("zzz-sorts-last")
        rc, out = _run(self.dir)
        self.assertEqual(rc, 1)
        self.assertIn("zzz-sorts-last", out)
        self.assertIn("LATENT", out)


class RedThenGreenTest(GateCase):
    """The proof that the gate can fail, and that the documented fix clears it."""

    def test_known_bad_input_is_RED(self):
        self.app("Application.php", UNGUARDED_BOOTSTRAP % "")
        rc, out = _run(self.dir)
        self.assertEqual(rc, 1, "an unguarded Bootstrap reference with no prelude MUST fail")
        self.assertIn("FAIL", out)
        self.assertIn("Application.php", out)

    def test_same_app_with_the_prelude_is_GREEN(self):
        self.app("Application.php", UNGUARDED_BOOTSTRAP % PRELUDE)
        rc, out = _run(self.dir)
        self.assertEqual(rc, 0, "the documented prelude MUST clear the gate")
        self.assertIn("apphost-autoload-prelude: OK", out)


class NamedConstantPreludeTest(GateCase):
    """The app id may be given a NAME, and that must not be a finding.

    doriath writes the prelude as

        \\OC_App::registerAutoloading(self::OPENREGISTER_APP_ID, $path);

    with `private const OPENREGISTER_APP_ID = 'openregister';` four lines
    above. That is the same call as the documented one, spelled better — and
    the gate reported it as having NO prelude, because the matcher required a
    QUOTED literal inside the parentheses.

    Measured on doriath#163: gate-64 FAIL, "2 AppHost adoption(s) with no
    OpenRegister autoload prelude", with the prelude present and correct.

    The three tests below are one unit. The first is the fix; the second and
    third are what stop the fix from being "accept any argument", which would
    make the gate blind to the defect it exists to catch.
    """

    CONST_FORM = """<?php
namespace OCA\\Leaf\\AppInfo;
use OCA\\OpenRegister\\AppHost\\Bootstrap;
class Application {
    private const %s = '%s';
    public function register($context): void {
        $path = \\OCP\\Server::get(\\OCP\\App\\IAppManager::class)->getAppPath('openregister');
        \\OC_App::registerAutoloading(self::%s, $path);
        Bootstrap::register($context, 'leaf', []);
    }
}
"""

    def test_named_constant_bound_to_openregister_is_GREEN(self):
        self.app("Application.php", self.CONST_FORM % (
            "OPENREGISTER_APP_ID", "openregister", "OPENREGISTER_APP_ID"))
        rc, out = _run(self.dir)
        self.assertEqual(
            rc, 0,
            "a const bound to 'openregister' IS the prelude — this is doriath's shape")
        self.assertIn("apphost-autoload-prelude: OK", out)

    def test_constant_bound_to_another_app_still_FAILS(self):
        """The discriminator. Same syntax, different binding."""
        self.app("Application.php", self.CONST_FORM % (
            "SOME_OTHER_APP_ID", "opencatalogi", "SOME_OTHER_APP_ID"))
        rc, out = _run(self.dir)
        self.assertEqual(
            rc, 1,
            "registerAutoloading() for a DIFFERENT app is not an OpenRegister prelude")
        self.assertIn("FAIL", out)

    def test_unknown_constant_still_FAILS(self):
        """A name the blob never binds must not be taken on trust."""
        self.app("Application.php", """<?php
namespace OCA\\Leaf\\AppInfo;
use OCA\\OpenRegister\\AppHost\\Bootstrap;
class Application {
    public function register($context): void {
        \\OC_App::registerAutoloading(self::NEVER_DEFINED_ANYWHERE, $path);
        Bootstrap::register($context, 'leaf', []);
    }
}
""")
        rc, out = _run(self.dir)
        self.assertEqual(
            rc, 1,
            "an unresolvable name must not satisfy the gate — that is how it goes blind")
        self.assertIn("FAIL", out)

    def test_variable_and_define_spellings_are_accepted(self):
        self.app("Application.php", """<?php
namespace OCA\\Leaf\\AppInfo;
use OCA\\OpenRegister\\AppHost\\Bootstrap;
class Application {
    public function register($context): void {
        $openRegisterAppId = 'openregister';
        $path = \\OCP\\Server::get(\\OCP\\App\\IAppManager::class)->getAppPath($openRegisterAppId);
        \\OC_App::registerAutoloading($openRegisterAppId, $path);
        Bootstrap::register($context, 'leaf', []);
    }
}
""")
        rc, out = _run(self.dir)
        self.assertEqual(rc, 0, "a variable bound to the literal is the same prelude")


class DetectionShapesTest(GateCase):
    def test_class_exists_probe_without_prelude_is_RED(self):
        self.app("Application.php", """<?php
namespace OCA\\Leaf\\AppInfo;
class Application {
    public function register($context): void {
        if (class_exists('OCA\\\\OpenRegister\\\\AppHost\\\\Routes') === true) {
            $context->registerService('x', fn () => null);
        }
    }
}
""")
        rc, out = _run(self.dir)
        self.assertEqual(rc, 1)
        self.assertIn("class_exists()", out)

    def test_fqcn_string_form_is_detected(self):
        self.app("Application.php", """<?php
namespace OCA\\Leaf\\AppInfo;
class Application {
    public function register($context): void {
        $b = 'OCA\\\\OpenRegister\\\\AppHost\\\\Bootstrap';
        $b::register($context, 'leaf', []);
    }
}
""")
        self.assertEqual(_run(self.dir)[0], 1)

    def test_prelude_in_a_sibling_composition_root_file_is_accepted(self):
        self.app("Application.php", UNGUARDED_BOOTSTRAP % "        $this->prelude();\n")
        self.app("AutoloadPrelude.php", "<?php\nnamespace OCA\\Leaf\\AppInfo;\nclass AutoloadPrelude {\n public function prelude(): void {\n%s\n }\n}\n" % PRELUDE)
        rc, out = _run(self.dir)
        self.assertEqual(rc, 0, "the prelude may live in a sibling file register() calls")


class NoFalsePositiveTest(GateCase):
    def test_lazy_container_string_reference_is_not_flagged(self):
        """A closure body that resolves an AppHost service runs long after every
        app has registered. Flagging it would make the gate noise."""
        self.app("Application.php", """<?php
namespace OCA\\Leaf\\AppInfo;
class Application {
    public function register($context): void {
        $context->registerService('health', function ($c) {
            return $c->get('OCA\\\\OpenRegister\\\\AppHost\\\\Observability\\\\MetricsEngine');
        });
    }
}
""")
        rc, out = _run(self.dir)
        self.assertEqual(rc, 0, "lazy closure bodies must NOT be flagged")

    def test_openregister_itself_is_exempt(self):
        self.app("Application.php", """<?php
namespace OCA\\OpenRegister\\AppInfo;
use OCA\\OpenRegister\\AppHost\\Bootstrap;
class Application {
    public function register($context): void {
        Bootstrap::register($context, 'openregister', []);
    }
}
""")
        self.assertEqual(_run(self.dir)[0], 0, "OpenRegister owns AppHost")

    def test_app_with_no_lib_appinfo_is_clean(self):
        (self.dir / "src").mkdir(parents=True, exist_ok=True)
        self.assertEqual(_run(self.dir)[0], 0)


class SuppressionTest(GateCase):
    def test_reason_bearing_suppression_is_accepted(self):
        self.app("Application.php", UNGUARDED_BOOTSTRAP % (
            "        // apphost-prelude exclude this app is openregister's own test harness\n"
        ))
        self.assertEqual(_run(self.dir)[0], 0)

    def test_bare_suppression_with_no_reason_still_FAILS(self):
        self.app("Application.php", UNGUARDED_BOOTSTRAP % (
            "        // apphost-prelude exclude\n"
        ))
        self.assertEqual(
            _run(self.dir)[0], 1,
            "a bare annotation with no reason must not buy a pass",
        )


class WrongFixTest(GateCase):
    def test_loadApp_is_rejected_and_explained(self):
        self.app("Application.php", UNGUARDED_BOOTSTRAP % (
            "        \\OCP\\Server::get(\\OCP\\App\\IAppManager::class)->loadApp('openregister');\n"
        ))
        rc, out = _run(self.dir)
        self.assertEqual(rc, 1, "loadApp() is not a prelude")
        self.assertIn("bootApp()", out)


if __name__ == "__main__":
    unittest.main()
