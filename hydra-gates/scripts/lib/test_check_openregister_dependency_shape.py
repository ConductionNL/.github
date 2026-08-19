#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for ADR-083's gate.

Every check is asserted in BOTH directions. A gate that has only ever been
seen to pass is indistinguishable from one that cannot fail, and this suite
exists because that failure mode has already cost this fleet real findings.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import check_openregister_dependency_shape as mod


def _app(files: dict, routes: str | None = None) -> str:
    """Lay out a throwaway app tree and return its root.

    *files* maps a path under lib/ to PHP source.
    """
    root = tempfile.mkdtemp()
    for rel, body in files.items():
        p = Path(root) / "lib" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    if routes is not None:
        p = Path(root) / "appinfo"
        p.mkdir(parents=True, exist_ok=True)
        (p / "routes.php").write_text(routes, encoding="utf-8")
    return root


def _run(root: str, check: str = "all") -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = mod.main(["check", root, "--check", check])
    return rc, buf.getvalue()


_ROUTES_ROOT = """<?php
return ['routes' => [
    ['name' => 'page#index', 'url' => '/', 'verb' => 'GET'],
]];
"""


class ContainerLookup(unittest.TestCase):
    def test_container_lookup_is_reported(self):
        root = _app({"Service/AccountService.php": """<?php
namespace OCA\\Demo\\Service;
class AccountService {
    private function os(): object {
        return $this->container->get('OCA\\OpenRegister\\Service\\ObjectService');
    }
}
"""})
        rc, out = _run(root, "lookup")
        self.assertEqual(rc, 1)
        self.assertIn("container lookup", out)

    def test_constructor_injection_is_not_reported(self):
        """The shape ADR-083 asks for must not be what it flags."""
        root = _app({"Service/AccountService.php": """<?php
namespace OCA\\Demo\\Service;
use OCA\\OpenRegister\\Service\\ObjectService;
class AccountService {
    public function __construct(
        private readonly ObjectService $objectService,
    ) {}
}
"""})
        rc, out = _run(root, "lookup")
        self.assertEqual(rc, 0, out)

    def test_availability_guarded_lookup_is_not_reported(self):
        """A lookup behind isInstalled() is the CORRECT shape, not a violation.

        Measured on portaliq 2026-08-14. Injecting this dependency would make
        the whole service unconstructable without OpenRegister, turning a clean
        "not installed" message into a 500 — the exact failure rule 3 exists to
        prevent. Rule 1 governs UNCONDITIONAL dependencies.
        """
        src = """\
<?php
namespace OCA\\Portaliq\\Service;
class SettingsService {
    public function isOpenRegisterAvailable(): bool {
        return $this->appManager->isInstalled('openregister');
    }
    public function loadConfiguration(): array {
        if ($this->isOpenRegisterAvailable() === false) {
            return ['success' => false, 'message' => 'OpenRegister is not installed or enabled.'];
        }
        $cfg = $this->container->get('OCA\\OpenRegister\\Service\\ConfigurationService');
        return $cfg->importFromApp();
    }
}
"""
        rc, out = _run(_app({"Service/SettingsService.php": src}), "lookup")
        self.assertEqual(rc, 0, out)

    def test_getInstalledApps_guard_is_recognised(self):
        """The fleet's DOMINANT guard — 102 call sites, against 10 for isInstalled.

        Measured on zaakafhandelapp 2026-08-14. The first cut of the
        availability list quoted only `isInstalled` because that is the idiom
        the ADR happened to use, and it misread every one of these as a
        violation.
        """
        src = """\
<?php
namespace OCA\\Zaakafhandelapp\\Service;
class ObjectMapperService {
    public function getOpenRegisters(): ?object {
        if (in_array(needle: 'openregister', haystack: $this->appManager->getInstalledApps())) {
            try {
                return $this->container->get('OCA\\OpenRegister\\Service\\ObjectService');
            } catch (Exception $e) {
                return null;
            }
        }
        return null;
    }
}
"""
        rc, out = _run(_app({"Service/ObjectMapperService.php": src}), "lookup")
        self.assertEqual(rc, 0, out)

    def test_class_exists_guard_is_recognised(self):
        """`class_exists` answers the question DI would otherwise answer fatally."""
        src = """\
<?php
namespace OCA\\Demo\\Service;
class Thing {
    public function run(): array {
        if (class_exists('OCA\\OpenRegister\\Service\\ObjectService') === false) {
            return [];
        }
        return $this->container->get('OCA\\OpenRegister\\Service\\ObjectService')->findAll();
    }
}
"""
        rc, out = _run(_app({"Service/Thing.php": src}), "lookup")
        self.assertEqual(rc, 0, out)

    def test_degrading_catch_is_recognised_as_optional_capability(self):
        """A catch that degrades answers availability by TRYING rather than asking.

        launchpad documents its own: "Retrieve ObjectService lazily —
        OpenRegister may not be enabled on every instance. Returning an empty
        manifest (not an error) lets the frontend render its 'no dashboards
        yet' CTA without a red alert."
        """
        src = """\
<?php
namespace OCA\\Launchpad\\Controller;
class ManifestController {
    public function index(): array {
        try {
            $objectService = $this->container->get('OCA\\OpenRegister\\Service\\ObjectService');
        } catch (\\Throwable $e) {
            $this->logger->warning('OpenRegister unavailable — empty manifest.');
            return [];
        }
        return $objectService->findAll();
    }
}
"""
        rc, out = _run(_app({"Controller/ManifestController.php": src}), "lookup")
        self.assertEqual(rc, 0, out)

    def test_rethrowing_catch_is_still_reported(self):
        """Abuse control: a catch that RETHROWS is an unconditional dep in disguise.

        Without this the clause would clear every lookup that merely sits in a
        try, which is most of them.
        """
        src = """\
<?php
namespace OCA\\Demo\\Service;
class AccountService {
    private function os(): object {
        try {
            return $this->container->get('OCA\\OpenRegister\\Service\\ObjectService');
        } catch (\\Throwable $e) {
            throw new RuntimeException('OpenRegister ObjectService is unavailable.', 0, $e);
        }
    }
}
"""
        rc, out = _run(_app({"Service/AccountService.php": src}), "lookup")
        self.assertEqual(rc, 1, out)
        self.assertIn("unguarded container lookup", out)

    def test_composition_root_is_exempt(self):
        """lib/AppInfo/Application.php IS the wiring layer, so rule 1 is silent there.

        Its registration closures take the container as a PARAMETER — that is
        not a service reaching around its own constructor. 16 of 435 findings
        sat here, including all four of opencatalogi's.
        """
        src = """\
<?php
namespace OCA\\Opencatalogi\\AppInfo;
class Application {
    public function register($context): void {
        $context->registerService('X', function ($c) {
            return new Thing(
                manifestLoader: $c->get('OCA\\OpenRegister\\AppHost\\Observability\\ManifestLoader')
            );
        });
    }
}
"""
        rc, out = _run(_app({"AppInfo/Application.php": src}), "lookup")
        self.assertEqual(rc, 0, out)

    def test_a_service_named_Application_elsewhere_is_not_exempt(self):
        """Abuse control: the exemption is the PATH, not the class name."""
        src = """\
<?php
namespace OCA\\Demo\\Service;
class Application {
    public function run(): array {
        return $this->container->get('OCA\\OpenRegister\\Service\\ObjectService')->findAll();
    }
}
"""
        rc, out = _run(_app({"Service/Application.php": src}), "lookup")
        self.assertEqual(rc, 1, out)

    def test_unguarded_lookup_in_the_same_shape_is_still_reported(self):
        """Abuse control: drop the availability check and the finding returns.

        Without this, the guard clause above could be satisfied by any file that
        merely mentions the word, and the whole check would go quiet.
        """
        src = """\
<?php
namespace OCA\\Portaliq\\Service;
class SettingsService {
    public function loadConfiguration(): array {
        $cfg = $this->container->get('OCA\\OpenRegister\\Service\\ConfigurationService');
        return $cfg->importFromApp();
    }
}
"""
        rc, out = _run(_app({"Service/SettingsService.php": src}), "lookup")
        self.assertEqual(rc, 1, out)
        self.assertIn("unguarded container lookup", out)

    def test_lookup_named_only_in_a_comment_is_not_reported(self):
        """Abuse control: a docblock must not be able to fail the gate either."""
        root = _app({"Service/AccountService.php": """<?php
namespace OCA\\Demo\\Service;
use OCA\\OpenRegister\\Service\\ObjectService;
class AccountService {
    /**
     * Was $this->container->get('OCA\\OpenRegister\\Service\\ObjectService');
     * before ADR-083.
     */
    public function __construct(private readonly ObjectService $objectService) {}
}
"""})
        rc, out = _run(root, "lookup")
        self.assertEqual(rc, 0, out)


