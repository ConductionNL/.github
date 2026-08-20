#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_no_admin_idor (gate-7). Run with:

    python3 scripts/lib/test_check_no_admin_idor.py

or via pytest:

    python3 -m pytest scripts/lib/test_check_no_admin_idor.py
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_no_admin_idor as cni  # noqa: E402


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _scan(src: str) -> list[str]:
    """Write *src* to a temp file, scan it, capture printed lines."""
    with tempfile.NamedTemporaryFile(
        suffix=".php", mode="w", encoding="utf-8", delete=False
    ) as fh:
        fh.write(src)
        fh_name = fh.name
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            cni.scan_file(fh_name)
    finally:
        os.unlink(fh_name)
    return [ln for ln in buf.getvalue().splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# Exemption 2 — preflightedCors* name prefix
# ---------------------------------------------------------------------------

class PreflightedCorsExemptionTest(unittest.TestCase):
    """Methods whose name starts with preflightedCors must NOT be flagged.

    Nextcloud convention: OPTIONS routes handled by ``preflightedCors`` /
    ``preflightedCorsItem`` / ``preflightedCorsNested`` etc. are sent by
    browsers *without credentials* before the real request; an auth guard
    would break CORS.  These are never IDOR vectors.
    """

    def test_preflightedCors_not_flagged(self):
        """The exact fleet name preflightedCors with @NoAdminRequired is exempted."""
        src = """\
<?php
class DirectoryController {
    /**
     * @NoAdminRequired
     * @NoCSRFRequired
     * @PublicPage
     */
    public function preflightedCors(): Response
    {
        $response = new Response();
        $response->addHeader('Access-Control-Allow-Origin', '*');
        $response->addHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE');
        return $response;
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_preflightedCorsItem_not_flagged(self):
        """Variant suffix preflightedCorsItem is also exempted."""
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     * @NoCSRFRequired
     */
    public function preflightedCorsItem(): Response
    {
        $r = new Response();
        $r->addHeader('Access-Control-Allow-Origin', '*');
        $r->addHeader('Access-Control-Allow-Methods', 'PUT, PATCH');
        return $r;
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_preflightedCors_mixed_case_not_flagged(self):
        """Case-insensitive match: PreflightedCors prefix is also exempt."""
        src = """\
<?php
class SomeController {
    /**
     * @NoAdminRequired
     */
    public function PreflightedCors(): Response
    {
        $r = new Response();
        $r->addHeader('Access-Control-Allow-Origin', 'https://example.com');
        return $r;
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_non_preflight_method_without_guard_is_flagged(self):
        """A method NOT named preflightedCors* without a guard must be flagged."""
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     * @NoCSRFRequired
     */
    public function previewItem(string $id): JSONResponse
    {
        $item = $this->service->find($id);
        return new JSONResponse($item);
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("previewItem", findings[0])
        self.assertIn("no-auth-guard-in-body", findings[0])

    def test_idor_exempt_tag_with_reason_passes(self):
        """`@no-admin-idor-exempt <reason>` in the docblock exempts the method."""
        src = """\
<?php
class XWikiController {
    /**
     * Search xWiki pages.
     *
     * @NoAdminRequired
     * @NoCSRFRequired
     * @no-admin-idor-exempt read-only knowledge-base proxy, no object ids
     */
    public function search(): JSONResponse
    {
        return new JSONResponse($this->xwiki->search($q));
    }
}
"""
        findings = _scan(src)
        self.assertEqual(findings, [])

    def test_idor_exempt_tag_without_reason_still_flagged(self):
        """A bare `@no-admin-idor-exempt` tag (no reason) does NOT exempt."""
        src = """\
<?php
class XWikiController {
    /**
     * @NoAdminRequired
     * @no-admin-idor-exempt
     */
    public function search(): JSONResponse
    {
        return new JSONResponse($this->xwiki->search($q));
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("search", findings[0])

    def test_preview_prefix_not_confused_with_preflight(self):
        """Methods starting with 'preview' are NOT CORS handlers — still flagged."""
        src = """\
<?php
class ObjectController {
    /**
     * @NoAdminRequired
     */
    public function previewObject(): JSONResponse
    {
        return new JSONResponse($this->service->findAll());
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("previewObject", findings[0])


# ---------------------------------------------------------------------------
# Exemption 3 — CORS-headers-only body (no data access)
# ---------------------------------------------------------------------------

class CorsOnlyBodyExemptionTest(unittest.TestCase):
    """Oddly-named handlers that only set Access-Control-* headers are exempt."""

    def test_cors_only_body_exempted(self):
        """A method that only sets CORS headers is exempted even without the name convention."""
        src = """\
<?php
class ApiController {
    /**
     * @NoAdminRequired
     * @NoCSRFRequired
     */
    public function corsHandler(): Response
    {
        $r = new Response();
        $r->addHeader('Access-Control-Allow-Origin', '*');
        $r->addHeader('Access-Control-Allow-Methods', 'GET');
        return $r;
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_cors_plus_data_access_not_exempted(self):
        """A method that sets CORS headers AND accesses data is still flagged."""
        src = """\
<?php
class ApiController {
    /**
     * @NoAdminRequired
     */
    public function index(): JSONResponse
    {
        $data = $this->mapper->findAll();
        $r = new JSONResponse($data);
        $r->addHeader('Access-Control-Allow-Origin', '*');
        return $r;
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("index", findings[0])


# ---------------------------------------------------------------------------
# Exemption 1 — __construct
# ---------------------------------------------------------------------------

class ConstructorExemptionTest(unittest.TestCase):
    def test_constructor_not_flagged(self):
        """__construct is never a routed endpoint — always skipped."""
        src = """\
<?php
class MyController {
    /**
     * @NoAdminRequired
     */
    public function __construct(
        private MyService $service
    ) {
    }
}
"""
        self.assertEqual(_scan(src), [])


# ---------------------------------------------------------------------------
# Guard patterns — must satisfy gate-7
# ---------------------------------------------------------------------------

class GuardPatternTest(unittest.TestCase):
    def test_ocs_forbidden_exception_passes(self):
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function show(string $id): JSONResponse
    {
        if (!$this->canRead($id)) {
            throw new OCSForbiddenException('Access denied');
        }
        return new JSONResponse($this->service->find($id));
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_is_admin_check_passes(self):
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function show(string $id): JSONResponse
    {
        if (!$this->isAdmin()) {
            return new JSONResponse([], Http::STATUS_FORBIDDEN);
        }
        return new JSONResponse($this->service->find($id));
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_authorize_service_call_passes(self):
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function update(string $id): JSONResponse
    {
        $this->authorizationService->authorizeAction('update', $id);
        return new JSONResponse($this->service->find($id));
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_require_service_call_passes(self):
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function destroy(string $id): JSONResponse
    {
        $this->permissionService->requirePermission('delete', $id);
        $this->service->delete($id);
        return new JSONResponse([]);
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_ensure_service_call_passes(self):
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function create(): JSONResponse
    {
        $this->accessService->ensureOwnership($this->userId);
        return new JSONResponse($this->service->create([]));
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_status_unauthorized_from_an_authentication_check_is_FLAGGED(self):
        """INVERTED by `.github#365`. This test used to assert `[]`.

        It is the defect, written down and pinned as correct behaviour: a
        `no user -> 401` preamble is AUTHENTICATION, `$this->service->find($id)`
        below it still takes an arbitrary caller-supplied id, and the gate went
        silent. gate-7 reported 0 in all 18 fleet apps on the strength of this.
        """
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function show(string $id): JSONResponse
    {
        if ($this->userSession->getUser() === null) {
            return new JSONResponse([], Http::STATUS_UNAUTHORIZED);
        }
        return new JSONResponse($this->service->find($id));
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("show", findings[0])

    def test_status_unauthorized_from_a_per_object_check_still_passes(self):
        """The other half of `#365`, and the one that keeps this fix honest.

        Byte-identical response line, byte-identical status constant — the ONLY
        difference from the test above is that the condition compares object
        data against the caller. That is a real authorisation guard written with
        the wrong status code, and flagging it would be the false positive that
        made gate-7 untrusted (`#353`, `#360`).
        """
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function show(string $id): JSONResponse
    {
        $item = $this->service->find($id);
        if ($item['ownerId'] !== $this->userId) {
            return new JSONResponse([], Http::STATUS_UNAUTHORIZED);
        }
        return new JSONResponse($item);
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_authentication_preamble_answering_403_is_also_FLAGGED(self):
        """The status code is not what makes a check an authorisation guard.

        `#365` as filed proposes dropping `401`/`UNAUTHORIZED` from the guard
        regex. That repair would leave this method green — and turning
        `STATUS_UNAUTHORIZED` into `STATUS_FORBIDDEN` is a one-token edit, so
        the silence could be bought straight back by making the code WORSE.
        Authentication-ness is a property of the CONDITION.
        """
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function show(string $id): JSONResponse
    {
        if ($this->userSession->getUser() === null) {
            return new JSONResponse([], Http::STATUS_FORBIDDEN);
        }
        return new JSONResponse($this->service->find($id));
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("show", findings[0])

    def test_presence_test_wrapping_the_body_does_not_blank_the_guard(self):
        """Polarity control — the blanking must not eat a whole method body.

        `if ($user !== null) { ...everything... }` is a WRAPPER, not a guard
        clause. Blanking it would erase the real ownership check inside and
        report a correctly-guarded method.
        """
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function show(string $id): JSONResponse
    {
        $user = $this->userSession->getUser();
        if ($user !== null) {
            $item = $this->service->find($id);
            if ($item['ownerId'] !== $user->getUID()) {
                return new JSONResponse([], Http::STATUS_FORBIDDEN);
            }
            return new JSONResponse($item);
        }
        return new JSONResponse([], Http::STATUS_NOT_FOUND);
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_template_response_passes(self):
        """SPA page renderers that return TemplateResponse are exempt."""
        src = """\
<?php
class DashboardController {
    /**
     * @NoAdminRequired
     */
    public function page(): TemplateResponse
    {
        return new TemplateResponse('myapp', 'index');
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_template_response_in_return_type_hint_passes(self):
        """TemplateResponse in the return-type hint (not in the body) is also exempt.

        The bash gate includes the function declaration line in its _body
        variable, so a method like ``dashboard(): TemplateResponse`` that
        delegates to ``$this->makeSpaResponse()`` passes because the return
        type hint contains 'TemplateResponse'. The Python implementation must
        match this behaviour.
        """
        src = """\
<?php
class UiController {
    /**
     * @NoAdminRequired
     * @NoCSRFRequired
     */
    public function dashboard(): TemplateResponse
    {
        return $this->makeSpaResponse();
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_public_page_annotation_on_method_passes(self):
        """@PublicPage on the method head satisfies the gate."""
        src = """\
<?php
class PublicController {
    /**
     * @NoAdminRequired
     * @PublicPage
     */
    public function listing(): JSONResponse
    {
        return new JSONResponse($this->service->findAll());
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_attribute_public_page_passes(self):
        """#[PublicPage] PHP 8 attribute on the method also satisfies the gate."""
        src = """\
<?php
class PublicController {
    /**
     * @NoAdminRequired
     */
    #[PublicPage]
    public function listing(): JSONResponse
    {
        return new JSONResponse($this->service->findAll());
    }
}
"""
        self.assertEqual(_scan(src), [])


# ---------------------------------------------------------------------------
# Real IDOR violation — must be caught
# ---------------------------------------------------------------------------

class RealIdorViolationTest(unittest.TestCase):
    def test_no_guard_at_all_is_flagged(self):
        """A @NoAdminRequired method with no guard, no PublicPage, no exemption is flagged."""
        src = """\
<?php
class ObjectsController {
    /**
     * @NoAdminRequired
     * @NoCSRFRequired
     */
    public function show(string $id): JSONResponse
    {
        $object = $this->objectService->find($id);
        return new JSONResponse($object);
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("show", findings[0])
        self.assertIn("no-auth-guard-in-body", findings[0])

    def test_multiple_violations_all_reported(self):
        """Multiple unguarded methods in the same file are all reported."""
        src = """\
<?php
class ObjectsController {
    /**
     * @NoAdminRequired
     */
    public function index(): JSONResponse
    {
        return new JSONResponse($this->service->findAll());
    }

    /**
     * @NoAdminRequired
     */
    public function show(string $id): JSONResponse
    {
        return new JSONResponse($this->service->find($id));
    }

    /**
     * @NoAdminRequired
     */
    public function destroy(string $id): JSONResponse
    {
        $this->service->delete($id);
        return new JSONResponse([]);
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 3)
        names = {f.split("method=")[1].split(" ")[0] for f in findings}
        self.assertEqual(names, {"index", "show", "destroy"})

    def test_method_without_no_admin_required_not_flagged(self):
        """Methods that lack @NoAdminRequired are out of scope for gate-7."""
        src = """\
<?php
class AdminController {
    public function adminAction(): JSONResponse
    {
        return new JSONResponse($this->service->findAll());
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_idor_with_cors_plus_data_access(self):
        """A method with CORS headers AND data access is still flagged if no guard."""
        src = """\
<?php
class ApiController {
    /**
     * @NoAdminRequired
     */
    public function records(): JSONResponse
    {
        $rows = $this->mapper->findAll();
        $r = new JSONResponse($rows);
        $r->addHeader('Access-Control-Allow-Origin', '*');
        return $r;
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("records", findings[0])


# ---------------------------------------------------------------------------
# Pattern 1 — private guard-helper delegation
# ---------------------------------------------------------------------------

class GuardHelperDelegationTest(unittest.TestCase):
    """A routed method that delegates its guard to a same-class helper passes."""

    def test_helper_that_throws_clears_caller(self):
        """Caller invoking a helper whose body throws is guarded."""
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function show(string $id): JSONResponse
    {
        $this->guardCase($id);
        return new JSONResponse($this->service->find($id));
    }

    private function guardCase(string $id): void
    {
        if (!$this->canRead($id)) {
            throw new OCSForbiddenException('nope');
        }
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_helper_returning_403_response_clears_caller(self):
        """Helper that returns a 403 Response (checked by caller) is a guard."""
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function index(): JSONResponse
    {
        $denial = $this->requireAdmin();
        if ($denial !== null) {
            return $denial;
        }
        return new JSONResponse($this->service->findAll());
    }

    private function requireAdmin(): ?JSONResponse
    {
        if ($this->isCurrentUserAdmin() === false) {
            return new JSONResponse(['error' => 'forbidden'], 403);
        }
        return null;
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_predicate_named_helper_clears_caller(self):
        """A helper whose NAME reads as an auth predicate counts as a guard."""
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function destroy(string $id): JSONResponse
    {
        if ($this->isCurrentUserAdmin() === false) {
            return new JSONResponse([], 403);
        }
        $this->service->delete($id);
        return new JSONResponse([]);
    }

    private function isCurrentUserAdmin(): bool
    {
        return $this->groupManager->isInGroup($this->userId, 'admin');
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_guard_helper_after_mutation_still_flags(self):
        """A guard-helper called only AFTER the write does not protect it."""
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function update(string $id): JSONResponse
    {
        $this->service->updateThing($id);
        $this->assertMayAct($id);
        return new JSONResponse([]);
    }

    private function assertMayAct(string $id): void
    {
        throw new OCSForbiddenException('too late');
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("update", findings[0])

    def test_calling_non_guard_helper_still_flags(self):
        """Invoking an ordinary (non-guard) helper does NOT clear the finding."""
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function show(string $id): JSONResponse
    {
        $data = $this->serialize($id);
        return new JSONResponse($data);
    }

    private function serialize(string $id): array
    {
        return ['id' => $id];
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("show", findings[0])


# ---------------------------------------------------------------------------
# Pattern 2 — OpenRegister data-layer RBAC delegation (ADR-022)
# ---------------------------------------------------------------------------

class OrDataLayerDelegationTest(unittest.TestCase):
    """OR-namespace methods delegating to ObjectService / a *Mapper pass."""

    def test_objectservice_access_in_or_namespace_cleared(self):
        """@NoAdminRequired + ObjectService fetch inside OCA\\OpenRegister passes."""
        src = """\
<?php
namespace OCA\\OpenRegister\\Controller;
class ObjectsController {
    /**
     * @NoAdminRequired
     */
    public function show(string $id): JSONResponse
    {
        $object = $this->objectService->find($id);
        return new JSONResponse($object);
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_mapper_access_in_or_namespace_cleared(self):
        """@NoAdminRequired + *Mapper fetch inside OCA\\OpenRegister passes."""
        src = """\
<?php
namespace OCA\\OpenRegister\\Controller;
class SourcesController {
    /**
     * @NoAdminRequired
     */
    public function index(): JSONResponse
    {
        $sources = $this->sourceMapper->findAll();
        return new JSONResponse($sources);
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_helper_objectservice_fetch_in_or_namespace_cleared(self):
        """A validateObject-style helper doing the OR RBAC fetch clears the caller."""
        src = """\
<?php
namespace OCA\\OpenRegister\\Controller;
class DeckLinksController {
    /**
     * @NoAdminRequired
     */
    public function index(string $register, string $schema, string $id): JSONResponse
    {
        $object = $this->validateObject($register, $schema, $id);
        if ($object === null) {
            return new JSONResponse(['error' => 'not found'], 404);
        }
        return new JSONResponse($this->deckLinkService->getLinkedCards($object->getUuid()));
    }

    private function validateObject(string $register, string $schema, string $id): ?ObjectEntity
    {
        $this->objectService->setRegister($register);
        $this->objectService->setSchema($schema);
        $this->objectService->setObject($id);
        return $this->objectService->getObject();
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_same_objectservice_access_OUTSIDE_or_namespace_still_flags(self):
        """A leaf app whose `$this->objectService` is NOT OpenRegister's still flags.

        This is the decidesk#44 safety proof. Pattern 2b (2026-08-14) lets a
        leaf app delegate authorisation to OpenRegister, but only when the file
        actually imports `OCA\\OpenRegister\\…\\ObjectService`. This fixture
        does not, so `$this->objectService` is an unresolved local collaborator
        and clears nothing — a real IDOR is still reported.
        """
        src = """\
<?php
namespace OCA\\Decidesk\\Controller;
class MinutesController {
    /**
     * @NoAdminRequired
     */
    public function generateALVDraft(string $minutesId): JSONResponse
    {
        $minutes = $this->objectService->findObject(id: $minutesId);
        return new JSONResponse($this->generate($minutes));
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("generateALVDraft", findings[0])

    def test_leaf_app_delegating_to_openregister_objectservice_cleared(self):
        """ADR-022: a leaf app reaching objects through OR's ObjectService is guarded.

        Measured on openbuild 2026-08-14: RulesController::evaluate resolved via
        `searchObjectsBySlug(..., _rbac: true)` and was reported as an IDOR, in
        direct contradiction of ADR-022, which requires apps to consume OR's
        abstractions including RBAC on data.
        """
        src = """\
<?php
namespace OCA\\OpenBuild\\Controller;

use OCA\\OpenRegister\\Service\\ObjectService;

class RulesController {
    /**
     * @NoAdminRequired
     */
    public function evaluate(string $ruleSetSlug): JSONResponse
    {
        $rows = $this->objectService->searchObjectsBySlug(
            'openbuild', 'rule-set', ['slug' => $ruleSetSlug], _rbac: true, _multitenancy: false
        );
        return new JSONResponse($rows);
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_leaf_app_openregister_delegation_with_rbac_false_still_flags(self):
        """`_rbac: false` withdraws the clear — the app said OR is NOT authorising."""
        src = """\
<?php
namespace OCA\\OpenBuild\\Controller;

use OCA\\OpenRegister\\Service\\ObjectService;

class RulesController {
    /**
     * @NoAdminRequired
     */
    public function evaluate(string $ruleSetSlug): JSONResponse
    {
        $rows = $this->objectService->searchObjectsBySlug(
            'openbuild', 'rule-set', ['slug' => $ruleSetSlug], _rbac: false
        );
        return new JSONResponse($rows);
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("evaluate", findings[0])

    def test_leaf_app_delegating_to_openregister_via_collaborator_cleared(self):
        """Pattern 2b reaches one class out, as Pattern 4 does for other guards.

        openbuild's `RulesController::evaluate` never touches the facade
        itself — it calls `RuleEngineService::evaluate`, which resolves via
        `searchObjectsBySlug(..., _rbac: true)`. Clearing that from a private
        helper but not from an injected service would be an arbitrary
        distinction, since both are the same delegation.

        Uses `_scan_app` because collaborator resolution reads the
        collaborator's own source off disk; an unresolvable type clears nothing.
        """
        engine = """\
<?php
namespace OCA\\OpenBuild\\Service;

use OCA\\OpenRegister\\Service\\ObjectService;

class RuleEngineService {
    public function evaluate(string $slug): array
    {
        return $this->objectService->searchObjectsBySlug(
            'openbuild', 'rule-set', ['slug' => $slug], _rbac: true
        );
    }
}
"""
        controller = """\
<?php
namespace OCA\\OpenBuild\\Controller;

use OCA\\OpenBuild\\Service\\RuleEngineService;

class TestController {
    public function __construct(
        private readonly RuleEngineService $ruleEngine,
    ) {}

    /**
     * @NoAdminRequired
     */
    public function evaluate(string $ruleSetSlug): JSONResponse
    {
        return new JSONResponse($this->ruleEngine->evaluate(slug: $ruleSetSlug));
    }
}
"""
        self.assertEqual(_scan_app(controller, {"RuleEngineService": engine}), [])

    def test_collaborator_without_or_import_does_not_clear(self):
        """Abuse control: an identical shape whose service does NOT reach OR still flags."""
        engine = """\
<?php
namespace OCA\\OpenBuild\\Service;

class RuleEngineService {
    public function evaluate(string $slug): array
    {
        return $this->ruleSetMapper->findBySlug($slug);
    }
}
"""
        controller = """\
<?php
namespace OCA\\OpenBuild\\Controller;

use OCA\\OpenBuild\\Service\\RuleEngineService;

class TestController {
    public function __construct(
        private readonly RuleEngineService $ruleEngine,
    ) {}

    /**
     * @NoAdminRequired
     */
    public function evaluate(string $ruleSetSlug): JSONResponse
    {
        return new JSONResponse($this->ruleEngine->evaluate(slug: $ruleSetSlug));
    }
}
"""
        findings = _scan_app(controller, {"RuleEngineService": engine})
        self.assertEqual(len(findings), 1)
        self.assertIn("evaluate", findings[0])

    def test_container_resolved_openregister_objectservice_cleared(self):
        """The container form counts: a leaf app cannot hard-depend on OR's class.

        Measured on pipelinq 2026-08-14: 75 of 160 service files resolve
        ObjectService out of the container against 11 that import it, because
        OpenRegister may not be installed. Recognising only the `use` import
        declared those 75 unguarded.
        """
        src = """\
<?php
namespace OCA\\Pipelinq\\Controller;

class LoyaltyController {
    /**
     * @NoAdminRequired
     */
    public function accounts(string $programmeId): JSONResponse
    {
        $objectService = $this->container->get('OCA\\OpenRegister\\Service\\ObjectService');
        return new JSONResponse($objectService->findAll(config: ['filters' => ['programmeId' => $programmeId]]));
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_openregister_named_only_in_a_comment_does_not_clear(self):
        """Abuse control: a docblock mention must not qualify the file.

        The container form lives in a string literal, so the check cannot read
        `cleaned` (strings blanked). Reading raw source instead would let a
        sentence in a comment switch this gate off — exactly the failure these
        gates exist to catch. It reads comment-free source, strings preserved.
        """
        src = """\
<?php
namespace OCA\\Pipelinq\\Controller;

class LoyaltyController {
    /**
     * Storage is eventually OCA\\OpenRegister\\Service\\ObjectService, but this
     * controller talks to its own mapper.
     *
     * @NoAdminRequired
     */
    public function accounts(string $programmeId): JSONResponse
    {
        return new JSONResponse($this->accountMapper->findByProgramme($programmeId));
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("accounts", findings[0])

    def test_leaf_app_own_mapper_still_flags_even_with_or_import(self):
        """A leaf app's OWN mapper is its own storage and delegates no authorisation.

        This is the "with the exception of when they have their own services"
        half of the rule: importing OR's ObjectService must not launder an
        endpoint that actually reads through the app's own data layer.
        """
        src = """\
<?php
namespace OCA\\OpenBuild\\Controller;

use OCA\\OpenRegister\\Service\\ObjectService;

class InvoiceController {
    /**
     * @NoAdminRequired
     */
    public function show(string $invoiceId): JSONResponse
    {
        $invoice = $this->invoiceMapper->find($invoiceId);
        return new JSONResponse($invoice);
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("show", findings[0])

    def test_or_namespace_no_data_access_still_flags(self):
        """An OR method with NO ObjectService/Mapper access and no guard still flags."""
        src = """\
<?php
namespace OCA\\OpenRegister\\Controller;
class WidgetController {
    /**
     * @NoAdminRequired
     */
    public function ping(string $id): JSONResponse
    {
        return new JSONResponse($this->externalGateway->call($id));
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("ping", findings[0])


# ---------------------------------------------------------------------------
# Numeric status-code parity (401/403 literal == Http::STATUS_* constant)
# ---------------------------------------------------------------------------

class NumericStatusParityTest(unittest.TestCase):
    def test_numeric_statuscode_named_arg_parity_holds_for_a_real_guard(self):
        """`statusCode: 403` is recognised exactly as `Http::STATUS_FORBIDDEN` is.

        REWRITTEN by `.github#365`. The original body of this test was named
        for 403 and actually wrote `statusCode: 401` behind a `no user` check —
        so it asserted the numeric-parity property over an AUTHENTICATION
        clause, and pinned the `#365` defect while appearing to test spelling
        parity. The parity property is real and is kept; the subject is now a
        per-object comparison, which is what the parity was ever for.
        """
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function show(string $id): JSONResponse
    {
        $item = $this->service->find($id);
        if ($item['ownerId'] !== $this->userId) {
            return new JSONResponse([], statusCode: 403);
        }
        return new JSONResponse($item);
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_numeric_401_statuscode_named_arg_from_authentication_is_FLAGGED(self):
        """The spelling-parity fix must not carry the authentication clause in.

        Same named-argument spelling, same numeric literal position — but the
        condition asks "is anyone logged in?", so it clears nothing.
        """
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function show(string $id): JSONResponse
    {
        if ($this->userSession->getUser() === null) {
            return new JSONResponse([], statusCode: 401);
        }
        return new JSONResponse($this->service->find($id));
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("show", findings[0])

    def test_numeric_403_positional_arg_passes(self):
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function show(string $id): JSONResponse
    {
        if (!$this->canRead($id)) {
            return new JSONResponse(['error' => 'no'], 403);
        }
        return new JSONResponse($this->service->find($id));
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_unrelated_number_403_not_a_false_guard(self):
        """A bare 403 that is not a response status (e.g. an array value) does not clear."""
        src = """\
<?php
class ItemController {
    /**
     * @NoAdminRequired
     */
    public function show(string $id): JSONResponse
    {
        $limit = 403000;
        return new JSONResponse($this->service->find($id, $limit));
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("show", findings[0])


# ---------------------------------------------------------------------------
# _is_preflight_cors_method unit tests
# ---------------------------------------------------------------------------

class IsPreflightCorsMethodTest(unittest.TestCase):
    def test_exact_name_matches(self):
        self.assertTrue(cni._is_preflight_cors_method("preflightedCors"))

    def test_suffix_variant_matches(self):
        self.assertTrue(cni._is_preflight_cors_method("preflightedCorsItem"))
        self.assertTrue(cni._is_preflight_cors_method("preflightedCorsNested"))

    def test_case_insensitive(self):
        self.assertTrue(cni._is_preflight_cors_method("PreflightedCors"))
        self.assertTrue(cni._is_preflight_cors_method("PREFLIGHTEDCORS"))

    def test_preview_prefix_does_not_match(self):
        self.assertFalse(cni._is_preflight_cors_method("previewItem"))

    def test_preflight_alone_does_not_match(self):
        """Only the specific 'preflightedCors' prefix is exempt by name."""
        self.assertFalse(cni._is_preflight_cors_method("preflight"))
        self.assertFalse(cni._is_preflight_cors_method("preflightItem"))

    def test_construct_does_not_match(self):
        self.assertFalse(cni._is_preflight_cors_method("__construct"))


# ---------------------------------------------------------------------------
# Response-helper deny spellings (::forbidden( / ->unauthorized( )
# ---------------------------------------------------------------------------

class ResponseHelperGuardSpellingTest(unittest.TestCase):
    """A deny response routed through a helper is the same guard shape.

    Controllers that centralise deny-responses in a helper class
    (``ResponseHelper::forbidden(...)``) were flagged even though the guard
    was present, purely because the gate only recognised the inline
    ``Http::STATUS_FORBIDDEN`` / numeric spellings.
    """

    def test_static_response_helper_forbidden_passes(self):
        src = """\
<?php
class C {
    /**
     * @NoAdminRequired
     */
    public function act(string $id) {
        if ($this->request->getParam('userId') !== $this->userId) {
            return ResponseHelper::forbidden(message: 'nope');
        }
        return $this->svc->get($id);
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_instance_response_helper_unauthorized_from_authentication_is_FLAGGED(self):
        """INVERTED by `.github#365`. This test used to assert `[]`.

        `->unauthorized(` is the third spelling of the same defect — `#365`
        names `UNAUTHORIZED` and `401`, and the helper-call form was accepting
        the identical authentication clause. The response-helper SPELLING
        parity that this class exists to test is unaffected: see the sibling
        test, where `->unauthorized()` behind a per-object comparison still
        clears.
        """
        src = """\
<?php
class C {
    /**
     * @NoAdminRequired
     */
    public function act(string $id) {
        if ($this->userId === null) {
            return $this->responses->unauthorized();
        }
        return $this->svc->get($id);
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1)
        self.assertIn("act", findings[0])

    def test_instance_response_helper_unauthorized_after_a_real_check_passes(self):
        """Same helper call, same spelling — a per-object condition clears it."""
        src = """\
<?php
class C {
    /**
     * @NoAdminRequired
     */
    public function act(string $id) {
        $item = $this->svc->get($id);
        if ($item['ownerId'] !== $this->userId) {
            return $this->responses->unauthorized();
        }
        return $item;
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_forbidden_substring_is_not_a_false_guard(self):
        """``forbiddenWords(`` must NOT be mistaken for a deny response.

        Guards against the classic substring-match bug: the name must be
        followed by the call parenthesis, not merely start with 'forbidden'.
        """
        src = """\
<?php
class C {
    /**
     * @NoAdminRequired
     */
    public function act(string $id) {
        $bad = $this->filter->forbiddenWords($id);
        return $this->svc->get($id);
    }
}
"""
        out = _scan(src)
        self.assertEqual(len(out), 1)
        self.assertIn("method=act", out[0])


# ---------------------------------------------------------------------------
# Pattern 3 — session-scoped endpoint with no caller-supplied reference
# ---------------------------------------------------------------------------

class SessionScopedNoReferenceTest(unittest.TestCase):
    """Zero params + no request reads + session identity => not an IDOR vector.

    The adversarial cases below are the important half: each one removes a
    single condition and asserts the method is STILL flagged, so the pattern
    cannot be used to smuggle a real IDOR past the gate.
    """

    def test_zero_param_session_scoped_method_passes(self):
        """The canonical safe shape (cf. AcknowledgementController::pending)."""
        src = """\
<?php
class C {
    /**
     * @NoAdminRequired
     */
    public function pending() {
        return $this->svc->getPending(userId: $this->userId);
    }
}
"""
        self.assertEqual(_scan(src), [])

    def test_method_with_id_parameter_still_flagged(self):
        """A bound route parameter IS a direct object reference — must flag."""
        src = """\
<?php
class C {
    /**
     * @NoAdminRequired
     */
    public function show(int $id) {
        return $this->svc->find($id);
    }
}
"""
        out = _scan(src)
        self.assertEqual(len(out), 1)
        self.assertIn("method=show", out[0])

    def test_zero_params_but_reads_request_param_still_flagged(self):
        """Reading an id from the request is equally attacker-controlled."""
        src = """\
<?php
class C {
    /**
     * @NoAdminRequired
     */
    public function show() {
        $id = $this->request->getParam('id');
        return $this->svc->find($id);
    }
}
"""
        out = _scan(src)
        self.assertEqual(len(out), 1)
        self.assertIn("method=show", out[0])

    def test_zero_params_reading_superglobal_still_flagged(self):
        """$_GET is caller-controlled input just as much as getParam()."""
        src = """\
<?php
class C {
    /**
     * @NoAdminRequired
     */
    public function show() {
        return $this->svc->find($_GET['id']);
    }
}
"""
        out = _scan(src)
        self.assertEqual(len(out), 1)
        self.assertIn("method=show", out[0])

    def test_zero_params_without_session_identity_still_flagged(self):
        """No session scoping => no positive evidence it is self-scoped."""
        src = """\
<?php
class C {
    /**
     * @NoAdminRequired
     */
    public function listEverything() {
        return $this->svc->findAll();
    }
}
"""
        out = _scan(src)
        self.assertEqual(len(out), 1)
        self.assertIn("method=listEverything", out[0])

    def test_session_identity_does_not_launder_a_request_supplied_id(self):
        """The dangerous combination: session identity present but an id is
        still taken from the request and used unchecked. Must stay flagged."""
        src = """\
<?php
class C {
    /**
     * @NoAdminRequired
     */
    public function show() {
        $me = $this->userId;
        $id = $this->request->getParam('dossierId');
        return $this->svc->find($id);
    }
}
"""
        out = _scan(src)
        self.assertEqual(len(out), 1)
        self.assertIn("method=show", out[0])

    def test_unparseable_signature_fails_closed(self):
        """When the parameter list cannot be read, do not clear the method."""
        self.assertFalse(cni._is_session_scoped_no_reference(None, "$this->userId"))

    def test_helper_requires_all_three_conditions(self):
        # zero params + session identity, no request read -> clear
        self.assertTrue(cni._is_session_scoped_no_reference("", "$this->userId"))
        # params present -> not clear
        self.assertFalse(cni._is_session_scoped_no_reference("int $id", "$this->userId"))
        # request read present -> not clear
        self.assertFalse(
            cni._is_session_scoped_no_reference("", "$this->request->getParam('id')")
        )
        # no session identity -> not clear
        self.assertFalse(cni._is_session_scoped_no_reference("", "$this->svc->findAll()"))

    def test_default_valued_params_with_parens_are_not_zero_params(self):
        """Brace-aware parsing: a default value containing '(' must not make
        the parameter list look empty."""
        src = """\
<?php
class C {
    /**
     * @NoAdminRequired
     */
    public function show(int $id = 0, array $opts = ['a' => (1 + 2)]) {
        $me = $this->userId;
        return $this->svc->find($id);
    }
}
"""
        out = _scan(src)
        self.assertEqual(len(out), 1)
        self.assertIn("method=show", out[0])


# ---------------------------------------------------------------------------
# Pattern 4 — delegation chains and collaborator-hosted guards
# ---------------------------------------------------------------------------

def _scan_app(controller_src: str, collaborators: dict) -> list[str]:
    """Scan a controller inside a throwaway app tree with real collaborators.

    Pattern 4 resolves a typed property to a *file* under the app's ``lib/``
    tree and reads that file, so these tests must lay out a real directory:

        <root>/lib/Controller/TestController.php
        <root>/lib/Service/<Name>.php

    *collaborators* maps ``ClassName -> php source``.
    """
    with tempfile.TemporaryDirectory() as root:
        ctl_dir = Path(root) / "lib" / "Controller"
        svc_dir = Path(root) / "lib" / "Service"
        ctl_dir.mkdir(parents=True)
        svc_dir.mkdir(parents=True)
        for name, body in collaborators.items():
            (svc_dir / f"{name}.php").write_text(body, encoding="utf-8")
        ctl = ctl_dir / "TestController.php"
        ctl.write_text(controller_src, encoding="utf-8")
        # Pattern 4 caches per-root and per-file; a temp dir is unique per test
        # but clear anyway so a reused inode can never leak a stale answer.
        cni._CLASS_INDEX_CACHE.clear()
        cni._COLLABORATOR_GUARD_CACHE.clear()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cni.scan_file(str(ctl))
        cni._CLASS_INDEX_CACHE.clear()
        cni._COLLABORATOR_GUARD_CACHE.clear()
    return [ln for ln in buf.getvalue().splitlines() if ln.strip()]


# The decidesk responder, reduced to the shape that matters: staffAction()
# delegates to requireStaff() which denies with 401/403; citizenAction()
# denies an anonymous caller with 401; respond() is NOT a guard — it only maps
# a result or an exception onto a JSONResponse.
_RESPONDER = """\
<?php
namespace OCA\\Decidesk\\Service;

class ParticipationResponder {
    public function staffAction(callable $operation, ?string $key = null, int $status = 200) {
        return ($this->requireStaff() ?? $this->respond($operation, $key, $status));
    }

    public function citizenAction(callable $operation, ?string $key = null, int $status = 200) {
        $uid = $this->staffGuard->currentUid();
        if ($uid === null) {
            return new JSONResponse(['message' => 'Unauthorized'], Http::STATUS_UNAUTHORIZED);
        }
        return $this->respond($operation, $key, $status);
    }

    private function requireStaff() {
        if ($this->staffGuard->currentUid() === null) {
            return new JSONResponse(['message' => 'Unauthorized'], Http::STATUS_UNAUTHORIZED);
        }
        if ($this->staffGuard->isStaff() === false) {
            return new JSONResponse(['message' => 'Forbidden'], Http::STATUS_FORBIDDEN);
        }
        return null;
    }

    private function respond(callable $operation, ?string $key, int $status) {
        return new JSONResponse([$key => $operation()], $status);
    }
}
"""


class CollaboratorGuardDelegationTest(unittest.TestCase):
    """Pattern 4a — a guard reached through an injected collaborator.

    Regression cover for the decidesk measurement of 2026-08-04: gate-7
    reported 11 findings on ParticipationController /
    ParticipationBudgetController and every one was guarded, because the
    guard lives on ``$this->responder`` rather than in the method body.
    """

    def test_staffAction_delegation_is_recognised_as_guarded(self):
        """$this->responder->staffAction() reaches requireStaff() -> not flagged."""
        src = """\
<?php
namespace OCA\\Decidesk\\Controller;

class TestController {
    public function __construct(
        private readonly ParticipationResponder $responder,
    ) {
    }

    /**
     * @NoAdminRequired
     */
    public function transitionBudgetRound(string $budgetId, string $status) {
        return $this->responder->staffAction(
            operation: fn (): array => $this->lifecycleService->transitionBudgetRound($budgetId, $status),
            key: 'budgetRound'
        );
    }
}
"""
        self.assertEqual(_scan_app(src, {"ParticipationResponder": _RESPONDER}), [])

    def test_citizenAction_delegation_is_FLAGGED_it_only_authenticates(self):
        """INVERTED by `.github#365`. This test used to assert `[]`.

        It is the decidesk measurement's own counter-example, and the sharpest
        statement of the defect available: `staffAction()` and `citizenAction()`
        sit side by side in one collaborator, and only ONE of them is an
        authorisation guard.

            requireStaff()   currentUid() === null -> 401   (authentication)
                             isStaff()     === false -> 403 (AUTHORISATION)
            citizenAction()  currentUid() === null -> 401   (authentication)
                             ...and nothing else.

        `staffAction()` still clears — its 403 arm survives the blanking, and
        the sibling test above pins that. `citizenAction()` clears nothing: a
        caller routed through it may submit a proposal against ANY budgetId,
        which is the finding. The 401 arm was never doing the work; it was
        borrowing credibility from the 403 arm next door.
        """
        src = """\
<?php
namespace OCA\\Decidesk\\Controller;

class TestController {
    public function __construct(
        private readonly ParticipationResponder $responder,
    ) {
    }

    /**
     * @NoAdminRequired
     */
    public function submitProposal(string $budgetId, string $title = '') {
        return $this->responder->citizenAction(
            operation: fn (string $uid): array => $this->budgetService->submitProposal($budgetId, $title, $uid),
            key: 'proposal'
        );
    }
}
"""
        findings = _scan_app(src, {"ParticipationResponder": _RESPONDER})
        self.assertEqual(len(findings), 1)
        self.assertIn("submitProposal", findings[0])

    def test_three_hop_intra_class_chain_to_collaborator_guard(self):
        """validateProposal -> approve/reject -> applyDecision -> staffAction().

        The exact decidesk shape that needed three hops. Transitive closure
        must follow it all the way to the collaborator guard.
        """
        src = """\
<?php
namespace OCA\\Decidesk\\Controller;

class TestController {
    public function __construct(
        private readonly ParticipationResponder $responder,
    ) {
    }

    /**
     * @NoAdminRequired
     */
    public function validateProposal(string $proposalId, ?bool $approve = null) {
        if ($approve === false) {
            return $this->rejectProposal(proposalId: $proposalId);
        }
        return $this->approveProposal(proposalId: $proposalId);
    }

    private function approveProposal(string $proposalId) {
        return $this->applyProposalDecision(proposalId: $proposalId, approve: true);
    }

    private function rejectProposal(string $proposalId) {
        return $this->applyProposalDecision(proposalId: $proposalId, approve: false);
    }

    private function applyProposalDecision(string $proposalId, bool $approve) {
        return $this->responder->staffAction(
            operation: fn (): array => $this->budgetService->validateProposal($proposalId, $approve),
            key: 'proposal'
        );
    }
}
"""
        self.assertEqual(_scan_app(src, {"ParticipationResponder": _RESPONDER}), [])


class CollaboratorGuardStillCatchesRealIdorTest(unittest.TestCase):
    """Pattern 4 must not become a blanket clear — the negative direction.

    Every test here is a shape the gate MUST still flag. Without these, the
    Pattern 4 clear is only evidence about itself: a delegation-following
    gate that follows delegation to *anything* has stopped gating.
    """

    def test_plain_unguarded_method_still_flagged(self):
        """No responder, no helper, no guard, caller-supplied id -> flagged."""
        src = """\
<?php
namespace OCA\\Decidesk\\Controller;

class TestController {
    public function __construct(
        private readonly ParticipationResponder $responder,
    ) {
    }

    /**
     * @NoAdminRequired
     */
    public function deleteReaction(string $reactionId) {
        $this->consultationService->deleteReaction($reactionId);
        return new JSONResponse(['ok' => true]);
    }
}
"""
        out = _scan_app(src, {"ParticipationResponder": _RESPONDER})
        self.assertEqual(len(out), 1)
        self.assertIn("method=deleteReaction", out[0])

    def test_collaborator_method_that_is_not_a_guard_still_flagged(self):
        """respond() EXISTS on the responder but performs no authorisation.

        The sharpest control: resolution must discriminate between methods of
        the collaborator, not clear anything called on a property whose class
        happens to contain a guard somewhere.
        """
        src = """\
<?php
namespace OCA\\Decidesk\\Controller;

class TestController {
    public function __construct(
        private readonly ParticipationResponder $responder,
    ) {
    }

    /**
     * @NoAdminRequired
     */
    public function deleteReaction(string $reactionId) {
        return $this->responder->respond(
            fn (): array => $this->consultationService->deleteReaction($reactionId),
            'reaction',
            200
        );
    }
}
"""
        out = _scan_app(src, {"ParticipationResponder": _RESPONDER})
        self.assertEqual(len(out), 1)
        self.assertIn("method=deleteReaction", out[0])

    def test_unresolvable_collaborator_class_clears_nothing(self):
        """A type with no file under lib/ must fail closed, not fail open."""
        src = """\
<?php
namespace OCA\\Decidesk\\Controller;

class TestController {
    public function __construct(
        private readonly MysteryResponder $responder,
    ) {
    }

    /**
     * @NoAdminRequired
     */
    public function deleteReaction(string $reactionId) {
        return $this->responder->staffAction(
            fn (): array => $this->consultationService->deleteReaction($reactionId)
        );
    }
}
"""
        out = _scan_app(src, {})
        self.assertEqual(len(out), 1)
        self.assertIn("method=deleteReaction", out[0])

    def test_intra_class_chain_ending_in_no_guard_still_flagged(self):
        """A three-hop chain whose terminal method has no guard at all."""
        src = """\
<?php
namespace OCA\\Decidesk\\Controller;

class TestController {
    public function __construct(
        private readonly ParticipationResponder $responder,
    ) {
    }

    /**
     * @NoAdminRequired
     */
    public function deleteReaction(string $reactionId) {
        return $this->hopOne(reactionId: $reactionId);
    }

    private function hopOne(string $reactionId) {
        return $this->hopTwo(reactionId: $reactionId);
    }

    private function hopTwo(string $reactionId) {
        $this->consultationService->deleteReaction($reactionId);
        return new JSONResponse(['ok' => true]);
    }
}
"""
        out = _scan_app(src, {"ParticipationResponder": _RESPONDER})
        self.assertEqual(len(out), 1)
        self.assertIn("method=deleteReaction", out[0])

    def test_collaborator_guard_after_the_write_still_flagged(self):
        """The guard must run BEFORE the mutation or it protects nothing."""
        src = """\
<?php
namespace OCA\\Decidesk\\Controller;

class TestController {
    public function __construct(
        private readonly ParticipationResponder $responder,
    ) {
    }

    /**
     * @NoAdminRequired
     */
    public function deleteReaction(string $reactionId) {
        $this->consultationService->deleteReaction($reactionId);
        return $this->responder->staffAction(fn (): array => []);
    }
}
"""
        out = _scan_app(src, {"ParticipationResponder": _RESPONDER})
        self.assertEqual(len(out), 1)
        self.assertIn("method=deleteReaction", out[0])

    def test_bare_throw_does_not_seed_a_delegation_chain(self):
        """A collaborator method that only throws NotFoundException is not a guard.

        `throw` is accepted by the one-hop Pattern-1 helper rule; propagation
        deliberately requires a STRICTER signal, so "this can fail" never
        becomes "this checks who you are" further up the chain.
        """
        thrower = """\
<?php
namespace OCA\\Decidesk\\Service;

class ThingLoader {
    public function load(string $id) {
        if ($id === '') {
            throw new NotFoundException('missing');
        }
        return $this->mapper->find($id);
    }
}
"""
        src = """\
<?php
namespace OCA\\Decidesk\\Controller;

class TestController {
    public function __construct(
        private readonly ThingLoader $loader,
    ) {
    }

    /**
     * @NoAdminRequired
     */
    public function showThing(string $thingId) {
        return new JSONResponse($this->loader->load($thingId));
    }
}
"""
        out = _scan_app(src, {"ThingLoader": thrower})
        self.assertEqual(len(out), 1)
        self.assertIn("method=showThing", out[0])


# ---------------------------------------------------------------------------
# Pattern 5 — the TENANCY guard (ConductionNL/.github#160)
#
# gate-7 was ANTI-CORRELATED with the property it checks on a multi-tenant
# codebase: it stayed red on the correct fix and would have gone green if the
# code were made to leak. The fixtures below are OpenRegister's real shapes.
#
# Both ways, in the same class: the tenancy-scoped service must clear its
# caller, and a service that loads by client-supplied id with NO tenancy
# comparison must still be flagged.
# ---------------------------------------------------------------------------

# The exact shape from OpenRegister's FlowService, comment and all. A flow the
# caller may not see raises the SAME exception as one that does not exist.
_FLOW_SERVICE = """<?php
namespace OCA\\\\OpenRegister\\\\Service;

class FlowService
{
    /**
     * A flow the caller may not see raises the SAME exception as a flow that
     * does not exist. Distinguishing them would turn every read into an
     * oracle for enumerating other tenants' flow ids.
     */
    public function find(string $uuid): Flow
    {
        $flow = $this->mapper->findByUuid($uuid);
        if ($flow->belongsTo($this->activeOrganisation()) === false) {
            throw new DoesNotExistException('No such flow');
        }
        return $flow;
    }

    public function findAll(): array
    {
        $org = $this->activeOrganisation();
        if ($org === null) {
            return [];
        }
        return $this->mapper->findAllForOrganisation($org);
    }
}
"""

# Same surface, NO tenancy comparison: the client-supplied uuid goes straight
# to an unscoped mapper. This is what FlowController::state() actually did
# before it was fixed.
_UNSCOPED_SERVICE = """<?php
namespace OCA\\\\OpenRegister\\\\Service;

class FlowService
{
    public function find(string $uuid): Flow
    {
        return $this->mapper->findByUuid($uuid);
    }

    public function findAll(): array
    {
        return $this->mapper->findAll();
    }
}
"""

_FLOW_CONTROLLER = """<?php
namespace OCA\\\\OpenRegister\\\\Controller;

class TestController extends Controller
{
    private FlowService $flows;

    /**
     * @NoAdminRequired
     */
    public function state(string $uuid) {
        return new JSONResponse($this->flows->find($uuid)->getState());
    }
}
"""


class TenancyGuardTest(unittest.TestCase):
    def test_fp_org_scoped_service_clears_its_caller(self):
        # THE demonstration from #160: FlowController::state() was a real
        # IDOR, was fixed by routing through FlowService::find(), and gate-7
        # reported it identically before and after. It must now clear.
        self.assertEqual(_scan_app(_FLOW_CONTROLLER, {"FlowService": _FLOW_SERVICE}), [])

    def test_tp_the_same_controller_over_an_UNSCOPED_service_is_still_flagged(self):
        # The pairing that proves this is not a mute. Identical controller,
        # identical service NAME and signature — only the tenancy comparison
        # differs, and that is the whole property gate-7 exists to measure.
        out = _scan_app(_FLOW_CONTROLLER, {"FlowService": _UNSCOPED_SERVICE})
        self.assertEqual(len(out), 1)
        self.assertIn("method=state", out[0])

    def test_a_tenancy_comparison_with_no_refusal_is_not_a_guard(self):
        self.assertFalse(cni._has_tenancy_guard(
            "$org = $this->activeOrganisation(); $out = $flow->belongsTo($org); return $flow;"))

    def test_a_refusal_with_no_tenancy_comparison_is_not_a_tenancy_guard(self):
        self.assertFalse(cni._has_tenancy_guard(
            "$flow = $this->mapper->findByUuid($uuid); if ($flow === null) { throw new DoesNotExistException(); } return $flow;"))

    def test_both_halves_together_are_a_guard(self):
        self.assertTrue(cni._has_tenancy_guard(
            "if ($flow->belongsTo($this->activeOrganisation()) === false) { throw new DoesNotExistException(); }"))

    def test_silent_narrowing_to_an_empty_list_counts(self):
        self.assertTrue(cni._has_tenancy_guard(
            "$org = $this->activeOrganisation(); if ($org === null) { return []; }"))

    def test_a_mapper_applying_the_organisation_filter_counts(self):
        self.assertTrue(cni._has_tenancy_guard(
            "$qb = $this->applyOrganisationFilter($qb); if ($rows === []) { return []; }"))

    def test_a_plain_getter_named_getOrganisation_is_not_a_scope_signal(self):
        # `->getOrganisation()` is an ordinary accessor all over the fleet.
        # Only the ACTIVE/CURRENT forms are session-derived, and only a
        # session-derived value makes the comparison an authorisation check.
        self.assertFalse(cni._has_tenancy_guard(
            "$org = $entity->getOrganisation(); if ($org === null) { throw new DoesNotExistException(); }"))


class FullyQualifiedAttributeIsStillTheAttribute(unittest.TestCase):
    """`#[\\OCP\\AppFramework\\Http\\Attribute\\NoAdminRequired]` puts the method IN scope.

    Measured 2026-08-08. The look-back matched `#[NoAdminRequired` only — the
    imported short form. PHP equally permits the fully-qualified spelling, and
    with it a textbook IDOR (caller-supplied `$id`, no ownership check) fell out
    of scope entirely and the gate reported PASS. The byte-identical body under
    the short form reported FAIL.

    No fleet file uses the FQ form today, which is exactly why this needed
    closing deliberately: a false NEGATIVE on a security gate leaves no log, so
    the first FQ attribute anyone writes would have switched the gate off for
    that method silently.
    """

    _LEAK = """<?php
namespace OCA\\Fx\\Controller;
class C extends Controller {
    %s
    public function fetch(string $id): JSONResponse
    {
        $obj = $this->objectService->find(id: $id);
        return new JSONResponse(data: $obj);
    }
}
"""

    _GUARDED = """<?php
namespace OCA\\Fx\\Controller;
class C extends Controller {
    %s
    public function fetch(string $id): JSONResponse
    {
        $obj = $this->objectService->find(id: $id);
        if ($obj->getOwner() !== $this->userSession->getUser()->getUID()) {
            return new JSONResponse(data: [], statusCode: Http::STATUS_FORBIDDEN);
        }

        return new JSONResponse(data: $obj);
    }
}
"""

    def _scan(self, php: str) -> list[str]:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "C.php"
            p.write_text(php, encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                cni.scan_file(str(p))
        return [ln for ln in buf.getvalue().splitlines() if ln.strip()]

    def test_short_form_leak_is_reported(self):
        self.assertEqual(len(self._scan(self._LEAK % "#[NoAdminRequired]")), 1)

    def test_fully_qualified_leak_is_reported(self):
        php = self._LEAK % "#[\\OCP\\AppFramework\\Http\\Attribute\\NoAdminRequired]"
        self.assertEqual(len(self._scan(php)), 1)

    def test_fully_qualified_guarded_method_is_not_reported(self):
        php = self._GUARDED % "#[\\OCP\\AppFramework\\Http\\Attribute\\NoAdminRequired]"
        self.assertEqual(self._scan(php), [])

    def test_short_form_guarded_method_is_not_reported(self):
        self.assertEqual(self._scan(self._GUARDED % "#[NoAdminRequired]"), [])

    def test_an_unannotated_method_stays_out_of_scope(self):
        # Anti-widening: no NoAdminRequired at all means this gate has no say.
        self.assertEqual(self._scan(self._LEAK % ""), [])


class ZeroInputReadOnlyEndpoints(unittest.TestCase):
    """Pattern 3b (.github#297) — a routed method that takes NO parameters and
    reads NOTHING from the request has no direct object reference for an
    attacker to substitute, so IDOR is structurally impossible. Every
    authenticated caller gets a byte-identical response.

    Before this, the only way to close such a finding was
    `@no-admin-idor-exempt <reason>` — and a reason-tag on a finding that was
    never real is indistinguishable, six months later, from a reason-tag on one
    that was. nldesign left the gate red rather than tag it.

    THE RELAXATION IS BOUNDED TO READS. `_MUTATION_CALL_RE` keeps a zero-input
    side effect reportable, because "the caller names no object" is not a
    reason to let an unguarded `purgeAll()` through — that is the shape this
    argument would otherwise wave past, and it is the abuse control here.
    """

    _TPL = """<?php
class CatalogController {
    #[NoAdminRequired]
    public function %s
}
"""

    def _scan1(self, method_src: str) -> list[str]:
        return _scan(self._TPL % method_src)

    # -- the false positives, gone ----------------------------------------
    def test_fp_a_zero_input_catalogue_read_is_not_an_idor(self):
        # nldesign CatalogController::tokenSets, verbatim.
        self.assertEqual(self._scan1(
            "tokenSets(): JSONResponse\n"
            "    {\n"
            "        return new JSONResponse(['tokenSets' => "
            "$this->tokenSetService->getPublicCatalogue()]);\n"
            "    }"), [])

    def test_fp_a_published_public_key_is_not_an_idor(self):
        # openregister FederatedConfigController::publicKey.
        self.assertEqual(self._scan1(
            "publicKey(): JSONResponse\n"
            "    {\n"
            "        return new JSONResponse(['publicKey' => "
            "$this->service->publicKey()]);\n"
            "    }"), [])

    def test_fp_a_static_event_catalogue_is_not_an_idor(self):
        # openregister FlowController::eventCatalog.
        self.assertEqual(self._scan1(
            "eventCatalog(): JSONResponse\n"
            "    {\n"
            "        $results = $this->eventCatalog->getCatalog();\n"
            "        return new JSONResponse(['results' => $results, "
            "'total' => count($results)]);\n"
            "    }"), [])

    # -- THE ABUSE CONTROL: reads only ------------------------------------
    def test_abuse_control_a_zero_input_MUTATION_is_still_reported(self):
        # No parameters, no request reads — and it deletes everything. If
        # Pattern 3b ever drops its read-only condition, this goes quiet.
        out = self._scan1(
            "purgeAll(): JSONResponse\n"
            "    {\n"
            "        $this->objectService->deleteAll();\n"
            "        return new JSONResponse(['purged' => true]);\n"
            "    }")
        self.assertEqual(len(out), 1, out)
        self.assertIn("method=purgeAll", out[0])

    def test_abuse_control_a_zero_input_reset_is_still_reported(self):
        out = self._scan1(
            "resetSettings(): JSONResponse\n"
            "    {\n"
            "        $this->settingsService->resetToDefaults();\n"
            "        return new JSONResponse(['ok' => true]);\n"
            "    }")
        self.assertEqual(len(out), 1, out)
        self.assertIn("method=resetSettings", out[0])

    # -- THE ABUSE CONTROL THAT CAUGHT THE FIRST DRAFT --------------------
    # Pattern 3b's first draft cleared any zero-input READ. These two shapes
    # are why that was wrong, and six existing tests failed on it. They are
    # restated here so the reason travels with the pattern rather than living
    # only in the classes that happened to use them as fixtures.
    def test_abuse_control_a_zero_input_findAll_is_still_reported(self):
        out = self._scan1(
            "listEverything(): JSONResponse\n"
            "    {\n"
            "        return new JSONResponse($this->svc->findAll());\n"
            "    }")
        self.assertEqual(len(out), 1, out)
        self.assertIn("method=listEverything", out[0])

    def test_abuse_control_a_zero_input_mapper_read_is_still_reported(self):
        out = self._scan1(
            "index(): JSONResponse\n"
            "    {\n"
            "        $data = $this->mapper->findAll();\n"
            "        return new JSONResponse($data);\n"
            "    }")
        self.assertEqual(len(out), 1, out)
        self.assertIn("method=index", out[0])

    # -- THE TRUE POSITIVES THIS MUST NOT SWALLOW -------------------------
    def test_tp_a_method_taking_an_id_is_still_reported(self):
        # The moment the caller names an object, IDOR is possible again.
        out = self._scan1(
            "show(string $id): JSONResponse\n"
            "    {\n"
            "        return new JSONResponse($this->service->find($id));\n"
            "    }")
        self.assertEqual(len(out), 1, out)
        self.assertIn("method=show", out[0])

    def test_tp_a_zero_param_method_that_READS_THE_REQUEST_is_still_reported(self):
        # Zero declared parameters is not the same as zero caller input —
        # `getParam` is the other door, and it is exactly what IDOR walks in
        # through.
        out = self._scan1(
            "show(): JSONResponse\n"
            "    {\n"
            "        $id = $this->request->getParam('id');\n"
            "        return new JSONResponse($this->service->find($id));\n"
            "    }")
        self.assertEqual(len(out), 1, out)
        self.assertIn("method=show", out[0])


class VerbObjectGuardHelperNames(unittest.TestCase):
    """A guard helper may spell its object noun AFTER the auth token.

    ``_GUARD_HELPER_NAME_RE``'s first alternative used to require the auth
    token (``Access``/``Permission``/``Owner``/…) to be the FINAL CamelCase
    segment, so ``canAccess`` matched but ``canUserAccessAgent`` did not. That
    rejected the very common verb-object spelling and made gate-7 blind to
    genuine authorisation predicates, reporting every method that delegates to
    one as an unguarded IDOR.

    MEASURED: ConductionNL/hermiq @ development (cd23f547), full-scope run
    31490144919 / job 93776678440 — gate-7 FAIL, 3 methods, all three false
    positives of exactly the two shapes below. Gate-7 was proven NOT blind on
    that repo first: a textbook IDOR planted into the TRACKED file
    ``lib/Controller/AgentVersionController.php`` took the count 3 → 4.

    AN AUTH TOKEN IS STILL REQUIRED — only its POSITION is relaxed. The
    negative controls at the bottom are the abuse control: ``canRender`` /
    ``hasChanges`` carry no auth token in ANY position and must still be
    reported. The unguarded-fetch positive control for this shape already
    exists twice and is deliberately not duplicated here:
    ``RealIdorViolationTest.test_no_guard_at_all_is_flagged`` (docblock form)
    and ``ZeroInputReadOnlyEndpoints.test_tp_a_method_taking_an_id_is_still_reported``
    (attribute form).
    """

    # -- SHAPE A: in-body per-object filter through a verb-object predicate --
    #
    # NOTE ON THE FIXTURE. The pagination read (``$this->request->getParams()``)
    # is load-bearing, not decoration: without it the method takes no caller
    # input at all and the session-scoped / zero-reference exemption clears it
    # before the guard-helper pattern is ever consulted — the first draft of
    # this test passed identically with the OLD regex for that reason. The real
    # hermiq method reads pagination params, so the reference is real and the
    # only thing standing between it and a finding is the helper's NAME. The
    # two abuse controls below pin that: drop the helper, or rename it to a
    # name with no auth token, and the finding comes back.
    _SHAPE_A = """\
<?php
class AgentsController {
    #[NoAdminRequired]
    #[NoCSRFRequired]
    public function index(): JSONResponse
    {
        $userId = (string) $this->userSession->getUser()?->getUID();
        $params = $this->request->getParams();
        $limit  = (int) ($params['_limit'] ?? 50);
        $offset = (int) ($params['_offset'] ?? 0);

        $agents = $this->objectService->findAll(
            config: ['limit' => $limit, 'offset' => $offset]
        );

        $results = [];
        foreach ($agents as $agent) {
            if ($this->%s(agent: $agent, userId: $userId) === true) {
                $results[] = $agent->getObject();
            }
        }

        return new JSONResponse(data: ['results' => $results]);
    }
%s
}
"""

    _SHAPE_A_HELPER = """
    private function %s(ObjectEntity $agent, string $userId): bool
    {
        $data = $agent->getObject();
        if (($data['isPrivate'] ?? null) === false) {
            return true;
        }
        if ($agent->getOwner() === $userId) {
            return true;
        }
        return in_array($userId, ($data['invitedUsers'] ?? []), true);
    }
"""

    def test_in_body_verb_object_predicate_clears_caller(self):
        """hermiq AgentsController::index — every result filtered in-body."""
        src = self._SHAPE_A % (
            "canUserAccessAgent",
            self._SHAPE_A_HELPER % "canUserAccessAgent",
        )
        self.assertEqual(_scan(src), [])

    def test_shape_a_without_the_helper_is_still_reported(self):
        """Abuse control: the same body with NO helper defined stays a finding."""
        findings = _scan(self._SHAPE_A % ("canUserAccessAgent", ""))
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("method=index", findings[0])

    def test_shape_a_with_a_tokenless_helper_name_is_still_reported(self):
        """Abuse control: rename the helper to a name carrying no auth token
        and the finding returns — the NAME is what clears it, nothing else."""
        findings = _scan(
            self._SHAPE_A
            % ("canRenderAgent", self._SHAPE_A_HELPER % "canRenderAgent")
        )
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("method=index", findings[0])

    # -- SHAPE B: Pattern-4 transitive closure through a loader --------------
    def test_loader_delegating_to_verb_object_predicate_clears_caller(self):
        """hermiq AgentVersionController::index / ::diff — routed method →
        ``loadAccessibleAgent()`` → ``canUserAccessAgent()``, caller returns
        ``Http::STATUS_NOT_FOUND`` on null (the 404-style tenancy refusal this
        gate's own FAIL message endorses). Exercises the transitive closure:
        the loader itself has no auth token in its name and no strict deny
        signal in its body — it is guard-bearing only because it CALLS one.
        """
        src = """\
<?php
class AgentVersionController {
    #[NoAdminRequired]
    #[NoCSRFRequired]
    public function index(string $id): JSONResponse
    {
        $userId = (string) $this->userSession->getUser()?->getUID();

        $agent = $this->loadAccessibleAgent(id: $id, userId: $userId);
        if ($agent === null) {
            return new JSONResponse(['error' => 'Agent not found'], Http::STATUS_NOT_FOUND);
        }

        $versions = $this->agentVersionService->listVersions(agentUuid: $id);
        return new JSONResponse(['results' => $versions, 'total' => count($versions)]);
    }

    #[NoAdminRequired]
    #[NoCSRFRequired]
    public function diff(string $id): JSONResponse
    {
        $userId = (string) $this->userSession->getUser()?->getUID();

        $agent = $this->loadAccessibleAgent(id: $id, userId: $userId);
        if ($agent === null) {
            return new JSONResponse(['error' => 'Agent not found'], Http::STATUS_NOT_FOUND);
        }

        $from = (string) $this->request->getParam('from', '');
        $to   = (string) $this->request->getParam('to', '');
        return new JSONResponse($this->agentVersionService->diff($id, $from, $to));
    }

    private function loadAccessibleAgent(string $id, string $userId): ?ObjectEntity
    {
        $agent = $this->objectService->find(id: $id);
        if (($agent instanceof ObjectEntity) === false) {
            return null;
        }

        if ($this->canUserAccessAgent(agent: $agent, userId: $userId) === false) {
            return null;
        }

        return $agent;
    }

    private function canUserAccessAgent(ObjectEntity $agent, string $userId): bool
    {
        $data = $agent->getObject();
        if (($data['isPrivate'] ?? null) === false) {
            return true;
        }
        if ($agent->getOwner() === $userId) {
            return true;
        }
        return in_array($userId, ($data['invitedUsers'] ?? []), true);
    }
}
"""
        self.assertEqual(_scan(src), [])

    # -- NEGATIVE CONTROLS: no auth token in ANY position -------------------
    def test_canRender_helper_does_not_clear_caller(self):
        """``canRender`` has the can- prefix but no auth token — still flagged."""
        src = """\
<?php
class WidgetController {
    #[NoAdminRequired]
    public function show(string $id): JSONResponse
    {
        $widget = $this->objectService->find($id);
        if ($this->canRender($widget) === false) {
            return new JSONResponse(['results' => []]);
        }
        return new JSONResponse($widget);
    }

    private function canRender(ObjectEntity $widget): bool
    {
        return ($widget->getObject()['template'] ?? null) !== null;
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("method=show", findings[0])

    def test_hasChanges_helper_does_not_clear_caller(self):
        """``hasChanges`` has the has- prefix but no auth token — still flagged."""
        src = """\
<?php
class DraftController {
    #[NoAdminRequired]
    public function update(string $id): JSONResponse
    {
        $draft = $this->objectService->find($id);
        if ($this->hasChanges($draft) === true) {
            $this->objectService->saveObject($draft);
        }
        return new JSONResponse($draft);
    }

    private function hasChanges(ObjectEntity $draft): bool
    {
        return $draft->getUpdated() > $draft->getCreated();
    }
}
"""
        findings = _scan(src)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("method=update", findings[0])

    def test_verb_object_name_without_an_auth_token_is_not_a_guard_name(self):
        """The regex itself: a token is REQUIRED, only its position is free."""
        matches = cni._GUARD_HELPER_NAME_RE.match
        # Auth token in a trailing-object position — now accepted.
        self.assertTrue(matches("canUserAccessAgent"))
        self.assertTrue(matches("hasOwnerPermissionForRun"))
        self.assertTrue(matches("mayUserAdminTenant"))
        # No auth token anywhere — still rejected.
        self.assertFalse(matches("canRender"))
        self.assertFalse(matches("hasChanges"))
        self.assertFalse(matches("canUserModifyAgent"))
        self.assertFalse(matches("hasPendingRevision"))

    def test_the_auth_token_may_be_the_first_segment(self):
        """`.github#360` — the SHORT idiomatic guard names.

        `#353` relaxed WHERE the auth token may sit but left the segment
        before it mandatory, so the token could never come first.  The most
        conventional per-object guard names in the fleet are exactly that
        shape, and gate-7 reported every method delegating to one as an
        unguarded IDOR — before AND after `#353`.  Measured end-to-end in
        `test_gate7_verb_object_guards.sh`: a controller guarded by
        `hasPermission()` and `canAccess()` produced 2 findings, and produces
        0 now, while the same fixture still goes red under the pre-#360 regex.
        """
        matches = cni._GUARD_HELPER_NAME_RE.match
        for name in (
            "hasPermission", "canAccess", "isOwner", "isAllowed",
            "mayAccess", "hasAccess", "isPermitted", "canAccessAgentForUser",
        ):
            self.assertTrue(matches(name), f"{name} should be a guard name")

    def test_360_did_not_widen_into_silence(self):
        """The abuse control for `#360`: no token, no guard.

        Making the pre-token segment optional must not turn the pattern into
        "any is/has/can/may method".  If it had, gate-7 would clear real
        IDORs — the failure mode that is strictly worse than the false
        positives `#360` removes.
        """
        matches = cni._GUARD_HELPER_NAME_RE.match
        for name in (
            "canRender", "hasChanges", "isVisible", "canDelete", "hasItems",
            "isReady", "mayRetry", "canUserModifyAgent", "hasPendingRevision",
        ):
            self.assertFalse(matches(name), f"{name} must NOT be a guard name")


# ---------------------------------------------------------------------------
# `.github#365` — AUTHENTICATION IS NOT AUTHORISATION
# ---------------------------------------------------------------------------

_IDOR_BODY = """\
        $entry = $this->ledger->find($entryId);
        return new JSONResponse($entry);
"""


def _method(preamble: str, body: str = _IDOR_BODY) -> str:
    """One `@NoAdminRequired` method: *preamble*, then a fixed IDOR body.

    Every arm below shares `_IDOR_BODY` verbatim, so a verdict difference
    between two arms can only be explained by the preamble. That is what makes
    these a control rather than a collection of samples.
    """
    return (
        "<?php\nclass LedgerController {\n"
        "    /**\n     * @NoAdminRequired\n     */\n"
        "    public function show(string $entryId): JSONResponse\n    {\n"
        + preamble + body + "    }\n}\n"
    )


class AuthenticationIsNotAuthorisationTest(unittest.TestCase):
    """The `#365` three-arm control, at the level of one method body.

    Measured on a committed-plant rig before the fix (canonical package
    @ 57bcb2b): the bare arm reported 1, the byte-identical arm behind a
    `no user -> 401` preamble reported 0, and gate-7 reported 0 in all
    EIGHTEEN fleet apps while 453 of 791 controller files carried that
    preamble.
    """

    def test_arm_1_bare_is_flagged(self):
        """The positive control. If this stops firing, nothing else here means anything."""
        findings = _scan(_method(""))
        self.assertEqual(len(findings), 1)

    def test_arm_2_authentication_preamble_is_flagged(self):
        """THE DEFECT: identical body, a 401 preamble, and the gate went quiet."""
        findings = _scan(_method(
            "        $user = $this->userSession->getUser();\n"
            "        if ($user === null) {\n"
            "            return new JSONResponse([], Http::STATUS_UNAUTHORIZED);\n"
            "        }\n"
        ))
        self.assertEqual(len(findings), 1)

    def test_arm_3_real_guard_after_the_same_preamble_passes(self):
        """The abuse control: the preamble is IGNORED, not PUNISHED."""
        self.assertEqual(_scan(_method(
            "        $user = $this->userSession->getUser();\n"
            "        if ($user === null) {\n"
            "            return new JSONResponse([], Http::STATUS_UNAUTHORIZED);\n"
            "        }\n"
            "        $e = $this->ledger->find($entryId);\n"
            "        if ($e['ownerId'] !== $user->getUID()) {\n"
            "            return new JSONResponse([], Http::STATUS_FORBIDDEN);\n"
            "        }\n"
        )), [])

    def test_every_authentication_spelling_is_demoted(self):
        """Spelling-agnostic by construction — see the doriath retraction.

        `#365`'s own re-audit enumerated three spellings of "who is the
        caller", missed `sessionUserId()`, and manufactured 19 false positives
        from that one gap. Identity is recognised by TOKEN in an
        argument-free expression, so a resolver nobody has thought of yet is
        still recognised.
        """
        for preamble in (
            "        if ($this->userSession->getUser() === null) { return new JSONResponse([], 401); }\n",
            "        $uid = $this->sessionUserId();\n        if ($uid === null) { return new JSONResponse([], 401); }\n",
            "        $u = $this->userSession->getUser();\n        if ($u === null) { return new JSONResponse([], 401); }\n",
            "        if (empty($this->userId)) { return new JSONResponse([], 401); }\n",
            "        if (!$this->userId) { return new JSONResponse([], 401); }\n",
            "        $user = $this->userSession->getUser();\n        if (!$user instanceof IUser) { return new JSONResponse([], 401); }\n",
            "        if ($this->userSession->isLoggedIn() === false) { throw new OCSException('', 401); }\n",
            "        $currentUser = $this->userService->currentUser();\n        if ($currentUser === null) { return $this->responses->unauthorized(); }\n",
        ):
            with self.subTest(preamble=preamble.strip()[:60]):
                self.assertEqual(len(_scan(_method(preamble))), 1)

    def test_a_real_comparison_is_never_demoted(self):
        """The false-positive control, one arm per shape that must survive."""
        for preamble in (
            "        $e = $this->ledger->find($entryId);\n        if ($e['ownerId'] !== $this->userId) { return new JSONResponse([], 401); }\n",
            "        $e = $this->ledger->find($entryId);\n        if ($e['ownerId'] !== $this->userId) { return new JSONResponse([], 404); }\n",
            "        if ($this->isCurrentUserAdmin() === false) { return new JSONResponse([], 403); }\n",
            "        if ($this->hasPermission($entryId) === false) { return new JSONResponse([], 403); }\n",
        ):
            with self.subTest(preamble=preamble.strip()[:60]):
                self.assertEqual(_scan(_method(preamble)), [])

    def test_a_non_refusing_conditional_is_left_alone(self):
        """Control 3 — a clause that computes rather than refuses is not a guard clause.

        It must not be blanked, because blanking a body region is a
        destructive operation on the text every other pattern reads.
        """
        src = _method(
            "        $user = $this->userSession->getUser();\n"
            "        if ($user === null) {\n"
            "            $this->logger->debug('anon');\n"
            "        }\n"
            "        if ($this->ledger->find($entryId)['ownerId'] !== $this->userId) {\n"
            "            return new JSONResponse([], Http::STATUS_FORBIDDEN);\n"
            "        }\n"
        )
        self.assertEqual(_scan(src), [])


class SessionIdentityHandoffTest(unittest.TestCase):
    """Pattern 6 — the shape that keeps the `#365` fix from being a wolf-cry.

    Measured on doriath @ bfd6da6: shipping the `#365` blanking WITHOUT this
    pattern reported 45 findings there, and that app's real gate-7 exposure was
    hand-read as ZERO. `AttachmentService::loadOwnedSecret()` refuses on
    `$secret->getOwnerId() !== $userId`; the controller's job is to hand the
    identity down, and it does.
    """

    def test_identity_handed_to_the_data_call_passes(self):
        self.assertEqual(_scan(_method(
            "        $userId = $this->sessionUserId();\n"
            "        if ($userId === null) { return new JSONResponse([], 401); }\n",
            "        return new JSONResponse($this->ledger->findOwned(entryId: $entryId, userId: $userId));\n",
        )), [])

    def test_identity_resolved_but_NOT_handed_over_is_flagged(self):
        """The discriminator. Resolving the caller is not scoping the query."""
        findings = _scan(_method(
            "        $userId = $this->sessionUserId();\n"
            "        if ($userId === null) { return new JSONResponse([], 401); }\n",
            "        $this->audit->logForUser($userId, 'read');\n"
            "        return new JSONResponse($this->ledger->find($entryId));\n",
        ))
        self.assertEqual(len(findings), 1)

    def test_a_caller_supplied_userId_proves_nothing(self):
        """`find($id, $userId)` where `$userId` came off the route is not a guard.

        This exclusion is the whole reason Pattern 6 is not a blanket: without
        it, any endpoint that takes a `userId` parameter would clear itself.
        """
        src = (
            "<?php\nclass LedgerController {\n"
            "    /**\n     * @NoAdminRequired\n     */\n"
            "    public function show(string $entryId, string $userId): JSONResponse\n    {\n"
            "        return new JSONResponse($this->ledger->findOwned($entryId, $userId));\n"
            "    }\n}\n"
        )
        self.assertEqual(len(_scan(src)), 1)

    def test_one_unscoped_call_beside_a_scoped_one_still_reports(self):
        """The ALL-quantifier. `any` would let a log line clear a real IDOR."""
        findings = _scan(_method(
            "        $userId = $this->sessionUserId();\n"
            "        if ($userId === null) { return new JSONResponse([], 401); }\n",
            "        $mine  = $this->ledger->listOwned($entryId, $userId);\n"
            "        $other = $this->ledger->find($entryId);\n"
            "        return new JSONResponse([$mine, $other]);\n",
        ))
        self.assertEqual(len(findings), 1)


class OwnershipComparisonGuardTest(unittest.TestCase):
    """Pattern 7 — the 404-style ownership refusal, which the gate's own FAIL
    message has always endorsed in prose and never recognised in code."""

    def test_ownership_mismatch_answered_404_passes(self):
        self.assertEqual(_scan(_method(
            "        $e = $this->ledger->find($entryId);\n"
            "        if ($e['ownerId'] !== $this->userId) {\n"
            "            return new JSONResponse(['message' => 'Not found'], Http::STATUS_NOT_FOUND);\n"
            "        }\n"
        )), [])

    def test_a_bare_404_without_a_comparison_still_reports(self):
        """Not-found is not access-denied. Only the COMPARISON clears."""
        findings = _scan(_method(
            "        $e = $this->ledger->find($entryId);\n"
            "        if ($e === null) {\n"
            "            return new JSONResponse(['message' => 'Not found'], Http::STATUS_NOT_FOUND);\n"
            "        }\n"
        ))
        self.assertEqual(len(findings), 1)

    def test_a_status_string_containing_user_is_not_an_identity(self):
        """`'user_draft'` must not read as the caller. String literals are excluded."""
        findings = _scan(_method(
            "        $e = $this->ledger->find($entryId);\n"
            "        if ($e['state'] !== 'user_draft') {\n"
            "            return new JSONResponse([], Http::STATUS_NOT_FOUND);\n"
            "        }\n"
        ))
        self.assertEqual(len(findings), 1)


# ---------------------------------------------------------------------------
# Pattern 8 — `#[PublicPage]` must resolve inside a declared-public scope
# ---------------------------------------------------------------------------

_PUBLIC_TPL = """\
<?php
class CatalogueController {
%s
}
"""


def _public(body: str, attrs: str = "    #[PublicPage]\n",
            sig: str = "string $id", ret: str = "JSONResponse") -> str:
    return _PUBLIC_TPL % (
        attrs
        + "    public function show(%s): %s\n    {\n%s    }\n" % (sig, ret, body)
    )


class PublicPageScopeTest(unittest.TestCase):
    """`#[PublicPage]` says the CALLER may be anonymous. It says nothing about
    which OBJECTS the endpoint may reach. Reproduced at package 57bcb2b: a
    byte-identical IDOR plant carrying the annotation — including an
    unauthenticated write to an arbitrary id — reported PASS."""

    # -- fires -------------------------------------------------------------

    def test_public_page_only_with_arbitrary_id_is_reported(self):
        """opencatalogi#856's shape: no session, a caller-chosen id, a global
        lookup. THE annotation must not exempt it."""
        findings = _public("        return new JSONResponse($this->svc->find($id));\n")
        out = _scan(findings)
        self.assertEqual(len(out), 1, out)
        self.assertIn("rule=publicpage-unscoped-object-lookup", out[0])

    def test_public_page_only_is_in_scope_at_all(self):
        """🔑 The blinding is mostly NOT the exemption. A `#[PublicPage]`
        method carrying no `#[NoAdminRequired]` was dropped one branch EARLIER,
        by the scope filter — 267 of the fleet's 357 public controller methods.
        Deleting the exemption alone would not have moved this test."""
        out = _scan(_public(
            "        return new JSONResponse($this->svc->find($id));\n"))
        self.assertEqual(len(out), 1, out)

    def test_public_page_unauthenticated_write_is_reported(self):
        """A public WRITE to an arbitrary id. `array $data` is a payload, not a
        selector, so the finding is about `$id` alone."""
        out = _scan(_public(
            "        return new JSONResponse($this->svc->update($id, $data));\n",
            sig="string $id, array $data"))
        self.assertEqual(len(out), 1, out)

    def test_both_attributes_still_reported(self):
        """The arm the documented exemption actually cleared."""
        out = _scan(_public(
            "        return new JSONResponse($this->svc->find($id));\n",
            attrs="    #[NoAdminRequired]\n    #[PublicPage]\n"))
        self.assertEqual(len(out), 1, out)

    def test_template_response_does_not_clear_a_public_renderer(self):
        """`TemplateResponse` clears a `@NoAdminRequired` method because NC
        guarantees a session there. `@PublicPage` is the annotation that turns
        that guarantee OFF, so the reason does not survive the move."""
        out = _scan(_public(
            "        $o = $this->svc->find($id);\n"
            "        return new TemplateResponse('app', 'index', ['object' => $o]);\n",
            ret="TemplateResponse"))
        self.assertEqual(len(out), 1, out)

    # -- stays silent ------------------------------------------------------

    def test_public_page_with_no_identifier_is_not_reported(self):
        """No caller-supplied value, nothing to steer."""
        out = _scan(_public(
            "        return new JSONResponse($this->svc->listPublished());\n",
            sig=""))
        self.assertEqual(out, [])

    def test_public_page_scoped_to_a_configured_namespace_is_not_reported(self):
        """The shape opencatalogi shipped in 963f832a — resolve the configured
        register/schema, refuse if unconfigured, then look the id up inside."""
        out = _scan(_public(
            "        $scope = $this->themeConfiguration();\n"
            "        if ($scope === null) {\n"
            "            return new JSONResponse([], 503);\n"
            "        }\n"
            "        $o = $this->svc->find($id, $scope['register'], $scope['schema']);\n"
            "        return new JSONResponse($o);\n"))
        self.assertEqual(out, [])

    def test_public_page_with_a_publicness_named_lookup_is_not_reported(self):
        """`findPublished($id)` declares the constraint in the callee name."""
        out = _scan(_public(
            "        return new JSONResponse($this->svc->findPublished($id));\n"))
        self.assertEqual(out, [])

    def test_a_publication_named_lookup_is_NOT_a_publicness_constraint(self):
        """Abuse control for the CamelCase-segment rule: `getPublicationById`
        starts with the letters of `public` and is a plain object read. If the
        token were matched as a substring, every `publication`-flavoured app in
        the fleet would exempt itself by naming."""
        out = _scan(_public(
            "        return new JSONResponse($this->svc->getPublicationById($id));\n"))
        self.assertEqual(len(out), 1, out)

    def test_public_page_with_a_capability_identifier_is_not_reported(self):
        """The identifier IS the authorisation — NC's public-share convention."""
        out = _scan(_public(
            "        return new JSONResponse($this->svc->find($shareToken));\n",
            sig="string $shareToken"))
        self.assertEqual(out, [])

    def test_public_form_submission_is_not_reported(self):
        """A payload-only public POST selects nothing. portaliq's entire public
        forms surface is this shape and must not light up."""
        out = _scan(_public(
            "        return new JSONResponse($this->svc->create($data));\n",
            sig="array $data"))
        self.assertEqual(out, [])

    def test_verify_in_scope_then_act_is_not_reported(self):
        """Per SELECTOR, not per call. opencatalogi's `attachments()` proves the
        object is in the catalog, refuses, and only then fetches by id — judging
        each call alone reports the second half of a correct method."""
        out = _scan(_public(
            "        $cat = $this->catalogs->getBySlug($catalogSlug);\n"
            "        if ($cat === null) {\n"
            "            return new JSONResponse([], 404);\n"
            "        }\n"
            "        $o = $this->svc->findInCatalog($id, $cat['id']);\n"
            "        if ($o === null) {\n"
            "            return new JSONResponse([], 404);\n"
            "        }\n"
            "        return new JSONResponse($this->svc->attachments($id));\n",
            sig="string $catalogSlug, string $id"))
        self.assertEqual(out, [])

    def test_state_scoped_receiver_is_not_reported(self):
        """OpenRegister's ObjectService is scoped as STATE fleet-wide."""
        out = _scan(_public(
            "        $loc = $this->query->locate($id, $this->publishedRegisters());\n"
            "        if ($loc === null) {\n"
            "            return new JSONResponse([], 404);\n"
            "        }\n"
            "        $svc = $this->objectService();\n"
            "        $svc->setRegister($loc['register']);\n"
            "        $svc->setSchema($loc['schema']);\n"
            "        return new JSONResponse($svc->find($id));\n"))
        self.assertEqual(out, [])

    def test_allow_listed_identifier_is_not_reported(self):
        """decidesk's `OriController`: `self::RESOURCE_MAP[$resource] ?? null`
        with a refusal on a miss can only ever name a member of a closed set."""
        out = _scan(_public(
            "        $schema = self::RESOURCE_MAP[$resource] ?? null;\n"
            "        if ($schema === null) {\n"
            "            return new JSONResponse([], 404);\n"
            "        }\n"
            "        return new JSONResponse($this->svc->findAll($schema, $resource));\n",
            sig="string $resource"))
        self.assertEqual(out, [])

    def test_rbac_true_alone_does_not_scope(self):
        """⚠️ The counter-example opencatalogi's own fix commit names: `_rbac:
        true` was never sufficient, because OpenRegister grants read by default
        on a schema declaring no authorization block. A bare literal argument
        does not constrain."""
        out = _scan(_public(
            "        return new JSONResponse($this->svc->find($id, _rbac: true,"
            " _multitenancy: false));\n"))
        self.assertEqual(len(out), 1, out)


class PublicPageRawBodyTest(unittest.TestCase):
    """Pattern 8b — `ConductionNL/.github#413`.

    Pattern 8 decides scope from the PARAMETER LIST, so a SOAP / webhook
    handler whose selector arrives in the request body was structurally
    invisible to it. Measured on procest's `StufController::{zaken,personen}`:
    `#[PublicPage]` + `#[NoCSRFRequired]`, no authentication of any kind, and
    gate-7 reported ZERO findings on that app's 79 public methods.
    """

    def test_raw_body_handed_to_a_collaborator_is_reported(self):
        """The shipped shape: no parameters, `php://input`, one hop."""
        out = _scan(_public(
            "        return new DataDisplayResponse($this->dispatcher->dispatch(\n"
            "            rawBody: file_get_contents('php://input'),\n"
            "            service: 'zaken'\n"
            "        ));\n",
            sig="", ret="DataDisplayResponse"))
        self.assertEqual(len(out), 1, out)
        self.assertIn("rule=publicpage-unscoped-object-lookup", out[0])

    def test_request_get_content_is_the_same_read(self):
        """`IRequest::getContent()` is the other spelling of the same source."""
        out = _scan(_public(
            "        $raw = $this->request->getContent();\n"
            "        return new JSONResponse($this->dispatcher->dispatch($raw));\n",
            sig=""))
        self.assertEqual(len(out), 1, out)

    def test_raw_body_reaches_the_call_through_a_decoder(self):
        """A plain FUNCTION call does not launder the caller's bytes.
        `json_decode` is not a `->` hop, so taint survives it — this is
        openregister's `GraphQLController::execute()` shape."""
        out = _scan(_public(
            "        $body = file_get_contents('php://input');\n"
            "        $data = json_decode($body, true);\n"
            "        $query = $data['query'];\n"
            "        return new JSONResponse($this->svc->run($query));\n",
            sig=""))
        self.assertEqual(len(out), 1, out)

    def test_raw_body_only_logged_is_not_in_scope(self):
        """PSR-3 diagnostics return void and resolve nothing — the same
        exclusion Pattern 6 already makes."""
        out = _scan(_public(
            "        $raw = file_get_contents('php://input');\n"
            "        $this->logger->warning('inbound', ['body' => $raw]);\n"
            "        return new JSONResponse(['status' => 'ok']);\n",
            sig=""))
        self.assertEqual(out, [], out)

    def test_a_public_page_without_a_raw_body_read_is_untouched(self):
        """The abuse control on the widening itself: `#[PublicPage]` plus a
        parameterless body that reads nothing must stay silent, or the repair
        would be 'flag every public method'."""
        out = _scan(_public(
            "        return new JSONResponse($this->svc->listPublished());\n",
            sig=""))
        self.assertEqual(out, [], out)

    def test_raw_body_with_a_refusing_signature_check_clears(self):
        """NO NEW CLEAR WAS INVENTED. `checkSignature()` is recognised by the
        SAME `_GUARD_HELPER_NAME_RE` Pattern 1 has always used — procest's
        `DSOIntakeController::intake()`."""
        src = _PUBLIC_TPL % (
            "    #[PublicPage]\n"
            "    public function intake(): JSONResponse\n    {\n"
            "        $raw = (string)file_get_contents('php://input');\n"
            "        if ($this->checkSignature(body: $raw) === false) {\n"
            "            return new JSONResponse(['message' => 'bad signature'], 400);\n"
            "        }\n"
            "        return new JSONResponse($this->svc->process($raw));\n"
            "    }\n"
            "    private function checkSignature(string $body): bool\n    {\n"
            "        return $body !== '';\n"
            "    }\n")
        self.assertEqual(_scan(src), [])

    def test_forwarded_signature_variable_clears(self):
        """pipelinq's `BrpController::mutationWebhook()`: the HMAC is verified
        one hop down, and what the controller shows is the credential
        travelling with the bytes it authenticates. Same rule Pattern 8 already
        applies to a `$token` on a scalar lookup."""
        out = _scan(_public(
            "        $rawBody = (string)file_get_contents('php://input');\n"
            "        $signature = (string)$this->request->getHeader('X-Signature');\n"
            "        return new JSONResponse($this->listener->handle($rawBody, $signature));\n",
            sig=""))
        self.assertEqual(out, [], out)

    def test_forwarded_signature_named_argument_clears(self):
        """The same idiom spelled with a NAMED ARGUMENT — pipelinq's
        `CtiController::webhook()`, where the variable is `$signatureArg` and
        only the label says `signature:`. Reading one spelling and not the
        other would report one of these two apps and clear the other."""
        out = _scan(_public(
            "        $rawBody = (string)file_get_contents('php://input');\n"
            "        $sig = (string)$this->request->getHeader('X-Sig');\n"
            "        return new JSONResponse($this->svc->handleWebhook("
            "rawBody: $rawBody, signature: $sig));\n",
            sig=""))
        self.assertEqual(out, [], out)

    def test_no_credential_alongside_the_body_is_still_reported(self):
        """🔑 THE ABUSE CONTROL ON THAT CLEAR. procest's StUF routes forward
        the envelope and nothing else — the WSSE token is INSIDE the XML, so
        there is no credential in the argument list — and they were the two
        real exposures `#413` was filed for. Byte-identical to the arms above
        apart from the missing signature argument."""
        out = _scan(_public(
            "        $rawBody = (string)file_get_contents('php://input');\n"
            "        return new JSONResponse($this->listener->handle($rawBody, 'zaken'));\n",
            sig=""))
        self.assertEqual(len(out), 1, out)

    def test_raw_body_with_an_inline_401_clears(self):
        """procest's `DwangsomPaymentCallbackController::callback()`: the
        signature check IS the auth and it answers 401 in the body."""
        out = _scan(_public(
            "        $raw = (string)file_get_contents('php://input');\n"
            "        if ($this->signer->validateSignature(rawBody: $raw) === false) {\n"
            "            return new JSONResponse(['message' => 'invalid'], 401);\n"
            "        }\n"
            "        return new JSONResponse($this->svc->handleCallback($raw));\n",
            sig=""))
        self.assertEqual(out, [], out)


def _cast_arm(body: str, sig: str = "string $appId") -> str:
    """One `#[NoAdminRequired]` method whose body is given verbatim.

    Unlike `_method()` above, nothing is appended: every `#414` arm differs
    from its neighbours by ONE TOKEN, so the body has to be the whole variable.
    """
    return (
        "<?php\nclass AppOverrideController {\n"
        "    #[NoAdminRequired]\n"
        "    public function getUser(%s): JSONResponse\n    {\n" % sig
        + body + "    }\n}\n"
    )


class CastOnSessionIdentityTest(unittest.TestCase):
    """`ConductionNL/.github#414` — a `(string)` cast blinded Pattern 6.

    Control 2 of `_is_identity_expression` rejects "any call with arguments"
    with `\\(\\s*[^)\\s]`, and a cast is written with exactly those bytes. So
    the GUARD was unchanged and only its SPELLING moved the verdict — a false
    positive whose recommended repair (add a guard) was wrong, on an endpoint
    that already had one.
    """

    _CAST_ARG = (
        "        $user = $this->userSession->getUser();\n"
        "        return new JSONResponse($this->svc->getUserDelta("
        "appId: $appId, uid: (string)$user->getUID()));\n"
    )
    _PLAIN_ARG = (
        "        $user = $this->userSession->getUser();\n"
        "        return new JSONResponse($this->svc->getUserDelta("
        "appId: $appId, uid: $user->getUID()));\n"
    )
    _CAST_LOCAL = (
        "        $user = $this->userSession->getUser();\n"
        "        $uid = (string)$user->getUID();\n"
        "        return new JSONResponse($this->svc->getUserDelta("
        "appId: $appId, uid: $uid));\n"
    )

    def test_cast_on_the_identity_argument_still_clears(self):
        """Arm A — the SHIPPED openbuild spelling. FAIL before `#414`."""
        self.assertEqual(_scan(_cast_arm(self._CAST_ARG)), [])

    def test_uncast_arm_is_the_control(self):
        """Arm B. It passed before `#414` and after — it is what made the
        one-token difference visible in the first place."""
        self.assertEqual(_scan(_cast_arm(self._PLAIN_ARG)), [])

    def test_cast_through_a_local_clears_too(self):
        """Arm C, the one whose failure was NOT predicted: hoisting into a
        variable is the obvious workaround and it did not work, because the
        assignment's right-hand side is classified by the same predicate. A fix
        that normalises only the argument position leaves this one red."""
        self.assertEqual(_scan(_cast_arm(self._CAST_LOCAL)), [])

    def test_cast_on_a_caller_supplied_value_is_still_reported(self):
        """🔑 THE ABUSE CONTROL. Stripping the cast must not route a value the
        CALLER chose past the declared-parameter veto just because its name
        contains "uid". This must stay a finding, or `#414` would have turned a
        false positive into a false NEGATIVE — the direction that leaves no log
        to notice."""
        out = _scan(_cast_arm(
            "        return new JSONResponse($this->svc->getUserDelta("
            "appId: $appId, uid: (string)$targetUid));\n",
            sig="string $appId, string $targetUid"))
        self.assertEqual(len(out), 1, out)

    def test_cast_does_not_make_object_data_an_identity(self):
        """The subscript control survives the strip: `(string)$row['ownerId']`
        is the server's data about an object the caller named, not the caller."""
        self.assertFalse(
            cni._is_identity_expression("(string)$row['ownerId']"))

    def test_cast_does_not_make_a_predicate_call_an_identity(self):
        """And so does the argument control: after the cast is removed there is
        still a real argument list."""
        self.assertFalse(
            cni._is_identity_expression("(string)canAccess($id, $uid)"))

    def test_array_and_object_casts_are_not_stripped(self):
        """`(array)` / `(object)` would launder a payload into an identity, so
        they are deliberately absent from the cast list."""
        self.assertEqual(
            cni._strip_leading_scalar_casts("(array)$user->getUID()"),
            "(array)$user->getUID()")


class HelperGuardEvidenceTest(unittest.TestCase):
    """A gate that can be silenced by a sentence in a comment is not measuring
    the code."""

    _OWNED = """\
<?php
class AgentController {
    #[NoAdminRequired]
    public function rotate(string $id): JSONResponse
    {
        $user = $this->userSession->getUser();
        if ($user === null) {
            return new JSONResponse([], Http::STATUS_UNAUTHORIZED);
        }
        $agent = $this->%s(agentId: $id);
        if ($agent === null) {
            return new JSONResponse([], Http::STATUS_NOT_FOUND);
        }
        return new JSONResponse($this->webhooks->rotate(agent: $agent));
    }

    private function %s(string $agentId): ?ObjectEntity
    {
%s    }
}
"""

    _OWNERSHIP_BODY = (
        "        $agent = $this->objectService->find(id: $agentId);\n"
        "        if ($agent->getOwner() !== $this->userId) {\n"
        "            return null;\n"
        "        }\n"
        "        return $agent;\n"
    )

    _COMMENT_ONLY_BODY = (
        "        // The caller invokes this helper OUTSIDE its own try block, so\n"
        "        // the throw would escape as a framework 500.\n"
        "        return $this->objectService->find(id: $agentId);\n"
    )

    def test_a_comment_mentioning_throw_is_not_a_guard(self):
        """MEASURED on hermiq `AgentWebhookController::loadOwnedAgent`: the body
        contains no `throw` statement at all — the word appears only in a code
        comment explaining why the helper CATCHES one — and that made the helper
        guard-bearing, clearing all four routed methods that call it."""
        src = self._OWNED % ("loadAgent", "loadAgent", self._COMMENT_ONLY_BODY)
        findings = _scan(src)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("method=rotate", findings[0])

    def test_an_ownership_helper_answering_null_still_clears(self):
        """…and the narrowing costs no true clear: a helper that compares
        ownership and answers `null` — the deliberate anti-oracle choice — is
        recognised by its CONDITION, which is how hermiq's real
        `loadOwnedAgent()` keeps clearing its four callers."""
        src = self._OWNED % ("loadAgent", "loadAgent", self._OWNERSHIP_BODY)
        self.assertEqual(_scan(src), [])


# ---------------------------------------------------------------------------
# `.github#398` — Pattern 6 clause 2 vetoed on calls that resolve NOTHING
# ---------------------------------------------------------------------------

class SanitiserHelperFalsePositiveTest(unittest.TestCase):
    """A correctly-scoped method must not be flagged by a sanitiser call.

    ⚠️ ANCHORED SUBJECTS. Every assertion here pins BOTH the count AND the
    method name, and the fixtures below differ from one another by ONE
    LINE. `authn-vs-authz` went green over a reverted fix because it asserted
    `method=preamble` while a sibling logged `method=preambleForbiddenCode`,
    which CONTAINS it — so a substring match cannot tell these apart. The
    method here is always `show`, and the arms are separated by the count and
    by which fixture is used, never by a name prefix.

    The arms are a matrix, and the negative ones are the point: a fix that
    merely quietened the sanitiser case would pass arms 1-3 and silently
    break arms 5, 6 and 9 — each of which is a REAL unguarded lookup.
    """

    # `show` is scoped: `find($key, $uid)` carries the session identity.
    _TMPL = """\
<?php
namespace OCA\\Demo\\Controller;
use OCP\\AppFramework\\Controller;
use OCP\\AppFramework\\Http\\Attribute\\NoAdminRequired;
class ThingController extends Controller {
    #[NoAdminRequired]
    public function show(string $key): JSONResponse {
        $user = $this->userSession->getUser();
        if ($user === null) { return new JSONResponse([], Http::STATUS_UNAUTHORIZED); }
        $uid = $this->userSession->getUser()->getUID();
%s
    }
%s
}
"""
    _SANITISER = ("    private function sanitizeKey(string $k): string "
                  "{ return preg_replace('/[^a-z0-9]/i', '', $k); }")
    # Token-clean, but delegates to a collaborator that RESOLVES.
    _DELEGATING = ("    private function collect(string $k) "
                   "{ $d = $this->dossierService->getDossierForCase(caseId: $k); "
                   "return $d['items'] ?? []; }")
    # A helper that resolves in its own body.
    _RESOLVING = ("    private function findCatalogItem(string $k) "
                  "{ return $this->objectService->find($k); }")

    def _scan_body(self, body, helper):
        return _scan(self._TMPL % (body, helper))

    def test_1_scoped_method_is_clean(self):
        """Control: the unmodified scoped method is not flagged."""
        self.assertEqual(self._scan_body(
            "        return new JSONResponse($this->store->find($key, $uid));",
            self._SANITISER), [])

    def test_2_sanitiser_call_does_not_create_a_finding(self):
        """THE DEFECT. Adding only `$safeKey = $this->sanitizeKey($key);` to the
        clean method above used to flip it to a finding, though the data access
        it performs is byte-identical and still carries `$uid`."""
        self.assertEqual(self._scan_body(
            "        $safeKey = $this->sanitizeKey($key);\n"
            "        return new JSONResponse($this->store->find($key, $uid));",
            self._SANITISER), [])

    def test_3_identity_in_the_helper_call_also_clears(self):
        """The other direction of the original isolation: handing the identity
        to the SANITISER cleared it even before the fix. Pinned so a future
        change cannot make the two arms disagree."""
        self.assertEqual(self._scan_body(
            "        $safeKey = $this->sanitizeKey($key, $uid);\n"
            "        return new JSONResponse($this->store->find($key, $uid));",
            self._SANITISER), [])

    def test_5_a_LAUNDERED_lookup_is_still_reported(self):
        """⚠️ THE ARM THAT MATTERS. A scoped call exists (so clause 3 is
        satisfied) AND the sanitised value reaches an UNSCOPED lookup. Only
        taint propagation catches this; with half (A) removed and half (B)
        kept, this fixture goes SILENT and a real IDOR ships.

        Measured exactly that way during development: pre-fix 1, fixed 1,
        taint-disabled 0."""
        findings = self._scan_body(
            "        $safeKey = $this->sanitizeKey($key);\n"
            "        $mine = $this->store->listOwned($uid);\n"
            "        return new JSONResponse($this->store->find($safeKey));",
            self._SANITISER)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("method=show", findings[0])

    def test_6_logger_exempt_does_not_hide_a_real_lookup(self):
        """The PSR-3 exemption must not clear a method that also performs an
        unscoped lookup."""
        findings = self._scan_body(
            '        $this->logger->error("failed for ".$key);\n'
            "        $mine = $this->store->listOwned($uid);\n"
            "        return new JSONResponse($this->store->find($key));",
            self._SANITISER)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("method=show", findings[0])

    def test_7_a_logger_only_veto_clears(self):
        """…and the exemption does its job when the real lookup IS scoped.
        Measured on openbuild/procest: a caller-supplied id inside an error
        message was reported as an unscoped object resolution."""
        self.assertEqual(self._scan_body(
            '        $this->logger->error("looking up ".$key);\n'
            "        return new JSONResponse($this->store->find($key, $uid));",
            self._SANITISER), [])

    def test_8_a_helper_that_resolves_keeps_its_veto(self):
        """A same-class helper is cleared by READING IT, never by its name: one
        that performs data access in its own body still reports."""
        findings = self._scan_body(
            "        $item = $this->findCatalogItem($key);\n"
            "        $mine = $this->store->listOwned($uid);\n"
            "        return new JSONResponse($item);",
            self._RESOLVING)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("method=show", findings[0])

    def test_9_helper_delegating_to_a_collaborator_is_not_pure(self):
        """⚠️ REGRESSION PIN — this shape was SILENTLY CLEARED by the first
        draft, and no arm I had written caught it; hand-reading the cleared
        fleet set did.

        `collect()` contains no data-access, mutation or request-read token of
        its own — `getDossierForCase` matches none of the gate's vocabularies —
        but it reaches a collaborator that resolves. The purity walk therefore
        has to fail closed on ANY call it cannot account for, not just on the
        tokens it recognises. Real subject: procest
        `ZaakdossierDownloadController::downloadZip`, an unguarded case-dossier
        download."""
        findings = self._scan_body(
            "        $docs = $this->collect($key);\n"
            "        $mine = $this->store->listOwned($uid);\n"
            "        return new JSONResponse($docs);",
            self._DELEGATING)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("method=show", findings[0])


class CommentIsNotAGuardTest(unittest.TestCase):
    """A TODO naming the guard is not the guard (#415).

    `gsrc` — the text every guard lookup in `scan_file` runs against — was the
    RAW source with only authentication-only spans removed. So a sentence in a
    method body answered "is this endpoint guarded?". Measured through the
    runner, one fixture, ONE ADDED LINE: a real unguarded `#[NoAdminRequired]`
    endpoint went FAIL -> PASS on the strength of
    `// TODO: throw new OCSForbiddenException when the caller does not own $id.`

    **This gate's known failure mode has always been false POSITIVES**, which
    is precisely why its silences get believed, and why a false negative here
    costs more than in any other gate in the package. The arm below is the
    cheap, permanent version of that measurement.
    """

    _UNGUARDED = """<?php
namespace OCA\\Fx\\Controller;
class ItemController {
    #[NoAdminRequired]
    public function index(int $id) {
%s        return $this->service->find($id);
    }
}
"""

    def test_positive_control_an_unguarded_endpoint_is_a_finding(self):
        """First, and not decoration: every arm below is worthless if this
        one ever goes green."""
        findings = _scan(self._UNGUARDED % "")
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("method=index", findings[0])

    def test_a_todo_naming_the_missing_guard_is_not_a_guard(self):
        findings = _scan(self._UNGUARDED % (
            "        // TODO: throw new OCSForbiddenException when the caller "
            "does not own $id.\n"))
        self.assertEqual(len(findings), 1, findings)

    def test_a_docblock_describing_the_absent_guard_is_not_a_guard(self):
        """The block-comment spelling of the same sentence. `//` and `/* */`
        are two code paths in the stripper and a fix to one is not a fix to
        the other."""
        findings = _scan(self._UNGUARDED % (
            "        /* Once #999 lands we throw new OCSForbiddenException here\n"
            "           unless the caller owns $id. Not done yet. */\n"))
        self.assertEqual(len(findings), 1, findings)

    def test_a_hash_comment_is_a_comment_too(self):
        """`#` opens a PHP comment. It was not handled at all, so the whole
        repair was one alternative spelling away from being bypassed."""
        findings = _scan(self._UNGUARDED % (
            "        # TODO: throw new OCSForbiddenException unless $id is owned "
            "by the caller.\n"))
        self.assertEqual(len(findings), 1, findings)

    def test_the_attribute_survives_the_comment_stripper(self):
        """`#[NoAdminRequired]` is an ATTRIBUTE, not a `#` comment, and it is
        the single token that makes this gate look at a method at all.
        Blanking it would not widen the gate — it would switch it off, and the
        symptom would be a silent PASS on every controller in the fleet."""
        cleaned = cni._strip_strings_and_comments(
            "#[NoAdminRequired]\npublic function index() {}\n", keep_strings=True)
        self.assertIn("#[NoAdminRequired]", cleaned)

    def test_a_real_ownership_guard_still_passes(self):
        """The anti-widening pair. A stripper that ate code rather than
        comments passes every arm above and fails this one."""
        findings = _scan("""<?php
namespace OCA\\Fx\\Controller;
class ItemController {
    #[NoAdminRequired]
    public function index(int $id) {
        $thing = $this->service->find($id);
        if ($thing->getOwner() !== $this->userSession->getUser()->getUID()) {
            throw new OCSForbiddenException();
        }
        return $thing;
    }
}
""")
        self.assertEqual(findings, [])

    def test_a_guard_whose_argument_is_a_string_still_passes(self):
        """String literals are deliberately KEPT by `keep_strings=True`. A
        guard's evidence is often an argument that IS a string — a scope name,
        a permission key — and blanking literals in a 2,800-line checker whose
        known failure mode is over-reporting would trade a measured false
        negative for an unmeasured wave of false positives."""
        findings = _scan("""<?php
namespace OCA\\Fx\\Controller;
class ItemController {
    #[NoAdminRequired]
    public function index(int $id) {
        $thing = $this->service->find($id);
        if ($thing->getOwner() !== $this->userSession->getUser()->getUID()) {
            throw new OCSForbiddenException('thing.read denied for this owner');
        }
        return $thing;
    }
}
""")
        self.assertEqual(findings, [])


class AuthenticationHelperIsNotAGuardTest(unittest.TestCase):
    """`.github#365` follow-up — the DELEGATED authentication check.

    `#365` established that `if ($user === null) { 401 }` is authentication,
    not authorisation, and blanked it where it is written INLINE. The same
    clause hidden one call-hop away, behind a helper whose name merely starts
    with `require`, still cleared the method on its NAME alone.

    MEASURED on decidesk `ConflictOfInterestController` (2026-08-20): three
    `#[NoAdminRequired]` routes took a caller-supplied id straight into a
    service with no caller scoping, and gate-7 reported PASS. A probe carrying
    ONLY `$this->requireUserOr401(...)` silenced a textbook IDOR.
    """

    def test_require_user_helper_does_not_clear(self) -> None:
        src = """<?php
class C extends Controller {
    #[NoAdminRequired]
    public function show(string $id): JSONResponse {
        $auth = $this->requireUserOr401(session: $this->userSession);
        if ($auth !== null) {
            return $auth;
        }
        return new JSONResponse($this->objectService->find($id));
    }
}
"""
        self.assertTrue(
            _scan(src),
            "an authentication-only helper must not clear an unguarded id",
        )

    def test_real_authorisation_helpers_still_clear(self) -> None:
        """The exclusion must not eat genuine authorisation spellings."""
        for call in (
            "$this->requireOwner(id: $id);",
            "$this->requireUserIsOwner(id: $id);",
            "$this->ensureAccess(id: $id);",
            "$this->authorizePermission(id: $id);",
        ):
            src = """<?php
class C extends Controller {
    #[NoAdminRequired]
    public function show(string $id): JSONResponse {
        %s
        return new JSONResponse($this->objectService->find($id));
    }
}
""" % call
            self.assertEqual(
                [], _scan(src),
                f"{call} is an authorisation guard and must still clear",
            )


# Keep this block LAST in the file. `tests/run-helper-suites.sh` invokes this
# suite as `python3 scripts/lib/test_check_no_admin_idor.py`, so `unittest.main()`
# runs — and exits — at the point it is reached. A test class appended BELOW it
# is never even defined, let alone collected: the run reports OK on a smaller
# suite, which reads exactly like a passing full one. (Adding two tests under a
# trailing main block took the CI count from 169 to 169.)
if __name__ == "__main__":
    unittest.main()