class ClassHeader(unittest.TestCase):
    def test_extends_openregister_is_reported(self):
        root = _app({"Service/Thing.php": """<?php
namespace OCA\\Demo\\Service;
class Thing extends \\OCA\\OpenRegister\\Service\\ObjectService {
}
"""})
        rc, out = _run(root, "header")
        self.assertEqual(rc, 1)
        self.assertIn("class header", out)

    def test_implements_openregister_is_reported(self):
        root = _app({"Service/Provider.php": """<?php
namespace OCA\\Demo\\Service;
class Provider implements \\OCA\\OpenRegister\\Contract\\IThing {
}
"""})
        rc, out = _run(root, "header")
        self.assertEqual(rc, 1)

    def test_injecting_an_openregister_type_is_not_a_header_finding(self):
        """Rule 1 asks for exactly this; rule 2 must not contradict it."""
        root = _app({"Service/Thing.php": """<?php
namespace OCA\\Demo\\Service;
use OCA\\OpenRegister\\Service\\ObjectService;
class Thing {
    public function __construct(private readonly ObjectService $objectService) {}
}
"""})
        rc, out = _run(root, "header")
        self.assertEqual(rc, 0, out)


class FrontpageReachability(unittest.TestCase):
    def test_frontpage_controller_touching_openregister_is_reported(self):
        root = _app({"Controller/PageController.php": """<?php
namespace OCA\\Demo\\Controller;
use OCA\\OpenRegister\\Db\\OrganisationMapper;
class PageController {
    public function __construct(private readonly OrganisationMapper $orgs) {}
    public function index() {}
}
"""}, routes=_ROUTES_ROOT)
        rc, out = _run(root, "frontpage")
        self.assertEqual(rc, 1)
        self.assertIn("default route", out)

    def test_frontpage_reaching_openregister_one_hop_out_is_reported(self):
        """The transitive case — the one convention cannot catch."""
        root = _app({
            "Controller/PageController.php": """<?php
namespace OCA\\Demo\\Controller;
use OCA\\Demo\\Service\\StatsService;
class PageController {
    public function __construct(private readonly StatsService $stats) {}
    public function index() {}
}
""",
            "Service/StatsService.php": """<?php
namespace OCA\\Demo\\Service;
use OCA\\OpenRegister\\Service\\ObjectService;
class StatsService {
    public function __construct(private readonly ObjectService $objectService) {}
}
""",
        }, routes=_ROUTES_ROOT)
        rc, out = _run(root, "frontpage")
        self.assertEqual(rc, 1)
        self.assertIn("StatsService", out)

    def test_core_only_frontpage_passes(self):
        """The conforming shape: core deps only, availability published."""
        root = _app({
            "Controller/PageController.php": """<?php
namespace OCA\\Demo\\Controller;
use OCP\\App\\IAppManager;
use OCP\\AppFramework\\Services\\IInitialState;
class PageController {
    public function __construct(
        private readonly IAppManager $appManager,
        private readonly IInitialState $initialState,
    ) {}
    public function index() {
        $this->initialState->provideInitialState(
            'openregister_available', $this->appManager->isInstalled('openregister')
        );
    }
}
""",
            "Service/AccountService.php": """<?php
namespace OCA\\Demo\\Service;
use OCA\\OpenRegister\\Service\\ObjectService;
class AccountService {
    public function __construct(private readonly ObjectService $objectService) {}
}
""",
        }, routes=_ROUTES_ROOT)
        rc, out = _run(root, "frontpage")
        self.assertEqual(rc, 0, out)


class ScopeCodes(unittest.TestCase):
    def test_no_lib_is_a_skip_not_a_pass(self):
        root = tempfile.mkdtemp()
        rc, out = _run(root)
        self.assertEqual(rc, 3)
        self.assertIn("checked 0 file(s)", out)

    def test_app_without_openregister_reports_its_own_code(self):
        root = _app({"Service/Plain.php": "<?php\nnamespace OCA\\Demo\\Service;\nclass Plain {}\n"})
        rc, out = _run(root)
        self.assertEqual(rc, 4)
        self.assertIn("no subject matter", out)

    def test_openregister_itself_is_skipped_not_judged(self):
        """ADR-083 governs how OTHER apps depend on OpenRegister.

        Inside OpenRegister every file is in the OCA\\OpenRegister namespace, so
        "references OpenRegister" is true of the whole tree and says nothing.
        Measured 2026-08-14 before the guard: rule 3 reported openregister's own
        DashboardController twice, for naming its own namespace, with a finding
        that talked about an app unable to boot without a dependency it IS.

        Asserted as 4 (skip), never 0 — nothing here was judged.
        """
        root = _app({
            "Controller/DashboardController.php": """<?php
namespace OCA\\OpenRegister\\Controller;
use OCA\\OpenRegister\\Service\\DashboardService;
class DashboardController {
    public function __construct(private readonly DashboardService $dashboard) {}
    public function index() {}
}
""",
            "Service/DashboardService.php": """<?php
namespace OCA\\OpenRegister\\Service;
class DashboardService {
    public function totals(): array { return []; }
}
""",
        }, routes=_ROUTES_ROOT)
        rc, out = _run(root)
        self.assertEqual(rc, 4, out)
        self.assertIn("IS the OpenRegister app", out)

    def test_a_leaf_app_is_not_mistaken_for_openregister(self):
        """Abuse control: importing OR must not buy the skip that DECLARING it does."""
        root = _app({"Service/AccountService.php": """<?php
namespace OCA\\Pipelinq\\Service;
class AccountService {
    private function os(): object {
        return $this->container->get('OCA\\OpenRegister\\Service\\ObjectService');
    }
}
"""})
        rc, out = _run(root, "lookup")
        self.assertEqual(rc, 1, out)
        self.assertIn("container lookup", out)

    def test_every_run_states_how_many_files_it_read(self):
        """A run that stops before this line crashed; it did not find a clean tree."""
        root = _app({"Service/AccountService.php": """<?php
namespace OCA\\Demo\\Service;
use OCA\\OpenRegister\\Service\\ObjectService;
class AccountService {
    public function __construct(private readonly ObjectService $objectService) {}
}
"""})
        _rc, out = _run(root)
        self.assertRegex(out, r"checked \d+ file\(s\)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
